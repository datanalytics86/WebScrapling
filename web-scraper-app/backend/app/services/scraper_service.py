# Servicio de Scraping
# ====================
"""
Servicio que orquesta el proceso de scraping.
Maneja la lógica de negocio para ejecutar scrapers y guardar resultados.
"""

import os
import json
import logging
from datetime import datetime
from typing import List, Dict, Any, Optional, Type

from sqlalchemy.orm import Session

from ..models import Website, Product, PriceHistory, ScrapingLog
from ..scrapers.base_scraper import BaseScraper, ScrapedProduct
from ..scrapers.mercadolibre_scraper import MercadoLibreScraper
from ..scrapers.falabella_scraper import FalabellaScraper
from ..scrapers.bci_scraper import BciBenefitsScraper

# Configurar logging
logger = logging.getLogger(__name__)

# Umbral de cambio de precio para marcar (porcentaje)
PRICE_CHANGE_THRESHOLD = float(os.getenv('PRICE_CHANGE_THRESHOLD', 10))


class ScraperService:
    """
    Servicio para ejecutar scrapers y gestionar los datos extraídos.

    Responsabilidades:
    - Ejecutar scrapers para sitios configurados
    - Guardar/actualizar productos en la base de datos
    - Registrar histórico de precios
    - Detectar cambios significativos de precio
    - Generar logs de ejecución
    """

    # Mapeo de nombres de clase a clases de scrapers
    SCRAPER_CLASSES: Dict[str, Type[BaseScraper]] = {
        'MercadoLibreScraper': MercadoLibreScraper,
        'FalabellaScraper': FalabellaScraper,
        'BciBenefitsScraper': BciBenefitsScraper,
    }

    def __init__(self, db: Session):
        """
        Inicializa el servicio con una sesión de base de datos.

        Args:
            db: Sesión de SQLAlchemy
        """
        self.db = db

    def get_scraper_class(self, class_name: str) -> Optional[Type[BaseScraper]]:
        """
        Obtiene la clase de scraper por nombre.

        Args:
            class_name: Nombre de la clase del scraper

        Returns:
            Clase del scraper o None si no existe
        """
        return self.SCRAPER_CLASSES.get(class_name)

    def run_scraping_for_website(
        self,
        website: Website,
        max_pages: int = 1
    ) -> ScrapingLog:
        """
        Ejecuta el scraping para un sitio web específico.

        Args:
            website: Modelo Website a scrapear
            max_pages: Número máximo de páginas a procesar

        Returns:
            Log del scraping ejecutado
        """
        # Crear registro de log
        log = ScrapingLog(
            website_id=website.id,
            status='running',
            started_at=datetime.utcnow()
        )
        self.db.add(log)
        self.db.commit()

        errors = []
        products_found = 0
        products_new = 0
        products_updated = 0

        try:
            # Obtener clase del scraper
            scraper_class = self.get_scraper_class(website.scraper_class)

            if not scraper_class:
                raise ValueError(f"Scraper no encontrado: {website.scraper_class}")

            # Crear instancia del scraper
            with scraper_class() as scraper:
                logger.info(f"🚀 Iniciando scraping de {website.name}")

                # Ejecutar scraping
                scraped_products = scraper.scrape(
                    search_term=website.search_term or "notebook",
                    max_pages=max_pages
                )

                products_found = len(scraped_products)
                stats = scraper.get_stats()

                # Procesar productos encontrados
                for scraped in scraped_products:
                    try:
                        is_new = self._save_product(website.id, scraped)
                        if is_new:
                            products_new += 1
                        else:
                            products_updated += 1
                    except Exception as e:
                        errors.append(f"Error guardando producto '{scraped.name[:50]}': {str(e)}")
                        logger.error(f"Error guardando producto: {e}")

                # Actualizar log con éxito
                log.status = 'success' if not errors else 'partial'
                log.products_found = products_found
                log.products_new = products_new
                log.products_updated = products_updated
                log.duration = stats.get('duration')

        except Exception as e:
            logger.error(f"❌ Error en scraping de {website.name}: {e}")
            errors.append(str(e))
            log.status = 'error'

        finally:
            # Guardar errores y finalizar log
            log.errors = json.dumps(errors) if errors else None
            log.finished_at = datetime.utcnow()

            if log.duration is None and log.started_at:
                log.duration = (log.finished_at - log.started_at).total_seconds()

            self.db.commit()

        logger.info(
            f"✅ Scraping de {website.name} completado: "
            f"{products_found} encontrados, {products_new} nuevos, {products_updated} actualizados"
        )

        return log

    def _save_product(self, website_id: int, scraped: ScrapedProduct) -> bool:
        """
        Guarda o actualiza un producto en la base de datos.

        Args:
            website_id: ID del sitio web
            scraped: Producto scrapeado

        Returns:
            True si es un producto nuevo, False si se actualizó
        """
        # Buscar producto existente por URL o external_id
        existing = None

        if scraped.external_id:
            existing = self.db.query(Product).filter(
                Product.website_id == website_id,
                Product.external_id == scraped.external_id
            ).first()

        if not existing and scraped.url:
            existing = self.db.query(Product).filter(
                Product.website_id == website_id,
                Product.url == scraped.url
            ).first()

        is_new = existing is None

        if is_new:
            # Crear nuevo producto
            product = Product(
                website_id=website_id,
                external_id=scraped.external_id,
                name=scraped.name,
                url=scraped.url,
                image_url=scraped.image_url,
                current_price=scraped.current_price,
                original_price=scraped.original_price,
                discount=scraped.discount,
                currency=scraped.currency,
                in_stock=scraped.in_stock,
                last_scraped=datetime.utcnow()
            )
            self.db.add(product)
            self.db.flush()  # Para obtener el ID

        else:
            product = existing

            # Calcular cambio de precio
            old_price = product.current_price
            new_price = scraped.current_price

            if old_price and old_price > 0:
                price_change = ((new_price - old_price) / old_price) * 100
                product.price_change_percent = round(price_change, 2)
                product.price_changed = abs(price_change) >= PRICE_CHANGE_THRESHOLD

                if product.price_changed:
                    logger.info(
                        f"💰 Cambio de precio detectado en '{product.name[:30]}': "
                        f"{old_price} -> {new_price} ({price_change:+.1f}%)"
                    )

            # Actualizar campos
            product.name = scraped.name
            product.url = scraped.url
            product.image_url = scraped.image_url
            product.current_price = scraped.current_price
            product.original_price = scraped.original_price
            product.discount = scraped.discount
            product.in_stock = scraped.in_stock
            product.last_scraped = datetime.utcnow()

        # Guardar en histórico de precios
        history = PriceHistory(
            product_id=product.id,
            price=scraped.current_price,
            original_price=scraped.original_price,
            discount=scraped.discount
        )
        self.db.add(history)

        self.db.commit()
        return is_new

    def run_all_active_websites(self, max_pages: int = 1) -> List[ScrapingLog]:
        """
        Ejecuta scraping para todos los sitios activos.

        Args:
            max_pages: Número máximo de páginas por sitio

        Returns:
            Lista de logs generados
        """
        websites = self.db.query(Website).filter(Website.active == True).all()

        logs = []
        for website in websites:
            try:
                log = self.run_scraping_for_website(website, max_pages)
                logs.append(log)
            except Exception as e:
                logger.error(f"Error en scraping de {website.name}: {e}")

        return logs

    def initialize_default_websites(self):
        """
        Crea los sitios web por defecto si no existen.
        """
        default_websites = [
            {
                'name': 'MercadoLibre Chile',
                'base_url': 'https://www.mercadolibre.cl',
                'scraper_class': 'MercadoLibreScraper',
                'search_term': 'notebook',
                'active': True
            },
            {
                'name': 'Falabella Chile',
                'base_url': 'https://www.falabella.com/falabella-cl',
                'scraper_class': 'FalabellaScraper',
                'search_term': 'notebook',
                'active': True
            },
            {
                'name': 'BCI Beneficios Chile',
                'base_url': 'https://www.bci.cl/beneficios',
                'scraper_class': 'BciBenefitsScraper',
                'search_term': 'beneficios',
                'active': True
            }
        ]

        for website_data in default_websites:
            existing = self.db.query(Website).filter(
                Website.name == website_data['name']
            ).first()

            if not existing:
                website = Website(**website_data)
                self.db.add(website)
                logger.info(f"✅ Sitio web creado: {website_data['name']}")

        self.db.commit()

    @staticmethod
    def get_available_scrapers() -> Dict[str, str]:
        """
        Retorna los scrapers disponibles.

        Returns:
            Diccionario {nombre_clase: nombre_legible}
        """
        return {
            'MercadoLibreScraper': 'MercadoLibre Chile',
            'FalabellaScraper': 'Falabella Chile',
            'BciBenefitsScraper': 'BCI Beneficios Chile',
        }
