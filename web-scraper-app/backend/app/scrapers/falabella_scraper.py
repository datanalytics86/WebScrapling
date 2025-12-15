# Scraper Falabella Chile
# =======================
"""
Scraper específico para Falabella Chile.
Extrae productos de la sección de tecnología.
"""

import re
import json
from typing import List, Optional
from urllib.parse import urljoin, quote
from bs4 import BeautifulSoup

from .base_scraper import BaseScraper, ScrapedProduct


class FalabellaScraper(BaseScraper):
    """
    Scraper para Falabella Chile (falabella.com/falabella-cl)

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
        return "Falabella Chile"

    @property
    def base_url(self) -> str:
        return "https://www.falabella.com/falabella-cl"

    def build_search_url(self, search_term: str, page: int = 1) -> str:
        """
        Construye la URL de búsqueda de Falabella.

        Formato: https://www.falabella.com/falabella-cl/search?Ntt={término}&page={página}

        Args:
            search_term: Término de búsqueda
            page: Número de página

        Returns:
            URL de búsqueda completa
        """
        # Codificar término de búsqueda
        encoded_term = quote(search_term.strip())

        return f"{self.base_url}/search?Ntt={encoded_term}&page={page}"

    def get_headers(self) -> dict:
        """
        Obtiene headers específicos para Falabella.
        Falabella requiere headers adicionales.

        Returns:
            Diccionario de headers
        """
        headers = super().get_headers()
        headers.update({
            'Accept': 'text/html,application/xhtml+xml,application/xml;q=0.9,image/avif,image/webp,image/apng,*/*;q=0.8',
            'sec-ch-ua': '"Not_A Brand";v="8", "Chromium";v="120", "Google Chrome";v="120"',
            'sec-ch-ua-mobile': '?0',
            'sec-ch-ua-platform': '"Windows"',
            'Sec-Fetch-Dest': 'document',
            'Sec-Fetch-Mode': 'navigate',
            'Sec-Fetch-Site': 'none',
            'Sec-Fetch-User': '?1',
        })
        return headers

    def parse_products(self, soup: BeautifulSoup) -> List[ScrapedProduct]:
        """
        Extrae productos del HTML de Falabella.

        Args:
            soup: BeautifulSoup con el HTML de la página

        Returns:
            Lista de productos extraídos
        """
        products = []

        # Intentar extraer datos del JSON embebido (más confiable)
        json_products = self._extract_from_json(soup)
        if json_products:
            return json_products

        # Fallback: parsear HTML directamente
        # Buscar contenedores de productos
        product_cards = soup.select('div.pod-4_GRID')

        if not product_cards:
            product_cards = soup.select('div[data-pod]')

        if not product_cards:
            product_cards = soup.select('div.jsx-1833870204')

        if not product_cards:
            # Estructura alternativa
            product_cards = soup.select('div.search-results-4-grid div.pod')

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

    def _extract_from_json(self, soup: BeautifulSoup) -> List[ScrapedProduct]:
        """
        Intenta extraer productos del JSON embebido en la página.

        Args:
            soup: BeautifulSoup con el HTML

        Returns:
            Lista de productos o lista vacía si no se encuentra JSON
        """
        products = []

        # Buscar scripts con datos de productos
        scripts = soup.find_all('script', type='application/ld+json')

        for script in scripts:
            try:
                data = json.loads(script.string)

                # Buscar ItemList
                if isinstance(data, dict) and data.get('@type') == 'ItemList':
                    items = data.get('itemListElement', [])
                    for item in items:
                        product_data = item.get('item', item)
                        product = self._parse_json_product(product_data)
                        if product:
                            products.append(product)

                # Buscar Product individual
                elif isinstance(data, dict) and data.get('@type') == 'Product':
                    product = self._parse_json_product(data)
                    if product:
                        products.append(product)

                # Buscar array de productos
                elif isinstance(data, list):
                    for item in data:
                        if isinstance(item, dict) and item.get('@type') == 'Product':
                            product = self._parse_json_product(item)
                            if product:
                                products.append(product)

            except (json.JSONDecodeError, TypeError):
                continue

        return products

    def _parse_json_product(self, data: dict) -> Optional[ScrapedProduct]:
        """
        Parsea un producto desde datos JSON estructurados.

        Args:
            data: Diccionario con datos del producto

        Returns:
            ScrapedProduct o None
        """
        try:
            name = data.get('name', '')
            if not name:
                return None

            url = data.get('url', '')

            # Extraer precio
            offers = data.get('offers', {})
            if isinstance(offers, list):
                offers = offers[0] if offers else {}

            price = offers.get('price')
            if not price:
                return None

            current_price = float(price)

            # Imagen
            image = data.get('image', '')
            if isinstance(image, list):
                image = image[0] if image else ''

            return ScrapedProduct(
                external_id=data.get('sku'),
                name=name,
                url=url,
                current_price=current_price,
                original_price=None,
                discount=0.0,
                image_url=image,
                currency="CLP",
                in_stock=True
            )

        except (ValueError, KeyError, TypeError):
            return None

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
            card.select_one('b.pod-subTitle') or
            card.select_one('span.pod-subTitle') or
            card.select_one('a.pod-link span') or
            card.select_one('div.pod-details a') or
            card.select_one('b[class*="title"]')
        )

        if not name_elem:
            return None

        name = name_elem.get_text(strip=True)

        if not name:
            return None

        # Extraer URL
        url_elem = (
            card.select_one('a.pod-link') or
            card.select_one('a[href*="/product/"]') or
            card.select_one('div.pod-details a')
        )

        url = ''
        if url_elem:
            url = url_elem.get('href', '')
            if url and not url.startswith('http'):
                url = urljoin('https://www.falabella.com', url)

        # Extraer precio actual
        price_elem = (
            card.select_one('li.price-0 span') or
            card.select_one('span[data-internet-price]') or
            card.select_one('div.prices span.copy10') or
            card.select_one('ol.pod-prices li:first-child span')
        )

        if not price_elem:
            # Intentar con atributos de datos
            price_attr = card.get('data-price')
            if price_attr:
                current_price = self.clean_price(price_attr)
            else:
                return None
        else:
            current_price = self.clean_price(price_elem.get_text(strip=True))

        if not current_price or current_price <= 0:
            return None

        # Extraer precio original
        original_price = None
        original_price_elem = (
            card.select_one('li.price-1 span') or
            card.select_one('span[data-normal-price]') or
            card.select_one('span.copy10.primary.medium.line-through')
        )

        if original_price_elem:
            original_price = self.clean_price(original_price_elem.get_text(strip=True))

        # Extraer descuento
        discount = 0.0
        discount_elem = (
            card.select_one('span.discount-badge') or
            card.select_one('div.discount span') or
            card.select_one('span[class*="discount"]')
        )

        if discount_elem:
            discount_text = discount_elem.get_text(strip=True)
            match = re.search(r'(\d+)', discount_text)
            if match:
                discount = float(match.group(1))
        elif original_price and original_price > current_price:
            discount = self.calculate_discount(current_price, original_price)

        # Extraer imagen
        image_url = None
        img_elem = (
            card.select_one('img.jsx-1996933093') or
            card.select_one('img[data-src]') or
            card.select_one('img.pod-image') or
            card.select_one('picture img')
        )

        if img_elem:
            image_url = (
                img_elem.get('data-src') or
                img_elem.get('src', '')
            )

        # Extraer ID externo
        external_id = None
        if url:
            match = re.search(r'/product/(\d+)', url)
            if match:
                external_id = match.group(1)

        # Intentar obtener SKU de atributos
        if not external_id:
            external_id = card.get('data-sku') or card.get('data-product-id')

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
