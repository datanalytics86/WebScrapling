# Scraper Base Abstracto
# ======================
"""
Clase base abstracta para todos los scrapers.
Define la interfaz común y funcionalidades compartidas.
"""

import time
import random
import logging
from abc import ABC, abstractmethod
from typing import List, Dict, Any, Optional
from dataclasses import dataclass
from datetime import datetime

import requests
from bs4 import BeautifulSoup
from fake_useragent import UserAgent

# Configurar logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)


@dataclass
class ScrapedProduct:
    """
    Estructura de datos para un producto extraído.
    Representa los datos crudos antes de guardarlos en BD.
    """
    external_id: Optional[str]
    name: str
    url: str
    current_price: float
    original_price: Optional[float] = None
    discount: float = 0.0
    image_url: Optional[str] = None
    currency: str = "CLP"
    in_stock: bool = True


class BaseScraper(ABC):
    """
    Clase base abstracta para scrapers de e-commerce.

    Características:
    - Rotación de User-Agent
    - Delays aleatorios entre requests
    - Retry logic con backoff exponencial
    - Logging detallado
    - Manejo de errores robusto
    """

    # Configuración por defecto
    DEFAULT_DELAY_MIN = 2
    DEFAULT_DELAY_MAX = 5
    DEFAULT_MAX_RETRIES = 3
    DEFAULT_TIMEOUT = 30

    def __init__(
        self,
        delay_min: float = DEFAULT_DELAY_MIN,
        delay_max: float = DEFAULT_DELAY_MAX,
        max_retries: int = DEFAULT_MAX_RETRIES,
        timeout: int = DEFAULT_TIMEOUT
    ):
        """
        Inicializa el scraper con la configuración especificada.

        Args:
            delay_min: Delay mínimo entre requests (segundos)
            delay_max: Delay máximo entre requests (segundos)
            max_retries: Número máximo de reintentos
            timeout: Timeout para requests (segundos)
        """
        self.delay_min = delay_min
        self.delay_max = delay_max
        self.max_retries = max_retries
        self.timeout = timeout

        # Inicializar User-Agent rotativo
        try:
            self.ua = UserAgent()
        except Exception:
            # Fallback si fake_useragent falla
            self.ua = None
            self._fallback_agents = [
                'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36',
                'Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36',
                'Mozilla/5.0 (Windows NT 10.0; Win64; x64; rv:121.0) Gecko/20100101 Firefox/121.0',
                'Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/605.1.15 (KHTML, like Gecko) Version/17.1 Safari/605.1.15',
            ]

        # Configurar logging para esta instancia
        self.logger = logging.getLogger(self.__class__.__name__)

        # Sesión de requests para reutilizar conexiones
        self.session = requests.Session()

        # Estadísticas de la sesión
        self.stats = {
            'requests_made': 0,
            'requests_failed': 0,
            'products_found': 0,
            'start_time': None,
            'end_time': None,
        }

    @property
    @abstractmethod
    def name(self) -> str:
        """Nombre del scraper (para logs y UI)"""
        pass

    @property
    @abstractmethod
    def base_url(self) -> str:
        """URL base del sitio web"""
        pass

    @abstractmethod
    def build_search_url(self, search_term: str, page: int = 1) -> str:
        """
        Construye la URL de búsqueda para el término dado.

        Args:
            search_term: Término de búsqueda
            page: Número de página (para paginación)

        Returns:
            URL completa de búsqueda
        """
        pass

    @abstractmethod
    def parse_products(self, soup: BeautifulSoup) -> List[ScrapedProduct]:
        """
        Extrae productos del HTML parseado.

        Args:
            soup: Objeto BeautifulSoup con el HTML

        Returns:
            Lista de productos extraídos
        """
        pass

    def get_random_user_agent(self) -> str:
        """
        Obtiene un User-Agent aleatorio.

        Returns:
            String del User-Agent
        """
        if self.ua:
            try:
                return self.ua.random
            except Exception:
                pass
        return random.choice(self._fallback_agents)

    def get_headers(self) -> Dict[str, str]:
        """
        Genera headers HTTP con User-Agent aleatorio.

        Returns:
            Diccionario de headers
        """
        return {
            'User-Agent': self.get_random_user_agent(),
            'Accept': 'text/html,application/xhtml+xml,application/xml;q=0.9,image/webp,*/*;q=0.8',
            'Accept-Language': 'es-CL,es;q=0.9,en;q=0.8',
            'Accept-Encoding': 'gzip, deflate, br',
            'Connection': 'keep-alive',
            'Upgrade-Insecure-Requests': '1',
            'Cache-Control': 'max-age=0',
        }

    def random_delay(self) -> None:
        """Aplica un delay aleatorio entre requests."""
        delay = random.uniform(self.delay_min, self.delay_max)
        self.logger.debug(f"Esperando {delay:.2f} segundos...")
        time.sleep(delay)

    def fetch_page(self, url: str) -> Optional[BeautifulSoup]:
        """
        Obtiene y parsea una página web con retry logic.

        Args:
            url: URL a obtener

        Returns:
            Objeto BeautifulSoup o None si falla
        """
        last_exception = None

        for attempt in range(1, self.max_retries + 1):
            try:
                self.logger.info(f"Obteniendo URL (intento {attempt}/{self.max_retries}): {url}")

                response = self.session.get(
                    url,
                    headers=self.get_headers(),
                    timeout=self.timeout
                )

                self.stats['requests_made'] += 1

                # Verificar código de respuesta
                response.raise_for_status()

                # Parsear HTML
                soup = BeautifulSoup(response.content, 'lxml')

                self.logger.info(f"✅ Página obtenida exitosamente ({len(response.content)} bytes)")
                return soup

            except requests.exceptions.Timeout:
                last_exception = "Timeout"
                self.logger.warning(f"⏱️ Timeout en intento {attempt}")

            except requests.exceptions.HTTPError as e:
                last_exception = str(e)
                self.logger.warning(f"🚫 Error HTTP en intento {attempt}: {e}")

                # Si es 404 o similar, no reintentar
                if response.status_code in [404, 403, 410]:
                    break

            except requests.exceptions.ConnectionError as e:
                last_exception = str(e)
                self.logger.warning(f"🔌 Error de conexión en intento {attempt}: {e}")

            except Exception as e:
                last_exception = str(e)
                self.logger.error(f"❌ Error inesperado en intento {attempt}: {e}")

            # Backoff exponencial antes de reintentar
            if attempt < self.max_retries:
                backoff = (2 ** attempt) + random.uniform(0, 1)
                self.logger.info(f"Esperando {backoff:.2f} segundos antes de reintentar...")
                time.sleep(backoff)

        self.stats['requests_failed'] += 1
        self.logger.error(f"❌ Falló después de {self.max_retries} intentos. Último error: {last_exception}")
        return None

    def scrape(self, search_term: str, max_pages: int = 1) -> List[ScrapedProduct]:
        """
        Ejecuta el scraping completo para un término de búsqueda.

        Args:
            search_term: Término a buscar
            max_pages: Número máximo de páginas a procesar

        Returns:
            Lista de productos encontrados
        """
        self.stats['start_time'] = datetime.utcnow()
        all_products = []

        self.logger.info(f"🚀 Iniciando scraping de '{search_term}' en {self.name}")

        for page in range(1, max_pages + 1):
            self.logger.info(f"📄 Procesando página {page}/{max_pages}")

            # Construir URL
            url = self.build_search_url(search_term, page)

            # Obtener página
            soup = self.fetch_page(url)

            if soup is None:
                self.logger.warning(f"No se pudo obtener la página {page}")
                continue

            # Extraer productos
            try:
                products = self.parse_products(soup)
                self.logger.info(f"📦 Encontrados {len(products)} productos en página {page}")
                all_products.extend(products)
            except Exception as e:
                self.logger.error(f"❌ Error parseando productos: {e}")

            # Delay entre páginas
            if page < max_pages:
                self.random_delay()

        self.stats['end_time'] = datetime.utcnow()
        self.stats['products_found'] = len(all_products)

        duration = (self.stats['end_time'] - self.stats['start_time']).total_seconds()
        self.logger.info(
            f"✅ Scraping completado: {len(all_products)} productos en {duration:.2f} segundos"
        )

        return all_products

    def get_stats(self) -> Dict[str, Any]:
        """
        Retorna estadísticas de la sesión de scraping.

        Returns:
            Diccionario con estadísticas
        """
        duration = None
        if self.stats['start_time'] and self.stats['end_time']:
            duration = (self.stats['end_time'] - self.stats['start_time']).total_seconds()

        return {
            **self.stats,
            'duration': duration,
            'success_rate': (
                (self.stats['requests_made'] - self.stats['requests_failed']) /
                max(self.stats['requests_made'], 1) * 100
            )
        }

    def __enter__(self):
        """Context manager entry."""
        return self

    def __exit__(self, exc_type, exc_val, exc_tb):
        """Context manager exit - cierra la sesión."""
        self.session.close()

    @staticmethod
    def clean_price(price_text: str) -> Optional[float]:
        """
        Limpia y convierte un texto de precio a float.

        Args:
            price_text: Texto del precio (ej: "$1.234.567")

        Returns:
            Precio como float o None si no se puede parsear
        """
        if not price_text:
            return None

        try:
            # Remover caracteres no numéricos excepto puntos y comas
            cleaned = price_text.strip()

            # Remover símbolos de moneda comunes
            for symbol in ['$', '€', '£', 'CLP', 'USD', '\xa0', ' ']:
                cleaned = cleaned.replace(symbol, '')

            # Determinar formato de miles/decimales
            # En Chile se usa punto para miles y coma para decimales
            if '.' in cleaned and ',' in cleaned:
                # Formato: 1.234,56
                cleaned = cleaned.replace('.', '').replace(',', '.')
            elif '.' in cleaned:
                # Podría ser 1.234 (miles) o 12.34 (decimales)
                # En precios chilenos, asumimos miles
                parts = cleaned.split('.')
                if len(parts[-1]) == 3:  # Es separador de miles
                    cleaned = cleaned.replace('.', '')
                # Si es otro caso, dejamos como está
            elif ',' in cleaned:
                # Formato: 1234,56 (decimal con coma)
                cleaned = cleaned.replace(',', '.')

            return float(cleaned)

        except (ValueError, AttributeError):
            return None

    @staticmethod
    def calculate_discount(current_price: float, original_price: Optional[float]) -> float:
        """
        Calcula el porcentaje de descuento.

        Args:
            current_price: Precio actual
            original_price: Precio original

        Returns:
            Porcentaje de descuento (0-100)
        """
        if not original_price or original_price <= 0:
            return 0.0

        if current_price >= original_price:
            return 0.0

        discount = ((original_price - current_price) / original_price) * 100
        return round(discount, 2)
