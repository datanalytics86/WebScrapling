# Scraper Beneficios BCI Chile
# ============================
"""
Scraper específico para la página de beneficios de BCI Chile.
Extrae ofertas, descuentos y beneficios de tarjetas BCI desde bci.cl/beneficios.
"""

import re
import hashlib
from typing import List, Optional
from urllib.parse import urljoin
from bs4 import BeautifulSoup

from .base_scraper import BaseScraper, ScrapedProduct


class BciBenefitsScraper(BaseScraper):
    """
    Scraper para Beneficios BCI Chile (bci.cl/beneficios)

    Extrae:
    - Beneficios principales (Viajes, Restaurantes, Cuotas, Cashback)
    - Tarjetas BCI con sus ventajas de acumulación
    - Ofertas destacadas del hero carousel
    - Banners promocionales (huincha-beneficios)
    - Socios comerciales asociados
    """

    BASE = "https://www.bci.cl"

    # Categorías conocidas del sitio y sus rutas
    CATEGORY_PATHS = {
        "viajes": "/beneficios/beneficios-viajes",
        "restaurantes": "/beneficios/beneficios-restaurantes",
        "cuotas": "/beneficios/beneficios-cuotas",
    }

    @property
    def name(self) -> str:
        return "BCI Beneficios Chile"

    @property
    def base_url(self) -> str:
        return self.BASE

    # ------------------------------------------------------------------
    # URL construction
    # ------------------------------------------------------------------

    def build_search_url(self, search_term: str, page: int = 1) -> str:
        """
        Construye la URL según el término de búsqueda.

        Si search_term coincide con una categoría conocida se usa su ruta
        específica; en caso contrario se usa /beneficios (página general).
        La paginación no aplica en este sitio; se ignora page.
        """
        term = (search_term or "").strip().lower()
        path = self.CATEGORY_PATHS.get(term, "/beneficios")
        return f"{self.BASE}{path}"

    # ------------------------------------------------------------------
    # Parsing principal
    # ------------------------------------------------------------------

    def parse_products(self, soup: BeautifulSoup) -> List[ScrapedProduct]:
        """
        Extrae todos los beneficios disponibles de la página.
        Combina distintas secciones del sitio en una lista única de
        ScrapedProduct, usando 'discount' para el porcentaje de descuento
        y 'current_price' = 0 (los beneficios no tienen precio de producto).
        """
        products: List[ScrapedProduct] = []
        seen_ids: set = set()

        # 1. Ofertas del hero carousel
        products.extend(self._parse_carousel(soup))

        # 2. Banner promocional (huincha-beneficios)
        products.extend(self._parse_huincha(soup))

        # 3. Tarjetas BCI (acumulación / cashback)
        products.extend(self._parse_tarjetas(soup))

        # 4. Secciones principales (Viajes / Restaurantes / Cuotas)
        products.extend(self._parse_benefit_sections(soup))

        # 5. Socios comerciales (logos carousel)
        products.extend(self._parse_partner_logos(soup))

        # Deduplicar por external_id
        unique: List[ScrapedProduct] = []
        for p in products:
            if p.external_id and p.external_id in seen_ids:
                continue
            if p.external_id:
                seen_ids.add(p.external_id)
            unique.append(p)

        self.logger.info(f"BCI: {len(unique)} beneficios únicos extraídos")
        return unique

    # ------------------------------------------------------------------
    # Sección 1: Hero carousel
    # ------------------------------------------------------------------

    def _parse_carousel(self, soup: BeautifulSoup) -> List[ScrapedProduct]:
        products: List[ScrapedProduct] = []
        carousel = soup.select("#carouselExampleIndicators .carousel-item")

        for idx, item in enumerate(carousel):
            title_el = item.select_one("h1") or item.select_one(".card-body h2")
            desc_el = item.select_one("p")
            img_el = item.select_one("img.hero-bg-img") or item.select_one("img")
            link_el = item.select_one("a[href]")

            title = (title_el.get_text(strip=True) if title_el else "").strip()
            if not title:
                continue

            desc = desc_el.get_text(strip=True) if desc_el else ""
            name = f"{title} – {desc}" if desc else title

            url = self._abs_url(link_el) if link_el else f"{self.BASE}/beneficios"
            image = self._img_src(img_el)
            discount = self._extract_discount(name)

            products.append(ScrapedProduct(
                external_id=self._make_id("carousel", idx, title),
                name=name,
                url=url,
                current_price=0.0,
                original_price=None,
                discount=discount,
                image_url=image,
                currency="CLP",
                in_stock=True,
            ))

        return products

    # ------------------------------------------------------------------
    # Sección 2: Banner huincha-beneficios
    # ------------------------------------------------------------------

    def _parse_huincha(self, soup: BeautifulSoup) -> List[ScrapedProduct]:
        products: List[ScrapedProduct] = []
        strips = soup.select(".huincha-beneficios")

        for idx, strip in enumerate(strips):
            texts = [t.get_text(strip=True) for t in strip.select("p") if t.get_text(strip=True)]
            if not texts:
                continue

            name = " – ".join(texts)
            discount = self._extract_discount(name)

            products.append(ScrapedProduct(
                external_id=self._make_id("huincha", idx, name),
                name=name,
                url=f"{self.BASE}/beneficios",
                current_price=0.0,
                original_price=None,
                discount=discount,
                image_url=None,
                currency="CLP",
                in_stock=True,
            ))

        return products

    # ------------------------------------------------------------------
    # Sección 3: Tarjetas BCI – .box-destacados dentro de #tarjetas-acumulacion
    # Cada columna contiene: <img class="card"> (imagen principal),
    # <div class="tit"><h3> (título), <div class="caja-acumulacion-bcip"> (detalles + enlace)
    # ------------------------------------------------------------------

    def _parse_tarjetas(self, soup: BeautifulSoup) -> List[ScrapedProduct]:
        products: List[ScrapedProduct] = []
        container = soup.select_one("#tarjetas-acumulacion")
        if not container:
            return products

        boxes = container.select(".box-destacados")
        for idx, box in enumerate(boxes):
            # Título en h3 dentro de .tit
            title_el = box.select_one(".tit h3") or box.select_one("h3")
            title = title_el.get_text(strip=True) if title_el else ""
            if not title:
                continue

            # Imagen principal (img.card dentro del box)
            img_el = box.select_one("img.card") or box.select_one("img")
            image = self._img_src(img_el)

            # Detalle + enlace dentro de .caja-acumulacion-bcip
            info_box = box.select_one(".caja-acumulacion-bcip")
            link_el = info_box.select_one("a[href]") if info_box else None
            url = self._abs_url(link_el) if link_el else f"{self.BASE}/beneficios"

            # Texto del botón / enlace como descripción
            link_text = link_el.get_text(strip=True) if link_el else ""
            name = f"{title} – {link_text}" if link_text else title

            discount = self._extract_discount(name)

            products.append(ScrapedProduct(
                external_id=self._make_id("tarjeta", idx, title),
                name=name,
                url=url,
                current_price=0.0,
                original_price=None,
                discount=discount,
                image_url=image,
                currency="CLP",
                in_stock=True,
            ))

        return products

    # ------------------------------------------------------------------
    # Sección 4: Banner captura + secciones con beneficios detallados
    # Parsea section#banner-captura y otros section con listas de beneficios (li)
    # ------------------------------------------------------------------

    def _parse_benefit_sections(self, soup: BeautifulSoup) -> List[ScrapedProduct]:
        products: List[ScrapedProduct] = []

        # Banner principal con resumen de beneficios
        banner = soup.select_one("section#banner-captura")
        if banner:
            heading = banner.select_one("p.h1") or banner.select_one("h1") or banner.select_one("h2")
            heading_text = heading.get_text(strip=True) if heading else "Beneficios Tarjetas BCI"

            items = banner.select("ul.list-check li")
            for idx, li in enumerate(items):
                text = li.get_text(strip=True)
                if not text:
                    continue

                name = f"{heading_text} – {text}"
                discount = self._extract_discount(text)

                img_el = banner.select_one("img")
                image = self._img_src(img_el)

                products.append(ScrapedProduct(
                    external_id=self._make_id("banner", idx, text),
                    name=name,
                    url=f"{self.BASE}/personas/abrir-cuenta-corriente",
                    current_price=0.0,
                    original_price=None,
                    discount=discount,
                    image_url=image,
                    currency="CLP",
                    in_stock=True,
                ))

        # Enlaces directos a beneficios específicos (las rutas conocidas del sitio)
        benefit_links = soup.select('a[href*="/beneficios/beneficios"]')
        seen_hrefs: set = set()
        for idx, link in enumerate(benefit_links):
            href = link.get("href", "").strip()
            if not href or href in seen_hrefs:
                continue
            seen_hrefs.add(href)

            text = link.get_text(strip=True)
            if not text:
                continue

            url = self._abs_url(link)
            products.append(ScrapedProduct(
                external_id=self._make_id("enlace", idx, text),
                name=f"Beneficio – {text}",
                url=url,
                current_price=0.0,
                original_price=None,
                discount=0.0,
                image_url=None,
                currency="CLP",
                in_stock=True,
            ))

        return products

    # ------------------------------------------------------------------
    # Sección 5: Socios comerciales – .logo-item son <img> directamente
    # ------------------------------------------------------------------

    def _parse_partner_logos(self, soup: BeautifulSoup) -> List[ScrapedProduct]:
        products: List[ScrapedProduct] = []
        logos = soup.select("img.logo-item")

        seen_names: set = set()
        for idx, img in enumerate(logos):
            alt = (img.get("alt") or "").strip()
            src = img.get("src") or ""

            # Extraer nombre: "Logo Starbucks" → "Starbucks"
            name_raw = re.sub(r"(?i)^logo\s*", "", alt).strip()
            if not name_raw and src:
                filename = src.split("/")[-1].split(".")[0]
                name_raw = filename.replace("-", " ").replace("_", " ").title()

            if not name_raw or name_raw in seen_names:
                continue
            seen_names.add(name_raw)

            products.append(ScrapedProduct(
                external_id=self._make_id("socio", idx, name_raw),
                name=f"Socio Comercial – {name_raw}",
                url=f"{self.BASE}/beneficios",
                current_price=0.0,
                original_price=None,
                discount=0.0,
                image_url=self._abs_url_str(src),
                currency="CLP",
                in_stock=True,
            ))

        return products

    # ------------------------------------------------------------------
    # Helpers
    # ------------------------------------------------------------------

    @staticmethod
    def _extract_discount(text: str) -> float:
        """Extrae el primer porcentaje encontrado en el texto (ej: '50% descuento' → 50.0)."""
        match = re.search(r"(\d+(?:\.\d+)?)\s*%", text)
        return float(match.group(1)) if match else 0.0

    def _abs_url(self, tag) -> str:
        """Retorna URL absoluta de un tag con href."""
        href = tag.get("href", "") if tag else ""
        return urljoin(self.BASE, href) if href else f"{self.BASE}/beneficios"

    def _abs_url_str(self, url: str) -> Optional[str]:
        """Convierte una URL relativa a absoluta."""
        if not url:
            return None
        return urljoin(self.BASE, url)

    @staticmethod
    def _img_src(img_el) -> Optional[str]:
        """Obtiene src de un elemento img (soporta data-src como fallback)."""
        if not img_el:
            return None
        return img_el.get("data-src") or img_el.get("src")

    @staticmethod
    def _make_id(prefix: str, index: int, text: str) -> str:
        """Genera un external_id determinista a partir de prefix + texto."""
        slug = re.sub(r"[^a-zA-Z0-9]", "", text.lower())[:40]
        return f"{prefix}_{index}_{slug}"
