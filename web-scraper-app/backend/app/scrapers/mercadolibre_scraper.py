# Scraper MercadoLibre Chile
# ==========================
"""
Scraper específico para MercadoLibre Chile.
Extrae productos de resultados de búsqueda.
"""

import re
from typing import List, Optional
from urllib.parse import urljoin, quote
from bs4 import BeautifulSoup

from .base_scraper import BaseScraper, ScrapedProduct


class MercadoLibreScraper(BaseScraper):
    """
    Scraper para MercadoLibre Chile (mercadolibre.cl)

    Extrae:
    - Nombre del producto
    - Precio actual
    - Precio original (si hay descuento)
    - Porcentaje de descuento
    - URL del producto
    - Imagen
    """

    @property
    def name(self) -> str:
        return "MercadoLibre Chile"

    @property
    def base_url(self) -> str:
        return "https://listado.mercadolibre.cl"

    def build_search_url(self, search_term: str, page: int = 1) -> str:
        """
        Construye la URL de búsqueda de MercadoLibre.

        Formato: https://listado.mercadolibre.cl/{término}
        Paginación: _Desde_{offset} donde offset = (page-1) * 50 + 1

        Args:
            search_term: Término de búsqueda
            page: Número de página

        Returns:
            URL de búsqueda completa
        """
        # Limpiar y codificar término de búsqueda
        term = search_term.strip().replace(' ', '-')

        if page == 1:
            return f"{self.base_url}/{term}"
        else:
            # MercadoLibre usa offset basado en 50 productos por página
            offset = (page - 1) * 50 + 1
            return f"{self.base_url}/{term}_Desde_{offset}"

    def parse_products(self, soup: BeautifulSoup) -> List[ScrapedProduct]:
        """
        Extrae productos del HTML de MercadoLibre.

        Args:
            soup: BeautifulSoup con el HTML de la página

        Returns:
            Lista de productos extraídos
        """
        products = []

        # Buscar contenedores de productos
        # MercadoLibre usa diferentes estructuras, probamos varias
        product_cards = soup.select('li.ui-search-layout__item')

        if not product_cards:
            # Estructura alternativa
            product_cards = soup.select('div.ui-search-result__wrapper')

        if not product_cards:
            # Otra estructura posible
            product_cards = soup.select('div.andes-card')

        self.logger.debug(f"Encontrados {len(product_cards)} contenedores de productos")

        for card in product_cards:
            try:
                product = self._parse_product_card(card)
                if product:
                    products.append(product)
            except Exception as e:
                self.logger.warning(f"Error parseando producto: {e}")
                continue

        return products

    def _parse_product_card(self, card) -> Optional[ScrapedProduct]:
        """
        Parsea una tarjeta individual de producto.

        Args:
            card: Elemento BeautifulSoup con la tarjeta del producto

        Returns:
            ScrapedProduct o None si falla el parseo
        """
        # Extraer nombre
        name_elem = (
            card.select_one('h2.ui-search-item__title') or
            card.select_one('a.ui-search-item__group__element') or
            card.select_one('h2.poly-box') or
            card.select_one('.poly-component__title')
        )

        if not name_elem:
            return None

        name = name_elem.get_text(strip=True)

        if not name:
            return None

        # Extraer URL
        url_elem = (
            card.select_one('a.ui-search-link') or
            card.select_one('a.ui-search-item__group__element') or
            card.select_one('a.poly-component__title') or
            card.select_one('a[href*="mercadolibre"]')
        )

        url = url_elem.get('href', '') if url_elem else ''

        if not url:
            # Intentar buscar cualquier enlace
            link = card.find('a', href=True)
            url = link.get('href', '') if link else ''

        # Extraer precio actual
        price_elem = (
            card.select_one('span.andes-money-amount__fraction') or
            card.select_one('span.price-tag-fraction') or
            card.select_one('.ui-search-price__second-line span.andes-money-amount__fraction')
        )

        if not price_elem:
            return None

        current_price = self.clean_price(price_elem.get_text(strip=True))

        if not current_price or current_price <= 0:
            return None

        # Extraer precio original (si hay descuento)
        original_price = None
        original_price_elem = (
            card.select_one('s.andes-money-amount') or
            card.select_one('span.ui-search-price__original-value') or
            card.select_one('.ui-search-price__first-line span.andes-money-amount__fraction')
        )

        if original_price_elem:
            original_text = original_price_elem.get_text(strip=True)
            original_price = self.clean_price(original_text)

        # Extraer descuento (si está explícito)
        discount = 0.0
        discount_elem = (
            card.select_one('span.ui-search-price__discount') or
            card.select_one('.andes-money-amount__discount')
        )

        if discount_elem:
            discount_text = discount_elem.get_text(strip=True)
            # Extraer número del texto "20% OFF"
            match = re.search(r'(\d+)', discount_text)
            if match:
                discount = float(match.group(1))
        elif original_price and original_price > current_price:
            # Calcular descuento si tenemos precio original
            discount = self.calculate_discount(current_price, original_price)

        # Extraer imagen
        image_url = None
        img_elem = (
            card.select_one('img.ui-search-result-image__element') or
            card.select_one('img.poly-component__picture') or
            card.select_one('img[data-src]') or
            card.select_one('img')
        )

        if img_elem:
            image_url = img_elem.get('data-src') or img_elem.get('src', '')

        # Extraer ID externo de la URL
        external_id = None
        if url:
            match = re.search(r'MLC-?(\d+)', url)
            if match:
                external_id = f"MLC{match.group(1)}"

        return ScrapedProduct(
            external_id=external_id,
            name=name,
            url=url,
            current_price=current_price,
            original_price=original_price,
            discount=discount,
            image_url=image_url,
            currency="CLP",
            in_stock=True
        )
