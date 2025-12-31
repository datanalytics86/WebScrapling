#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Scraper de ChilePropiedades.cl - Arriendos en Santiago
=======================================================
Extrae listados de arriendos en toda la Región Metropolitana.
"""

import re
import time
import random
import logging
from datetime import datetime
from dataclasses import dataclass, asdict
from typing import List, Optional
from urllib.parse import urljoin, quote

import requests
from bs4 import BeautifulSoup
from openpyxl import Workbook
from openpyxl.styles import Font, Alignment, PatternFill, Border, Side

# Configurar logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)


@dataclass
class Propiedad:
    """Estructura de datos para una propiedad."""
    titulo: str
    precio: Optional[float]
    moneda: str
    comuna: str
    direccion: Optional[str]
    metros_cuadrados: Optional[int]
    metros_utiles: Optional[int]
    dormitorios: Optional[int]
    banos: Optional[int]
    estacionamientos: Optional[int]
    tipo_propiedad: Optional[str]
    url: str
    imagen_url: Optional[str]
    codigo: Optional[str]
    fecha_publicacion: Optional[str]
    fecha_scraping: str


class ChilePropiedadesScraper:
    """
    Scraper para ChilePropiedades.cl
    Extrae arriendos de toda la Región Metropolitana (Santiago).
    """

    BASE_URL = "https://www.chilepropiedades.cl"

    # Comunas de Santiago para scraping
    COMUNAS_SANTIAGO = [
        "las-condes",
        "providencia",
        "vitacura",
        "nunoa",
        "santiago",
        "la-reina",
        "penalolen",
        "macul",
        "san-miguel",
        "la-florida",
        "maipu",
        "puente-alto",
        "lo-barnechea",
        "huechuraba",
        "recoleta",
        "independencia",
        "quilicura",
        "cerrillos",
        "estacion-central",
        "san-joaquin",
        "la-cisterna",
        "el-bosque",
        "la-granja",
        "san-bernardo"
    ]

    USER_AGENTS = [
        'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36',
        'Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36',
        'Mozilla/5.0 (Windows NT 10.0; Win64; x64; rv:121.0) Gecko/20100101 Firefox/121.0',
        'Mozilla/5.0 (X11; Linux x86_64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36',
    ]

    def __init__(self, delay_min: float = 2, delay_max: float = 5, max_retries: int = 3):
        self.delay_min = delay_min
        self.delay_max = delay_max
        self.max_retries = max_retries
        self.session = requests.Session()
        self.propiedades: List[Propiedad] = []

    def get_headers(self) -> dict:
        """Headers con User-Agent aleatorio."""
        return {
            'User-Agent': random.choice(self.USER_AGENTS),
            'Accept': 'text/html,application/xhtml+xml,application/xml;q=0.9,image/webp,*/*;q=0.8',
            'Accept-Language': 'es-CL,es;q=0.9,en;q=0.8',
            'Accept-Encoding': 'gzip, deflate, br',
            'Connection': 'keep-alive',
            'Upgrade-Insecure-Requests': '1',
            'Cache-Control': 'max-age=0',
        }

    def random_delay(self):
        """Delay aleatorio entre requests."""
        delay = random.uniform(self.delay_min, self.delay_max)
        logger.debug(f"Esperando {delay:.2f} segundos...")
        time.sleep(delay)

    def fetch_page(self, url: str) -> Optional[BeautifulSoup]:
        """Obtiene página con retry logic."""
        for attempt in range(1, self.max_retries + 1):
            try:
                logger.info(f"Obteniendo (intento {attempt}): {url}")
                response = self.session.get(
                    url,
                    headers=self.get_headers(),
                    timeout=30,
                    allow_redirects=True
                )
                response.raise_for_status()
                return BeautifulSoup(response.content, 'lxml')

            except requests.exceptions.RequestException as e:
                logger.warning(f"Error en intento {attempt}: {e}")
                if attempt < self.max_retries:
                    time.sleep(2 ** attempt)

        logger.error(f"Falló después de {self.max_retries} intentos: {url}")
        return None

    def build_search_url(self, comuna: str, tipo: str = "departamento", page: int = 1) -> str:
        """
        Construye URL de búsqueda para ChilePropiedades.cl

        Formato típico:
        https://www.chilepropiedades.cl/propiedades/arriendo/departamento/region-metropolitana/las-condes
        """
        base = f"{self.BASE_URL}/propiedades/arriendo/{tipo}/region-metropolitana/{comuna}"

        if page > 1:
            return f"{base}?pagina={page}"
        return base

    def clean_price(self, price_text: str) -> tuple:
        """Extrae precio y moneda."""
        if not price_text:
            return None, "CLP"

        price_text = price_text.strip().upper()

        # Detectar moneda
        if 'UF' in price_text:
            moneda = "UF"
        elif 'US' in price_text or 'USD' in price_text:
            moneda = "USD"
        else:
            moneda = "CLP"

        # Extraer números
        # Limpiar y extraer
        numbers = re.findall(r'[\d.,]+', price_text)
        if numbers:
            price_str = numbers[0]
            # Formato chileno: 1.234.567 o 1.234,56
            if ',' in price_str:
                price_str = price_str.replace('.', '').replace(',', '.')
            else:
                price_str = price_str.replace('.', '')

            try:
                precio = float(price_str)
                # Si es UF y el precio parece muy alto, probablemente es CLP
                if moneda == "UF" and precio > 10000:
                    moneda = "CLP"
                return precio, moneda
            except ValueError:
                pass

        return None, moneda

    def extract_number(self, text: str) -> Optional[int]:
        """Extrae primer número entero."""
        if not text:
            return None
        numbers = re.findall(r'\d+', str(text))
        return int(numbers[0]) if numbers else None

    def parse_property(self, card, comuna: str) -> Optional[Propiedad]:
        """Parsea una tarjeta de propiedad."""
        try:
            # Título y URL
            title_elem = (
                card.select_one('h2 a') or
                card.select_one('h3 a') or
                card.select_one('.property-title a') or
                card.select_one('.titulo a') or
                card.select_one('a.title') or
                card.select_one('.card-title a')
            )

            if not title_elem:
                # Buscar cualquier enlace con título
                title_elem = card.select_one('a[title]')

            if not title_elem:
                return None

            titulo = title_elem.get_text(strip=True) or title_elem.get('title', '')
            url = title_elem.get('href', '')

            if not titulo:
                return None

            if url and not url.startswith('http'):
                url = urljoin(self.BASE_URL, url)

            # Precio
            price_elem = (
                card.select_one('.price') or
                card.select_one('.precio') or
                card.select_one('.property-price') or
                card.select_one('[class*="price"]') or
                card.select_one('[class*="precio"]')
            )

            precio, moneda = None, "CLP"
            if price_elem:
                precio, moneda = self.clean_price(price_elem.get_text())

            # Ubicación/Dirección
            location_elem = (
                card.select_one('.location') or
                card.select_one('.ubicacion') or
                card.select_one('.address') or
                card.select_one('.direccion') or
                card.select_one('[class*="location"]')
            )
            direccion = location_elem.get_text(strip=True) if location_elem else None

            # Formatear nombre de comuna
            comuna_display = comuna.replace('-', ' ').title()

            # Atributos (m2, dormitorios, baños, etc.)
            metros = None
            metros_utiles = None
            dormitorios = None
            banos = None
            estacionamientos = None

            # Buscar en diferentes formatos
            attrs = card.select('li, .feature, .attribute, [class*="feature"], [class*="attr"]')

            for attr in attrs:
                text = attr.get_text(strip=True).lower()

                if 'm²' in text or 'm2' in text or 'metros' in text:
                    num = self.extract_number(text)
                    if num:
                        if 'útil' in text or 'util' in text:
                            metros_utiles = num
                        else:
                            metros = num
                elif 'dormitorio' in text or 'dorm' in text or 'hab' in text:
                    dormitorios = self.extract_number(text)
                elif 'baño' in text or 'bano' in text:
                    banos = self.extract_number(text)
                elif 'estacionamiento' in text or 'parking' in text:
                    estacionamientos = self.extract_number(text)

            # También buscar en spans/divs con iconos
            icon_attrs = card.select('[class*="icon"], [class*="ico"]')
            for elem in icon_attrs:
                parent = elem.parent
                if parent:
                    text = parent.get_text(strip=True).lower()
                    num = self.extract_number(text)
                    if num:
                        if 'm' in text:
                            metros = metros or num
                        elif 'dorm' in text or 'hab' in text:
                            dormitorios = dormitorios or num
                        elif 'bañ' in text:
                            banos = banos or num

            # Tipo de propiedad (desde el título o clase)
            tipo_propiedad = None
            titulo_lower = titulo.lower()
            if 'departamento' in titulo_lower or 'depto' in titulo_lower:
                tipo_propiedad = "Departamento"
            elif 'casa' in titulo_lower:
                tipo_propiedad = "Casa"
            elif 'oficina' in titulo_lower:
                tipo_propiedad = "Oficina"
            elif 'local' in titulo_lower:
                tipo_propiedad = "Local Comercial"
            elif 'estudio' in titulo_lower or 'studio' in titulo_lower:
                tipo_propiedad = "Estudio"
            elif 'bodega' in titulo_lower:
                tipo_propiedad = "Bodega"

            # Imagen
            img_elem = card.select_one('img')
            imagen_url = None
            if img_elem:
                imagen_url = (
                    img_elem.get('data-src') or
                    img_elem.get('data-lazy') or
                    img_elem.get('src')
                )
                if imagen_url and not imagen_url.startswith('http'):
                    imagen_url = urljoin(self.BASE_URL, imagen_url)

            # Código de propiedad
            codigo = None
            code_elem = card.select_one('.code, .codigo, [class*="code"], [class*="ref"]')
            if code_elem:
                codigo = code_elem.get_text(strip=True)

            # También buscar en atributos data
            if not codigo:
                codigo = card.get('data-id') or card.get('data-code')

            return Propiedad(
                titulo=titulo,
                precio=precio,
                moneda=moneda,
                comuna=comuna_display,
                direccion=direccion,
                metros_cuadrados=metros,
                metros_utiles=metros_utiles,
                dormitorios=dormitorios,
                banos=banos,
                estacionamientos=estacionamientos,
                tipo_propiedad=tipo_propiedad,
                url=url,
                imagen_url=imagen_url,
                codigo=codigo,
                fecha_publicacion=None,
                fecha_scraping=datetime.now().strftime("%Y-%m-%d %H:%M:%S")
            )

        except Exception as e:
            logger.warning(f"Error parseando propiedad: {e}")
            return None

    def scrape_comuna(self, comuna: str, tipo: str = "departamento", max_pages: int = 2) -> List[Propiedad]:
        """Scrapea una comuna específica."""
        propiedades_comuna = []

        for page in range(1, max_pages + 1):
            url = self.build_search_url(comuna, tipo, page)
            soup = self.fetch_page(url)

            if not soup:
                break

            # Buscar contenedores de propiedades
            cards = (
                soup.select('.property-card') or
                soup.select('.listing-item') or
                soup.select('.property-item') or
                soup.select('[class*="property"]') or
                soup.select('.card') or
                soup.select('article')
            )

            if not cards:
                logger.info(f"No se encontraron propiedades en {comuna} página {page}")
                break

            logger.info(f"Encontradas {len(cards)} tarjetas en {comuna} página {page}")

            for card in cards:
                prop = self.parse_property(card, comuna)
                if prop and prop.precio:
                    propiedades_comuna.append(prop)

            if len(cards) < 10:  # Probablemente última página
                break

            if page < max_pages:
                self.random_delay()

        return propiedades_comuna

    def scrape_santiago(self,
                        comunas: List[str] = None,
                        tipo: str = "departamento",
                        max_pages_per_comuna: int = 2) -> List[Propiedad]:
        """
        Scrapea arriendos en Santiago completo o comunas específicas.

        Args:
            comunas: Lista de comunas a scrapear (None = todas)
            tipo: Tipo de propiedad (departamento, casa, oficina)
            max_pages_per_comuna: Páginas por comuna
        """
        self.propiedades = []
        comunas_to_scrape = comunas or self.COMUNAS_SANTIAGO

        logger.info(f"Iniciando scraping de {len(comunas_to_scrape)} comunas de Santiago")
        logger.info(f"Tipo: {tipo}, Páginas por comuna: {max_pages_per_comuna}")

        for i, comuna in enumerate(comunas_to_scrape, 1):
            logger.info(f"[{i}/{len(comunas_to_scrape)}] Scrapeando {comuna}...")

            props = self.scrape_comuna(comuna, tipo, max_pages_per_comuna)
            self.propiedades.extend(props)

            logger.info(f"  -> {len(props)} propiedades encontradas en {comuna}")

            if i < len(comunas_to_scrape):
                self.random_delay()

        logger.info(f"Scraping completado: {len(self.propiedades)} propiedades en total")
        return self.propiedades


def export_to_excel(propiedades: List[Propiedad], filename: str = "arriendos_santiago.xlsx"):
    """Exporta propiedades a Excel con formato profesional."""

    if not propiedades:
        logger.warning("No hay propiedades para exportar")
        return None

    wb = Workbook()
    ws = wb.active
    ws.title = "Arriendos Santiago"

    # Estilos
    header_font = Font(bold=True, color="FFFFFF", size=11)
    header_fill = PatternFill(start_color="1B4F72", end_color="1B4F72", fill_type="solid")
    header_alignment = Alignment(horizontal="center", vertical="center", wrap_text=True)
    alt_fill = PatternFill(start_color="EBF5FB", end_color="EBF5FB", fill_type="solid")

    border = Border(
        left=Side(style='thin', color='CCCCCC'),
        right=Side(style='thin', color='CCCCCC'),
        top=Side(style='thin', color='CCCCCC'),
        bottom=Side(style='thin', color='CCCCCC')
    )

    # Headers
    headers = [
        "ID", "Título", "Precio", "Moneda", "Comuna", "Dirección",
        "M² Total", "M² Útiles", "Dorm.", "Baños", "Estac.",
        "Tipo", "Código", "URL"
    ]

    for col, header in enumerate(headers, 1):
        cell = ws.cell(row=1, column=col, value=header)
        cell.font = header_font
        cell.fill = header_fill
        cell.alignment = header_alignment
        cell.border = border

    # Datos
    for row, prop in enumerate(propiedades, 2):
        data = [
            row - 1,
            prop.titulo[:80] if prop.titulo else "",
            prop.precio,
            prop.moneda,
            prop.comuna,
            prop.direccion,
            prop.metros_cuadrados,
            prop.metros_utiles,
            prop.dormitorios,
            prop.banos,
            prop.estacionamientos,
            prop.tipo_propiedad,
            prop.codigo,
            prop.url
        ]

        for col, value in enumerate(data, 1):
            cell = ws.cell(row=row, column=col, value=value)
            cell.border = border
            if row % 2 == 0:
                cell.fill = alt_fill

    # Formato de precios
    for row in range(2, len(propiedades) + 2):
        precio_cell = ws.cell(row=row, column=3)
        moneda = ws.cell(row=row, column=4).value
        if precio_cell.value:
            if moneda == "CLP":
                precio_cell.number_format = '"$"#,##0'
            elif moneda == "UF":
                precio_cell.number_format = '#,##0.0" UF"'

    # Anchos de columna
    widths = [5, 50, 15, 8, 18, 35, 10, 10, 7, 7, 7, 15, 12, 60]
    for i, width in enumerate(widths, 1):
        ws.column_dimensions[chr(64 + i) if i <= 26 else 'A'].width = width

    ws.freeze_panes = 'A2'

    # =====================
    # HOJA RESUMEN
    # =====================
    ws_summary = wb.create_sheet("Resumen")

    ws_summary.merge_cells('A1:D1')
    ws_summary['A1'] = "RESUMEN ARRIENDOS SANTIAGO"
    ws_summary['A1'].font = Font(bold=True, size=16, color="1B4F72")

    ws_summary['A3'] = "Total Propiedades:"
    ws_summary['B3'] = len(propiedades)
    ws_summary['B3'].font = Font(bold=True, size=14)

    # Por comuna
    comunas = {}
    for p in propiedades:
        comunas[p.comuna] = comunas.get(p.comuna, 0) + 1

    ws_summary['A5'] = "POR COMUNA"
    ws_summary['A5'].font = Font(bold=True, size=12)
    ws_summary['A6'] = "Comuna"
    ws_summary['B6'] = "Cantidad"
    ws_summary['C6'] = "% del Total"
    for cell in ['A6', 'B6', 'C6']:
        ws_summary[cell].font = Font(bold=True)

    row = 7
    for comuna, count in sorted(comunas.items(), key=lambda x: -x[1]):
        ws_summary[f'A{row}'] = comuna
        ws_summary[f'B{row}'] = count
        ws_summary[f'C{row}'] = f"{count/len(propiedades)*100:.1f}%"
        row += 1

    # Por tipo
    row += 1
    tipos = {}
    for p in propiedades:
        t = p.tipo_propiedad or "Sin especificar"
        tipos[t] = tipos.get(t, 0) + 1

    ws_summary[f'A{row}'] = "POR TIPO DE PROPIEDAD"
    ws_summary[f'A{row}'].font = Font(bold=True, size=12)
    row += 1

    for tipo, count in sorted(tipos.items(), key=lambda x: -x[1]):
        ws_summary[f'A{row}'] = tipo
        ws_summary[f'B{row}'] = count
        row += 1

    # Precios
    row += 1
    ws_summary[f'A{row}'] = "ANÁLISIS DE PRECIOS"
    ws_summary[f'A{row}'].font = Font(bold=True, size=12)
    row += 1

    precios_clp = [p.precio for p in propiedades if p.moneda == "CLP" and p.precio]
    precios_uf = [p.precio for p in propiedades if p.moneda == "UF" and p.precio]

    if precios_clp:
        ws_summary[f'A{row}'] = "Precios en CLP:"
        row += 1
        ws_summary[f'A{row}'] = f"  Mínimo: ${min(precios_clp):,.0f}"
        row += 1
        ws_summary[f'A{row}'] = f"  Máximo: ${max(precios_clp):,.0f}"
        row += 1
        ws_summary[f'A{row}'] = f"  Promedio: ${sum(precios_clp)/len(precios_clp):,.0f}"
        row += 2

    if precios_uf:
        ws_summary[f'A{row}'] = "Precios en UF:"
        row += 1
        ws_summary[f'A{row}'] = f"  Mínimo: {min(precios_uf):.1f} UF"
        row += 1
        ws_summary[f'A{row}'] = f"  Máximo: {max(precios_uf):.1f} UF"
        row += 1
        ws_summary[f'A{row}'] = f"  Promedio: {sum(precios_uf)/len(precios_uf):.1f} UF"

    ws_summary.column_dimensions['A'].width = 30
    ws_summary.column_dimensions['B'].width = 15
    ws_summary.column_dimensions['C'].width = 12

    # =====================
    # HOJA POR COMUNA
    # =====================
    ws_comunas = wb.create_sheet("Detalle por Comuna")

    ws_comunas['A1'] = "DETALLE DE PRECIOS POR COMUNA"
    ws_comunas['A1'].font = Font(bold=True, size=14)

    headers = ["Comuna", "Cantidad", "Precio Mín", "Precio Máx", "Precio Prom", "Moneda"]
    for col, h in enumerate(headers, 1):
        ws_comunas.cell(row=3, column=col, value=h).font = Font(bold=True)

    row = 4
    for comuna in sorted(comunas.keys()):
        props_comuna = [p for p in propiedades if p.comuna == comuna]
        precios = [p.precio for p in props_comuna if p.precio]

        if precios:
            # Determinar moneda predominante
            monedas = [p.moneda for p in props_comuna if p.precio]
            moneda_ppal = max(set(monedas), key=monedas.count)
            precios_moneda = [p.precio for p in props_comuna if p.precio and p.moneda == moneda_ppal]

            if precios_moneda:
                ws_comunas.cell(row=row, column=1, value=comuna)
                ws_comunas.cell(row=row, column=2, value=len(props_comuna))
                ws_comunas.cell(row=row, column=3, value=min(precios_moneda))
                ws_comunas.cell(row=row, column=4, value=max(precios_moneda))
                ws_comunas.cell(row=row, column=5, value=round(sum(precios_moneda)/len(precios_moneda)))
                ws_comunas.cell(row=row, column=6, value=moneda_ppal)

                # Formato
                if moneda_ppal == "CLP":
                    for c in [3, 4, 5]:
                        ws_comunas.cell(row=row, column=c).number_format = '"$"#,##0'

                row += 1

    for i, w in enumerate([20, 12, 15, 15, 15, 10], 1):
        ws_comunas.column_dimensions[chr(64 + i)].width = w

    # Guardar
    wb.save(filename)
    logger.info(f"Excel guardado: {filename}")
    return filename


def main():
    """Función principal."""
    print("=" * 70)
    print("SCRAPER DE ARRIENDOS - SANTIAGO COMPLETO")
    print("Fuente: ChilePropiedades.cl")
    print("=" * 70)
    print()

    # Crear scraper
    scraper = ChilePropiedadesScraper(
        delay_min=2,
        delay_max=4,
        max_retries=3
    )

    # Comunas principales de Santiago para scrapear
    comunas_principales = [
        "las-condes",
        "providencia",
        "vitacura",
        "nunoa",
        "santiago",
        "la-reina",
        "la-florida",
        "maipu",
        "penalolen",
        "lo-barnechea"
    ]

    # Ejecutar scraping
    print(f"Scrapeando {len(comunas_principales)} comunas de Santiago...")
    print(f"Comunas: {', '.join([c.replace('-', ' ').title() for c in comunas_principales])}")
    print()

    propiedades = scraper.scrape_santiago(
        comunas=comunas_principales,
        tipo="departamento",
        max_pages_per_comuna=2
    )

    if propiedades:
        # Exportar a Excel
        filename = "arriendos_santiago.xlsx"
        export_to_excel(propiedades, filename)

        # Resumen en consola
        print()
        print("=" * 70)
        print("RESUMEN")
        print("=" * 70)
        print(f"\nTotal propiedades encontradas: {len(propiedades)}")

        # Por comuna
        comunas = {}
        for p in propiedades:
            comunas[p.comuna] = comunas.get(p.comuna, 0) + 1

        print("\nPor comuna:")
        for comuna, count in sorted(comunas.items(), key=lambda x: -x[1]):
            print(f"  • {comuna}: {count}")

        # Precios
        precios_clp = [p.precio for p in propiedades if p.moneda == "CLP" and p.precio]
        precios_uf = [p.precio for p in propiedades if p.moneda == "UF" and p.precio]

        if precios_clp:
            print(f"\nPrecios en CLP ({len(precios_clp)}):")
            print(f"  • Mínimo: ${min(precios_clp):,.0f}")
            print(f"  • Máximo: ${max(precios_clp):,.0f}")
            print(f"  • Promedio: ${sum(precios_clp)/len(precios_clp):,.0f}")

        if precios_uf:
            print(f"\nPrecios en UF ({len(precios_uf)}):")
            print(f"  • Mínimo: {min(precios_uf):.1f} UF")
            print(f"  • Máximo: {max(precios_uf):.1f} UF")
            print(f"  • Promedio: {sum(precios_uf)/len(precios_uf):.1f} UF")

        print(f"\n📊 Archivo Excel generado: {filename}")

    else:
        print("\nNo se encontraron propiedades.")
        print("Esto puede deberse a restricciones de red o cambios en el sitio web.")

    return propiedades


if __name__ == "__main__":
    propiedades = main()
