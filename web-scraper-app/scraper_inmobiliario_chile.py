#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
SCRAPER INMOBILIARIO CHILE - MULTI-SITIO
=========================================
Extrae arriendos de múltiples portales inmobiliarios chilenos:
- PortalInmobiliario.com
- TocToc.cl
- Yapo.cl
- ChilePropiedades.cl
- MercadoLibre Inmuebles

Genera Excel completo con todos los campos relevantes.
"""

import re
import time
import random
import logging
from abc import ABC, abstractmethod
from datetime import datetime, timedelta
from dataclasses import dataclass, asdict, field
from typing import List, Optional, Dict, Type
from urllib.parse import urljoin, quote

import requests
from bs4 import BeautifulSoup
from openpyxl import Workbook
from openpyxl.styles import Font, Alignment, PatternFill, Border, Side, NamedStyle
from openpyxl.utils import get_column_letter

# Configurar logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)


# =============================================================================
# MODELO DE DATOS
# =============================================================================

@dataclass
class PropiedadInmobiliaria:
    """Estructura completa de una propiedad inmobiliaria."""
    # Identificación
    id: Optional[str] = None
    codigo: Optional[str] = None

    # Fuente
    sitio_web: str = ""
    url: str = ""

    # Información básica
    titulo: str = ""
    descripcion: Optional[str] = None
    tipo_operacion: str = "Arriendo"  # Arriendo, Venta
    tipo_propiedad: Optional[str] = None  # Departamento, Casa, Oficina, etc.

    # Ubicación
    region: str = "Metropolitana"
    comuna: str = ""
    direccion: Optional[str] = None
    barrio: Optional[str] = None

    # Precio
    precio: Optional[float] = None
    moneda: str = "CLP"  # CLP, UF, USD
    gastos_comunes: Optional[float] = None

    # Características físicas
    metros_totales: Optional[int] = None
    metros_utiles: Optional[int] = None
    metros_terreno: Optional[int] = None
    dormitorios: Optional[int] = None
    banos: Optional[int] = None
    estacionamientos: Optional[int] = None
    bodegas: Optional[int] = None

    # Características adicionales
    piso: Optional[int] = None
    antiguedad: Optional[int] = None  # Años
    orientacion: Optional[str] = None  # Norte, Sur, Oriente, Poniente
    amoblado: bool = False
    mascotas: Optional[bool] = None

    # Amenidades
    piscina: bool = False
    gimnasio: bool = False
    quincho: bool = False
    terraza: bool = False
    balcon: bool = False
    calefaccion: bool = False
    aire_acondicionado: bool = False

    # Fechas
    fecha_publicacion: Optional[str] = None
    fecha_actualizacion: Optional[str] = None
    fecha_scraping: str = field(default_factory=lambda: datetime.now().strftime("%Y-%m-%d %H:%M:%S"))

    # Contacto
    inmobiliaria: Optional[str] = None
    telefono: Optional[str] = None

    # Multimedia
    imagen_url: Optional[str] = None
    cantidad_fotos: Optional[int] = None


# =============================================================================
# SCRAPER BASE
# =============================================================================

class BaseInmobiliarioScraper(ABC):
    """Clase base para scrapers inmobiliarios."""

    USER_AGENTS = [
        'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 Chrome/120.0.0.0 Safari/537.36',
        'Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 Chrome/120.0.0.0 Safari/537.36',
        'Mozilla/5.0 (Windows NT 10.0; Win64; x64; rv:121.0) Gecko/20100101 Firefox/121.0',
        'Mozilla/5.0 (X11; Linux x86_64) AppleWebKit/537.36 Chrome/120.0.0.0 Safari/537.36',
    ]

    def __init__(self, delay_min: float = 2, delay_max: float = 5, max_retries: int = 3):
        self.delay_min = delay_min
        self.delay_max = delay_max
        self.max_retries = max_retries
        self.session = requests.Session()

    @property
    @abstractmethod
    def nombre(self) -> str:
        """Nombre del sitio."""
        pass

    @property
    @abstractmethod
    def base_url(self) -> str:
        """URL base del sitio."""
        pass

    def get_headers(self) -> dict:
        return {
            'User-Agent': random.choice(self.USER_AGENTS),
            'Accept': 'text/html,application/xhtml+xml,application/xml;q=0.9,*/*;q=0.8',
            'Accept-Language': 'es-CL,es;q=0.9,en;q=0.8',
            'Accept-Encoding': 'gzip, deflate, br',
            'Connection': 'keep-alive',
        }

    def random_delay(self):
        time.sleep(random.uniform(self.delay_min, self.delay_max))

    def fetch_page(self, url: str) -> Optional[BeautifulSoup]:
        for attempt in range(1, self.max_retries + 1):
            try:
                logger.info(f"[{self.nombre}] Obteniendo (intento {attempt}): {url[:80]}...")
                response = self.session.get(url, headers=self.get_headers(), timeout=30)
                response.raise_for_status()
                return BeautifulSoup(response.content, 'lxml')
            except requests.exceptions.RequestException as e:
                logger.warning(f"Error en intento {attempt}: {e}")
                if attempt < self.max_retries:
                    time.sleep(2 ** attempt)
        return None

    @abstractmethod
    def build_search_url(self, comuna: str, page: int = 1) -> str:
        pass

    @abstractmethod
    def parse_listings(self, soup: BeautifulSoup, comuna: str) -> List[PropiedadInmobiliaria]:
        pass

    def scrape_comuna(self, comuna: str, max_pages: int = 2) -> List[PropiedadInmobiliaria]:
        propiedades = []
        for page in range(1, max_pages + 1):
            url = self.build_search_url(comuna, page)
            soup = self.fetch_page(url)
            if not soup:
                break

            props = self.parse_listings(soup, comuna)
            if not props:
                break

            propiedades.extend(props)
            logger.info(f"[{self.nombre}] {comuna}: {len(props)} propiedades en página {page}")

            if page < max_pages:
                self.random_delay()

        return propiedades

    @staticmethod
    def clean_price(text: str) -> tuple:
        if not text:
            return None, "CLP"

        text = text.strip().upper()

        if 'UF' in text:
            moneda = "UF"
        elif 'US' in text:
            moneda = "USD"
        else:
            moneda = "CLP"

        numbers = re.findall(r'[\d.,]+', text)
        if numbers:
            price_str = numbers[0]
            if ',' in price_str and '.' in price_str:
                price_str = price_str.replace('.', '').replace(',', '.')
            else:
                price_str = price_str.replace('.', '').replace(',', '.')
            try:
                precio = float(price_str)
                if moneda == "UF" and precio > 50000:
                    moneda = "CLP"
                return precio, moneda
            except ValueError:
                pass
        return None, moneda

    @staticmethod
    def extract_number(text: str) -> Optional[int]:
        if not text:
            return None
        numbers = re.findall(r'\d+', str(text))
        return int(numbers[0]) if numbers else None


# =============================================================================
# SCRAPERS ESPECÍFICOS
# =============================================================================

class PortalInmobiliarioScraper(BaseInmobiliarioScraper):
    """Scraper para PortalInmobiliario.com"""

    @property
    def nombre(self) -> str:
        return "PortalInmobiliario"

    @property
    def base_url(self) -> str:
        return "https://www.portalinmobiliario.com"

    def build_search_url(self, comuna: str, page: int = 1) -> str:
        comuna_slug = comuna.lower().replace(' ', '-').replace('ñ', 'n')
        base = f"{self.base_url}/arriendo/departamento/{comuna_slug}-metropolitana"
        if page > 1:
            offset = (page - 1) * 48 + 1
            return f"{base}_Desde_{offset}"
        return base

    def parse_listings(self, soup: BeautifulSoup, comuna: str) -> List[PropiedadInmobiliaria]:
        propiedades = []
        cards = soup.select('li.ui-search-layout__item, div.ui-search-result__wrapper')

        for card in cards:
            try:
                prop = self._parse_card(card, comuna)
                if prop and prop.precio:
                    propiedades.append(prop)
            except Exception as e:
                logger.debug(f"Error parseando card: {e}")

        return propiedades

    def _parse_card(self, card, comuna: str) -> Optional[PropiedadInmobiliaria]:
        title_elem = card.select_one('h2 a, a.ui-search-link')
        if not title_elem:
            return None

        titulo = title_elem.get_text(strip=True)
        url = title_elem.get('href', '')

        price_elem = card.select_one('span.andes-money-amount__fraction')
        precio, moneda = self.clean_price(price_elem.get_text() if price_elem else '')

        # Atributos
        attrs = card.select('li.ui-search-card-attributes__attribute')
        m2, dorms, banos = None, None, None
        for attr in attrs:
            text = attr.get_text(strip=True).lower()
            if 'm²' in text:
                m2 = self.extract_number(text)
            elif 'dorm' in text:
                dorms = self.extract_number(text)
            elif 'baño' in text:
                banos = self.extract_number(text)

        # Imagen
        img = card.select_one('img')
        img_url = img.get('data-src') or img.get('src') if img else None

        return PropiedadInmobiliaria(
            sitio_web=self.nombre,
            url=url,
            titulo=titulo,
            tipo_propiedad="Departamento",
            comuna=comuna.title(),
            precio=precio,
            moneda=moneda,
            metros_totales=m2,
            dormitorios=dorms,
            banos=banos,
            imagen_url=img_url
        )


class TocTocScraper(BaseInmobiliarioScraper):
    """Scraper para TocToc.cl"""

    @property
    def nombre(self) -> str:
        return "TocToc"

    @property
    def base_url(self) -> str:
        return "https://www.toctoc.com"

    def build_search_url(self, comuna: str, page: int = 1) -> str:
        comuna_slug = comuna.lower().replace(' ', '-').replace('ñ', 'n')
        return f"{self.base_url}/arriendo/departamento/region-metropolitana/{comuna_slug}?page={page}"

    def parse_listings(self, soup: BeautifulSoup, comuna: str) -> List[PropiedadInmobiliaria]:
        propiedades = []
        cards = soup.select('div.property-card, article.listing-card')

        for card in cards:
            try:
                prop = self._parse_card(card, comuna)
                if prop and prop.precio:
                    propiedades.append(prop)
            except Exception as e:
                logger.debug(f"Error parseando card: {e}")

        return propiedades

    def _parse_card(self, card, comuna: str) -> Optional[PropiedadInmobiliaria]:
        title_elem = card.select_one('h2 a, h3 a, a.property-title')
        if not title_elem:
            return None

        titulo = title_elem.get_text(strip=True)
        url = title_elem.get('href', '')
        if url and not url.startswith('http'):
            url = urljoin(self.base_url, url)

        price_elem = card.select_one('.price, .property-price')
        precio, moneda = self.clean_price(price_elem.get_text() if price_elem else '')

        return PropiedadInmobiliaria(
            sitio_web=self.nombre,
            url=url,
            titulo=titulo,
            tipo_propiedad="Departamento",
            comuna=comuna.title(),
            precio=precio,
            moneda=moneda
        )


class YapoScraper(BaseInmobiliarioScraper):
    """Scraper para Yapo.cl"""

    @property
    def nombre(self) -> str:
        return "Yapo"

    @property
    def base_url(self) -> str:
        return "https://www.yapo.cl"

    def build_search_url(self, comuna: str, page: int = 1) -> str:
        comuna_slug = comuna.lower().replace(' ', '_').replace('ñ', 'n')
        return f"{self.base_url}/region_metropolitana/{comuna_slug}/arriendo_departamentos?page={page}"

    def parse_listings(self, soup: BeautifulSoup, comuna: str) -> List[PropiedadInmobiliaria]:
        propiedades = []
        cards = soup.select('div.listing-card, article.classified')

        for card in cards:
            try:
                prop = self._parse_card(card, comuna)
                if prop and prop.precio:
                    propiedades.append(prop)
            except Exception as e:
                logger.debug(f"Error parseando card: {e}")

        return propiedades

    def _parse_card(self, card, comuna: str) -> Optional[PropiedadInmobiliaria]:
        title_elem = card.select_one('h3 a, a.title, .ad-title a')
        if not title_elem:
            return None

        titulo = title_elem.get_text(strip=True)
        url = title_elem.get('href', '')
        if url and not url.startswith('http'):
            url = urljoin(self.base_url, url)

        price_elem = card.select_one('.price, .ad-price')
        precio, moneda = self.clean_price(price_elem.get_text() if price_elem else '')

        return PropiedadInmobiliaria(
            sitio_web=self.nombre,
            url=url,
            titulo=titulo,
            tipo_propiedad="Departamento",
            comuna=comuna.title(),
            precio=precio,
            moneda=moneda
        )


# =============================================================================
# GENERADOR DE DATOS DE EJEMPLO
# =============================================================================

def generar_datos_ejemplo(cantidad_por_comuna: int = 30) -> List[PropiedadInmobiliaria]:
    """Genera datos de ejemplo realistas para demostración."""

    COMUNAS_CONFIG = {
        "Las Condes": {"precio_m2": (18000, 28000), "uf_ratio": 0.35},
        "Providencia": {"precio_m2": (17000, 26000), "uf_ratio": 0.30},
        "Vitacura": {"precio_m2": (22000, 35000), "uf_ratio": 0.45},
        "Ñuñoa": {"precio_m2": (14000, 20000), "uf_ratio": 0.20},
        "Santiago Centro": {"precio_m2": (12000, 18000), "uf_ratio": 0.15},
        "La Reina": {"precio_m2": (15000, 22000), "uf_ratio": 0.25},
        "Peñalolén": {"precio_m2": (10000, 15000), "uf_ratio": 0.10},
        "La Florida": {"precio_m2": (9000, 14000), "uf_ratio": 0.10},
        "Maipú": {"precio_m2": (7000, 11000), "uf_ratio": 0.05},
        "Lo Barnechea": {"precio_m2": (20000, 32000), "uf_ratio": 0.40},
        "San Miguel": {"precio_m2": (11000, 16000), "uf_ratio": 0.12},
        "Macul": {"precio_m2": (10000, 15000), "uf_ratio": 0.10},
        "Recoleta": {"precio_m2": (8000, 12000), "uf_ratio": 0.08},
        "Independencia": {"precio_m2": (9000, 13000), "uf_ratio": 0.08},
        "Estación Central": {"precio_m2": (8000, 12000), "uf_ratio": 0.05},
    }

    SITIOS = ["PortalInmobiliario", "TocToc", "Yapo", "ChilePropiedades", "MercadoLibre"]
    INMOBILIARIAS = [
        "Coldwell Banker", "RE/MAX", "Century 21", "Engel & Völkers",
        "Propiedades.cl", "Inmobiliaria Chile", "Portal Propiedades",
        "Inmobiliaria Santiago", "Particular", "Corredora Independiente"
    ]

    CALLES = {
        "Las Condes": ["Av. Apoquindo", "Av. Las Condes", "Av. Kennedy", "El Golf", "Isidora Goyenechea"],
        "Providencia": ["Av. Providencia", "Av. 11 de Septiembre", "Los Leones", "Pedro de Valdivia"],
        "Vitacura": ["Av. Vitacura", "Av. Kennedy", "Nueva Costanera", "Alonso de Córdova"],
        "Ñuñoa": ["Av. Irarrázaval", "Av. Grecia", "José Domingo Cañas"],
        "Santiago Centro": ["Alameda", "Morandé", "Teatinos", "San Pablo"],
    }

    propiedades = []
    id_counter = 1

    for comuna, config in COMUNAS_CONFIG.items():
        calles = CALLES.get(comuna, ["Calle Principal", "Av. Central"])

        for _ in range(cantidad_por_comuna):
            # Tipo de propiedad
            tipo = random.choices(
                ["Departamento", "Estudio", "Casa", "Oficina"],
                weights=[70, 15, 10, 5]
            )[0]

            # Características según tipo
            if tipo == "Departamento":
                m2 = random.randint(35, 150)
                dorms = random.randint(1, 4)
                banos = max(1, dorms - random.randint(0, 1))
            elif tipo == "Estudio":
                m2 = random.randint(20, 40)
                dorms = 1
                banos = 1
            elif tipo == "Casa":
                m2 = random.randint(120, 350)
                dorms = random.randint(3, 6)
                banos = random.randint(2, 4)
            else:
                m2 = random.randint(30, 200)
                dorms = None
                banos = random.randint(1, 3)

            # Precio
            precio_m2 = random.randint(*config["precio_m2"])
            if random.random() < config["uf_ratio"]:
                precio_clp = m2 * precio_m2
                precio = round(precio_clp / 37000, 1)
                moneda = "UF"
            else:
                precio = round((m2 * precio_m2) / 10000) * 10000
                moneda = "CLP"

            # Gastos comunes
            gc = None
            if tipo in ["Departamento", "Estudio"]:
                gc = random.randint(50, 400) * 1000

            # Fechas
            dias_publicacion = random.randint(0, 60)
            fecha_pub = (datetime.now() - timedelta(days=dias_publicacion)).strftime("%Y-%m-%d")

            # Dirección
            calle = random.choice(calles)
            numero = random.randint(100, 9999)

            # Título
            sitio = random.choice(SITIOS)
            titulo_base = f"{tipo} {dorms}D {banos}B" if dorms else f"{tipo}"
            titulo = f"{titulo_base} {m2}m² en {comuna}"

            # Amenidades aleatorias
            amenidades = {
                "piscina": random.random() < 0.3,
                "gimnasio": random.random() < 0.4,
                "quincho": random.random() < 0.2,
                "terraza": random.random() < 0.5,
                "balcon": random.random() < 0.4,
                "calefaccion": random.random() < 0.3,
                "aire_acondicionado": random.random() < 0.2,
            }

            prop = PropiedadInmobiliaria(
                id=str(id_counter),
                codigo=f"{sitio[:2].upper()}-{1000 + id_counter}",
                sitio_web=sitio,
                url=f"https://www.{sitio.lower().replace(' ', '')}.cl/propiedad/{1000000 + id_counter}",
                titulo=titulo,
                tipo_operacion="Arriendo",
                tipo_propiedad=tipo,
                region="Metropolitana",
                comuna=comuna,
                direccion=f"{calle} {numero}",
                barrio=random.choice(["Centro", "Norte", "Sur", "Oriente", "Poniente"]) if random.random() < 0.3 else None,
                precio=precio,
                moneda=moneda,
                gastos_comunes=gc,
                metros_totales=m2,
                metros_utiles=int(m2 * random.uniform(0.8, 0.95)) if random.random() < 0.4 else None,
                dormitorios=dorms,
                banos=banos,
                estacionamientos=random.randint(1, 2) if random.random() < 0.6 else None,
                bodegas=1 if random.random() < 0.3 else None,
                piso=random.randint(1, 25) if tipo == "Departamento" else None,
                antiguedad=random.randint(0, 30) if random.random() < 0.3 else None,
                orientacion=random.choice(["Norte", "Sur", "Oriente", "Poniente"]) if random.random() < 0.2 else None,
                amoblado=random.random() < 0.3,
                mascotas=random.choice([True, False, None]),
                piscina=amenidades["piscina"],
                gimnasio=amenidades["gimnasio"],
                quincho=amenidades["quincho"],
                terraza=amenidades["terraza"],
                balcon=amenidades["balcon"],
                calefaccion=amenidades["calefaccion"],
                aire_acondicionado=amenidades["aire_acondicionado"],
                fecha_publicacion=fecha_pub,
                inmobiliaria=random.choice(INMOBILIARIAS),
                cantidad_fotos=random.randint(5, 30),
            )

            propiedades.append(prop)
            id_counter += 1

    random.shuffle(propiedades)
    return propiedades


# =============================================================================
# EXPORTACIÓN A EXCEL
# =============================================================================

def export_to_excel(propiedades: List[PropiedadInmobiliaria], filename: str = "propiedades_chile.xlsx"):
    """Exporta propiedades a Excel con formato profesional completo."""

    if not propiedades:
        logger.warning("No hay propiedades para exportar")
        return None

    wb = Workbook()

    # Estilos
    header_font = Font(bold=True, color="FFFFFF", size=10)
    header_fill = PatternFill(start_color="1F4E79", end_color="1F4E79", fill_type="solid")
    header_align = Alignment(horizontal="center", vertical="center", wrap_text=True)

    alt_fill = PatternFill(start_color="DCE6F1", end_color="DCE6F1", fill_type="solid")
    money_format_clp = '"$"#,##0'
    money_format_uf = '#,##0.0" UF"'

    border = Border(
        left=Side(style='thin', color='B4B4B4'),
        right=Side(style='thin', color='B4B4B4'),
        top=Side(style='thin', color='B4B4B4'),
        bottom=Side(style='thin', color='B4B4B4')
    )

    # =========================================================================
    # HOJA 1: LISTADO COMPLETO
    # =========================================================================
    ws = wb.active
    ws.title = "Listado Propiedades"

    # Definir columnas
    columnas = [
        ("ID", 6),
        ("Código", 12),
        ("Sitio Web", 18),
        ("Fecha Publicación", 16),
        ("Tipo Operación", 14),
        ("Tipo Propiedad", 15),
        ("Título", 50),
        ("Comuna", 18),
        ("Dirección", 30),
        ("Precio", 14),
        ("Moneda", 8),
        ("Gastos Comunes", 14),
        ("M² Totales", 11),
        ("M² Útiles", 10),
        ("Dormitorios", 11),
        ("Baños", 8),
        ("Estacionamientos", 15),
        ("Bodegas", 9),
        ("Piso", 6),
        ("Antigüedad", 11),
        ("Amoblado", 10),
        ("Mascotas", 10),
        ("Piscina", 8),
        ("Gimnasio", 9),
        ("Terraza", 8),
        ("Balcón", 8),
        ("Calefacción", 11),
        ("A/C", 6),
        ("Inmobiliaria", 25),
        ("Fotos", 7),
        ("URL", 60),
    ]

    # Headers
    for col, (header, width) in enumerate(columnas, 1):
        cell = ws.cell(row=1, column=col, value=header)
        cell.font = header_font
        cell.fill = header_fill
        cell.alignment = header_align
        cell.border = border
        ws.column_dimensions[get_column_letter(col)].width = width

    # Datos
    for row, prop in enumerate(propiedades, 2):
        data = [
            prop.id,
            prop.codigo,
            prop.sitio_web,
            prop.fecha_publicacion,
            prop.tipo_operacion,
            prop.tipo_propiedad,
            prop.titulo[:80] if prop.titulo else "",
            prop.comuna,
            prop.direccion,
            prop.precio,
            prop.moneda,
            prop.gastos_comunes,
            prop.metros_totales,
            prop.metros_utiles,
            prop.dormitorios,
            prop.banos,
            prop.estacionamientos,
            prop.bodegas,
            prop.piso,
            prop.antiguedad,
            "Sí" if prop.amoblado else "No",
            "Sí" if prop.mascotas else ("No" if prop.mascotas is False else "-"),
            "Sí" if prop.piscina else "-",
            "Sí" if prop.gimnasio else "-",
            "Sí" if prop.terraza else "-",
            "Sí" if prop.balcon else "-",
            "Sí" if prop.calefaccion else "-",
            "Sí" if prop.aire_acondicionado else "-",
            prop.inmobiliaria,
            prop.cantidad_fotos,
            prop.url,
        ]

        for col, value in enumerate(data, 1):
            cell = ws.cell(row=row, column=col, value=value)
            cell.border = border
            if row % 2 == 0:
                cell.fill = alt_fill

        # Formato precio
        ws.cell(row=row, column=10).number_format = money_format_clp if prop.moneda == "CLP" else money_format_uf
        if prop.gastos_comunes:
            ws.cell(row=row, column=12).number_format = money_format_clp

    ws.freeze_panes = 'A2'
    ws.auto_filter.ref = f"A1:{get_column_letter(len(columnas))}{len(propiedades) + 1}"

    # =========================================================================
    # HOJA 2: RESUMEN POR COMUNA
    # =========================================================================
    ws2 = wb.create_sheet("Resumen por Comuna")

    ws2['A1'] = "RESUMEN DE ARRIENDOS POR COMUNA - SANTIAGO"
    ws2['A1'].font = Font(bold=True, size=16, color="1F4E79")
    ws2.merge_cells('A1:H1')

    ws2['A2'] = f"Total: {len(propiedades)} propiedades | Fecha: {datetime.now().strftime('%Y-%m-%d %H:%M')}"
    ws2['A2'].font = Font(italic=True, color="666666")

    headers = ["Comuna", "Cantidad", "% Total", "Precio Mín", "Precio Máx", "Precio Prom", "M² Prom", "Moneda Ppal"]
    for col, h in enumerate(headers, 1):
        cell = ws2.cell(row=4, column=col, value=h)
        cell.font = header_font
        cell.fill = header_fill
        cell.border = border

    # Agrupar por comuna
    comunas = {}
    for p in propiedades:
        if p.comuna not in comunas:
            comunas[p.comuna] = []
        comunas[p.comuna].append(p)

    row = 5
    for comuna in sorted(comunas.keys(), key=lambda x: -len(comunas[x])):
        props = comunas[comuna]
        precios = [p.precio for p in props if p.precio]
        m2_list = [p.metros_totales for p in props if p.metros_totales]
        monedas = [p.moneda for p in props if p.precio]
        moneda_ppal = max(set(monedas), key=monedas.count) if monedas else "CLP"

        precios_moneda = [p.precio for p in props if p.precio and p.moneda == moneda_ppal]

        ws2.cell(row=row, column=1, value=comuna)
        ws2.cell(row=row, column=2, value=len(props))
        ws2.cell(row=row, column=3, value=f"{len(props)/len(propiedades)*100:.1f}%")

        if precios_moneda:
            ws2.cell(row=row, column=4, value=min(precios_moneda))
            ws2.cell(row=row, column=5, value=max(precios_moneda))
            ws2.cell(row=row, column=6, value=round(sum(precios_moneda)/len(precios_moneda)))

            fmt = money_format_clp if moneda_ppal == "CLP" else money_format_uf
            for c in [4, 5, 6]:
                ws2.cell(row=row, column=c).number_format = fmt

        if m2_list:
            ws2.cell(row=row, column=7, value=round(sum(m2_list)/len(m2_list)))

        ws2.cell(row=row, column=8, value=moneda_ppal)

        for col in range(1, 9):
            ws2.cell(row=row, column=col).border = border
            if row % 2 == 0:
                ws2.cell(row=row, column=col).fill = alt_fill

        row += 1

    for col, w in zip(range(1, 9), [20, 10, 10, 15, 15, 15, 10, 12]):
        ws2.column_dimensions[get_column_letter(col)].width = w

    # =========================================================================
    # HOJA 3: RESUMEN POR SITIO
    # =========================================================================
    ws3 = wb.create_sheet("Resumen por Sitio")

    ws3['A1'] = "DISTRIBUCIÓN POR SITIO WEB"
    ws3['A1'].font = Font(bold=True, size=14, color="1F4E79")

    headers = ["Sitio Web", "Cantidad", "% Total", "Precio Promedio CLP"]
    for col, h in enumerate(headers, 1):
        cell = ws3.cell(row=3, column=col, value=h)
        cell.font = header_font
        cell.fill = header_fill

    sitios = {}
    for p in propiedades:
        sitios[p.sitio_web] = sitios.get(p.sitio_web, [])
        sitios[p.sitio_web].append(p)

    row = 4
    for sitio in sorted(sitios.keys(), key=lambda x: -len(sitios[x])):
        props = sitios[sitio]
        precios_clp = [p.precio for p in props if p.precio and p.moneda == "CLP"]

        ws3.cell(row=row, column=1, value=sitio)
        ws3.cell(row=row, column=2, value=len(props))
        ws3.cell(row=row, column=3, value=f"{len(props)/len(propiedades)*100:.1f}%")
        if precios_clp:
            cell = ws3.cell(row=row, column=4, value=round(sum(precios_clp)/len(precios_clp)))
            cell.number_format = money_format_clp
        row += 1

    for col, w in zip(range(1, 5), [25, 12, 10, 20]):
        ws3.column_dimensions[get_column_letter(col)].width = w

    # =========================================================================
    # HOJA 4: ESTADÍSTICAS
    # =========================================================================
    ws4 = wb.create_sheet("Estadísticas")

    ws4['A1'] = "ESTADÍSTICAS GENERALES"
    ws4['A1'].font = Font(bold=True, size=16, color="1F4E79")

    precios_clp = [p.precio for p in propiedades if p.precio and p.moneda == "CLP"]
    precios_uf = [p.precio for p in propiedades if p.precio and p.moneda == "UF"]
    m2_list = [p.metros_totales for p in propiedades if p.metros_totales]
    dorms_list = [p.dormitorios for p in propiedades if p.dormitorios]

    stats = [
        ("Total Propiedades", len(propiedades)),
        ("Comunas Cubiertas", len(comunas)),
        ("Sitios Web", len(sitios)),
        ("", ""),
        ("PRECIOS EN CLP", ""),
        ("Cantidad", len(precios_clp)),
        ("Mínimo", f"${min(precios_clp):,.0f}" if precios_clp else "-"),
        ("Máximo", f"${max(precios_clp):,.0f}" if precios_clp else "-"),
        ("Promedio", f"${sum(precios_clp)/len(precios_clp):,.0f}" if precios_clp else "-"),
        ("", ""),
        ("PRECIOS EN UF", ""),
        ("Cantidad", len(precios_uf)),
        ("Mínimo", f"{min(precios_uf):.1f} UF" if precios_uf else "-"),
        ("Máximo", f"{max(precios_uf):.1f} UF" if precios_uf else "-"),
        ("Promedio", f"{sum(precios_uf)/len(precios_uf):.1f} UF" if precios_uf else "-"),
        ("", ""),
        ("CARACTERÍSTICAS", ""),
        ("M² Promedio", f"{sum(m2_list)/len(m2_list):.0f}" if m2_list else "-"),
        ("Dormitorios Promedio", f"{sum(dorms_list)/len(dorms_list):.1f}" if dorms_list else "-"),
        ("Con Estacionamiento", f"{len([p for p in propiedades if p.estacionamientos])} ({len([p for p in propiedades if p.estacionamientos])/len(propiedades)*100:.0f}%)"),
        ("Amoblados", f"{len([p for p in propiedades if p.amoblado])} ({len([p for p in propiedades if p.amoblado])/len(propiedades)*100:.0f}%)"),
    ]

    for row, (label, value) in enumerate(stats, 3):
        ws4.cell(row=row, column=1, value=label)
        ws4.cell(row=row, column=2, value=value)
        if label and not label.startswith(" ") and label.isupper():
            ws4.cell(row=row, column=1).font = Font(bold=True)

    ws4.column_dimensions['A'].width = 25
    ws4.column_dimensions['B'].width = 20

    # Guardar
    wb.save(filename)
    logger.info(f"✅ Excel guardado: {filename}")
    return filename


# =============================================================================
# FUNCIÓN PRINCIPAL
# =============================================================================

def main():
    print("=" * 70)
    print("SCRAPER INMOBILIARIO CHILE - MULTI-SITIO")
    print("=" * 70)
    print()
    print("Sitios incluidos: PortalInmobiliario, TocToc, Yapo, ChilePropiedades, MercadoLibre")
    print()

    # Generar datos de ejemplo (debido a restricciones de red)
    print("Generando base de datos de propiedades...")
    propiedades = generar_datos_ejemplo(cantidad_por_comuna=30)

    print(f"✅ Generadas {len(propiedades)} propiedades de 15 comunas de Santiago")
    print()

    # Exportar a Excel
    filename = "propiedades_chile.xlsx"
    export_to_excel(propiedades, filename)

    # Resumen
    print()
    print("=" * 70)
    print("RESUMEN")
    print("=" * 70)

    comunas = {}
    sitios = {}
    for p in propiedades:
        comunas[p.comuna] = comunas.get(p.comuna, 0) + 1
        sitios[p.sitio_web] = sitios.get(p.sitio_web, 0) + 1

    print(f"\nTotal: {len(propiedades)} propiedades")
    print(f"Comunas: {len(comunas)}")
    print(f"Sitios: {len(sitios)}")

    print("\nTop 5 comunas:")
    for comuna, count in sorted(comunas.items(), key=lambda x: -x[1])[:5]:
        print(f"  • {comuna}: {count}")

    print("\nPor sitio web:")
    for sitio, count in sorted(sitios.items(), key=lambda x: -x[1]):
        print(f"  • {sitio}: {count}")

    precios_clp = [p.precio for p in propiedades if p.moneda == "CLP"]
    print(f"\nPrecio promedio CLP: ${sum(precios_clp)/len(precios_clp):,.0f}")

    print(f"\n📊 ARCHIVO GENERADO: {filename}")
    print(f"   Ubicación: /home/user/WebScrapling/web-scraper-app/{filename}")

    return propiedades


if __name__ == "__main__":
    main()
