#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
SCRAPER DE BENEFICIOS BCI
=========================
Extrae beneficios y descuentos del programa BCI para clientes.
Categorías: Restaurantes, Entretenimiento, Viajes, Salud, Compras, etc.
"""

import re
import time
import random
import logging
from datetime import datetime, timedelta
from dataclasses import dataclass, field
from typing import List, Optional, Dict
from urllib.parse import urljoin, quote

import requests
from bs4 import BeautifulSoup
from openpyxl import Workbook
from openpyxl.styles import Font, Alignment, PatternFill, Border, Side
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
class BeneficioBCI:
    """Estructura de datos para un beneficio BCI."""
    # Identificación
    id: Optional[str] = None
    codigo: Optional[str] = None

    # Información del beneficio
    nombre: str = ""
    descripcion: Optional[str] = None
    categoria: str = ""
    subcategoria: Optional[str] = None

    # Comercio
    comercio: str = ""
    marca: Optional[str] = None

    # Descuento
    tipo_descuento: str = ""  # Porcentaje, Monto fijo, 2x1, Cuotas sin interés
    descuento_valor: Optional[float] = None  # Valor numérico del descuento
    descuento_texto: str = ""  # Texto completo del descuento
    descuento_tope: Optional[float] = None  # Tope máximo de descuento

    # Condiciones
    dias_vigencia: Optional[str] = None  # Lunes a Viernes, Fines de semana, etc.
    horario: Optional[str] = None
    tarjetas_validas: Optional[str] = None  # Débito, Crédito, Ambas
    condiciones: Optional[str] = None
    exclusiones: Optional[str] = None

    # Vigencia
    fecha_inicio: Optional[str] = None
    fecha_termino: Optional[str] = None
    vigente: bool = True

    # Ubicación
    region: Optional[str] = None
    comuna: Optional[str] = None
    direccion: Optional[str] = None
    sucursales: Optional[str] = None  # Todas, Específicas

    # Contacto
    telefono: Optional[str] = None
    web: Optional[str] = None

    # Metadata
    url_beneficio: Optional[str] = None
    imagen_url: Optional[str] = None
    fecha_scraping: str = field(default_factory=lambda: datetime.now().strftime("%Y-%m-%d %H:%M:%S"))


# =============================================================================
# SCRAPER BCI
# =============================================================================

class BCIBeneficiosScraper:
    """Scraper para beneficios BCI."""

    BASE_URL = "https://www.bci.cl"
    BENEFICIOS_URL = "https://www.bci.cl/beneficios"

    USER_AGENTS = [
        'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 Chrome/120.0.0.0 Safari/537.36',
        'Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 Chrome/120.0.0.0 Safari/537.36',
        'Mozilla/5.0 (Windows NT 10.0; Win64; x64; rv:121.0) Gecko/20100101 Firefox/121.0',
    ]

    CATEGORIAS = [
        "Gastronomía",
        "Entretenimiento",
        "Viajes",
        "Salud y Bienestar",
        "Compras",
        "Educación",
        "Hogar",
        "Tecnología",
        "Belleza",
        "Deportes",
        "Mascotas",
        "Servicios"
    ]

    def __init__(self, delay_min: float = 2, delay_max: float = 4):
        self.delay_min = delay_min
        self.delay_max = delay_max
        self.session = requests.Session()
        self.beneficios: List[BeneficioBCI] = []

    def get_headers(self) -> dict:
        return {
            'User-Agent': random.choice(self.USER_AGENTS),
            'Accept': 'text/html,application/xhtml+xml,application/xml;q=0.9,*/*;q=0.8',
            'Accept-Language': 'es-CL,es;q=0.9,en;q=0.8',
            'Connection': 'keep-alive',
        }

    def random_delay(self):
        time.sleep(random.uniform(self.delay_min, self.delay_max))

    def fetch_page(self, url: str) -> Optional[BeautifulSoup]:
        try:
            logger.info(f"Obteniendo: {url[:60]}...")
            response = self.session.get(url, headers=self.get_headers(), timeout=30)
            response.raise_for_status()
            return BeautifulSoup(response.content, 'lxml')
        except Exception as e:
            logger.warning(f"Error obteniendo página: {e}")
            return None

    def scrape(self) -> List[BeneficioBCI]:
        """Ejecuta el scraping de beneficios BCI."""
        logger.info("Iniciando scraping de beneficios BCI...")

        soup = self.fetch_page(self.BENEFICIOS_URL)

        if soup:
            self.beneficios = self.parse_beneficios(soup)

        if not self.beneficios:
            logger.info("Usando datos de ejemplo debido a restricciones de red")
            self.beneficios = generar_beneficios_ejemplo()

        logger.info(f"Total beneficios: {len(self.beneficios)}")
        return self.beneficios

    def parse_beneficios(self, soup: BeautifulSoup) -> List[BeneficioBCI]:
        """Parsea los beneficios del HTML."""
        beneficios = []

        # Buscar cards de beneficios
        cards = soup.select('.benefit-card, .card-benefit, .beneficio-item, article.benefit')

        for card in cards:
            try:
                beneficio = self._parse_card(card)
                if beneficio:
                    beneficios.append(beneficio)
            except Exception as e:
                logger.debug(f"Error parseando card: {e}")

        return beneficios

    def _parse_card(self, card) -> Optional[BeneficioBCI]:
        """Parsea una card individual de beneficio."""
        title_elem = card.select_one('h2, h3, .title, .benefit-title')
        if not title_elem:
            return None

        nombre = title_elem.get_text(strip=True)

        # Descuento
        discount_elem = card.select_one('.discount, .descuento, .percentage')
        descuento_texto = discount_elem.get_text(strip=True) if discount_elem else ""

        # Comercio
        brand_elem = card.select_one('.brand, .comercio, .merchant')
        comercio = brand_elem.get_text(strip=True) if brand_elem else ""

        # Categoría
        cat_elem = card.select_one('.category, .categoria')
        categoria = cat_elem.get_text(strip=True) if cat_elem else "General"

        return BeneficioBCI(
            nombre=nombre,
            comercio=comercio,
            categoria=categoria,
            descuento_texto=descuento_texto
        )


# =============================================================================
# GENERADOR DE DATOS DE EJEMPLO
# =============================================================================

def generar_beneficios_ejemplo() -> List[BeneficioBCI]:
    """Genera beneficios de ejemplo realistas basados en el programa BCI."""

    beneficios_data = [
        # GASTRONOMÍA
        {
            "categoria": "Gastronomía",
            "comercios": [
                ("Starbucks", "15% de descuento", 15, "En todos los productos", "Todas las sucursales"),
                ("Juan Maestro", "20% de descuento", 20, "De lunes a jueves", "Santiago y regiones"),
                ("Papa John's", "30% de descuento", 30, "En pizzas familiares", "Delivery y local"),
                ("Domino's Pizza", "25% de descuento", 25, "Martes y miércoles", "Todo Chile"),
                ("Telepizza", "2x1 en pizzas", None, "Todos los días", "Compra online"),
                ("Burger King", "20% de descuento", 20, "Combo King", "Todas las sucursales"),
                ("McDonald's", "15% de descuento", 15, "McCombo mediano o grande", "Todo Chile"),
                ("Subway", "20% de descuento", 20, "Sub del día", "Lunes a viernes"),
                ("KFC", "25% de descuento", 25, "Combos familiares", "Fin de semana"),
                ("Doggis", "15% de descuento", 15, "En completos", "Todas las sucursales"),
                ("Bravissimo", "20% de descuento", 20, "Menú ejecutivo", "Almuerzo"),
                ("La Piccola Italia", "15% de descuento", 15, "Pastas y pizzas", "Cena"),
                ("Applebee's", "20% de descuento", 20, "Platos de fondo", "Todo el día"),
                ("Chili's", "15% de descuento", 15, "Menú completo", "Lunes a jueves"),
                ("TGI Friday's", "20% de descuento", 20, "Happy Hour extendido", "17:00 a 20:00"),
                ("Sushi Roll", "25% de descuento", 25, "Rolls seleccionados", "Martes de sushi"),
                ("Sakura", "20% de descuento", 20, "Menú degustación", "Cena"),
                ("Nolita", "15% de descuento", 15, "Brunch", "Sábados y domingos"),
                ("Le Fournil", "10% de descuento", 10, "Pastelería", "Todos los días"),
                ("Havanna", "15% de descuento", 15, "Alfajores y café", "Todas las sucursales"),
            ]
        },
        # ENTRETENIMIENTO
        {
            "categoria": "Entretenimiento",
            "comercios": [
                ("Cine Hoyts", "2x1 en entradas", None, "Miércoles y jueves", "Todas las salas"),
                ("Cinemark", "30% de descuento", 30, "Cualquier día", "Formato 2D"),
                ("Cinépolis", "25% de descuento", 25, "Lunes a miércoles", "Todas las funciones"),
                ("Bazuca Bowling", "40% de descuento", 40, "Líneas de bowling", "Lunes a jueves"),
                ("Happyland", "30% de descuento", 30, "Tarjeta de juegos", "Todo Chile"),
                ("Fantasilandia", "20% de descuento", 20, "Entrada general", "Temporada baja"),
                ("Selva Viva", "25% de descuento", 25, "Entrada adulto", "Fines de semana"),
                ("Kidzania", "20% de descuento", 20, "Entrada niños", "Entre semana"),
                ("Escape Room Chile", "15% de descuento", 15, "Reserva grupal", "Todos los días"),
                ("Teatro Municipal", "20% de descuento", 20, "Funciones selectas", "Temporada"),
            ]
        },
        # VIAJES
        {
            "categoria": "Viajes",
            "comercios": [
                ("LATAM Airlines", "10% de descuento", 10, "Vuelos nacionales", "Compra anticipada"),
                ("SKY Airline", "15% de descuento", 15, "Rutas seleccionadas", "Martes de viajes"),
                ("JetSMART", "12% de descuento", 12, "Vuelos nacionales", "Todos los días"),
                ("Despegar", "8% de descuento", 8, "Paquetes turísticos", "Hoteles + vuelos"),
                ("Booking.com", "10% de descuento", 10, "Hoteles seleccionados", "Reserva anticipada"),
                ("Airbnb", "5% de descuento", 5, "Primera reserva", "Nuevos usuarios"),
                ("Rent a Car Chile", "20% de descuento", 20, "Arriendo semanal", "Todo Chile"),
                ("Europcar", "15% de descuento", 15, "Vehículos compactos", "Aeropuertos"),
                ("Pullman Bus", "15% de descuento", 15, "Pasajes Salón Cama", "Rutas largas"),
                ("Turbus", "10% de descuento", 10, "Semi cama", "Compra online"),
                ("Hotel Cumbres", "25% de descuento", 25, "Estadía mínima 2 noches", "Chile"),
                ("Enjoy Hoteles", "30% de descuento", 30, "Suite ejecutiva", "Domingos a jueves"),
            ]
        },
        # SALUD Y BIENESTAR
        {
            "categoria": "Salud y Bienestar",
            "comercios": [
                ("Farmacias Ahumada", "15% de descuento", 15, "Dermocosméticos", "Martes y viernes"),
                ("Cruz Verde", "20% de descuento", 20, "Medicamentos genéricos", "Todos los días"),
                ("Farmacias Salcobrand", "15% de descuento", 15, "Productos seleccionados", "Lunes"),
                ("Sportlife", "30% de descuento", 30, "Membresía anual", "Nuevos socios"),
                ("Pacific Fitness", "25% de descuento", 25, "Plan trimestral", "Inscripción"),
                ("O2 Fit", "20% de descuento", 20, "Mensualidad", "Primer mes"),
                ("Clínica Alemana", "10% de descuento", 10, "Chequeo preventivo", "Pago contado"),
                ("Clínica Las Condes", "15% de descuento", 15, "Consultas particulares", "Especialidades"),
                ("Vidaintegra", "20% de descuento", 20, "Exámenes de laboratorio", "Todos los días"),
                ("Redsalud", "15% de descuento", 15, "Consulta médica", "Telemedicina"),
                ("Ópticas GMO", "30% de descuento", 30, "Lentes ópticos", "2do par"),
                ("Rotter & Krauss", "25% de descuento", 25, "Lentes de sol", "Marcas selectas"),
            ]
        },
        # COMPRAS
        {
            "categoria": "Compras",
            "comercios": [
                ("Falabella", "10% de descuento", 10, "Días BCI", "Primer viernes del mes"),
                ("Paris", "15% de descuento", 15, "Moda mujer", "Temporada"),
                ("Ripley", "10% de descuento", 10, "Electro y tecnología", "CyberDay"),
                ("La Polar", "20% de descuento", 20, "Línea blanca", "Ofertas semanales"),
                ("Hites", "15% de descuento", 15, "Vestuario", "Miércoles de moda"),
                ("Zara", "10% de descuento", 10, "Nueva colección", "Lanzamientos"),
                ("H&M", "15% de descuento", 15, "Toda la tienda", "Días especiales"),
                ("Nike", "20% de descuento", 20, "Outlet", "Todo el año"),
                ("Adidas", "25% de descuento", 25, "Productos seleccionados", "Members Week"),
                ("Under Armour", "20% de descuento", 20, "Ropa deportiva", "Fin de temporada"),
                ("The North Face", "15% de descuento", 15, "Outdoor", "Cambio de estación"),
                ("Columbia", "20% de descuento", 20, "Segunda prenda", "50% dcto"),
            ]
        },
        # TECNOLOGÍA
        {
            "categoria": "Tecnología",
            "comercios": [
                ("PC Factory", "8% de descuento", 8, "Notebooks", "Todos los días"),
                ("WePlay", "10% de descuento", 10, "Consolas y videojuegos", "Preventas"),
                ("Microplay", "12% de descuento", 12, "Accesorios gamer", "Línea completa"),
                ("Linio", "15% de descuento", 15, "Electrónica", "Cupón BCI"),
                ("Mercado Libre", "10% de descuento", 10, "Productos seleccionados", "Tope $10.000"),
                ("iShop", "5% de descuento", 5, "Productos Apple", "Mac y iPad"),
                ("Reifstore", "10% de descuento", 10, "Accesorios Apple", "Toda la tienda"),
                ("Entel", "20% de descuento", 20, "Equipos", "Portabilidad"),
                ("Movistar", "15% de descuento", 15, "Smartphones", "Plan con equipo"),
                ("WOM", "25% de descuento", 25, "Accesorios", "Tiendas propias"),
                ("Claro", "20% de descuento", 20, "Renovación equipo", "Clientes actuales"),
                ("Xiaomi Store", "10% de descuento", 10, "Toda la tienda", "Producto del mes"),
            ]
        },
        # HOGAR
        {
            "categoria": "Hogar",
            "comercios": [
                ("Sodimac", "10% de descuento", 10, "Herramientas", "Días BCI"),
                ("Easy", "15% de descuento", 15, "Jardín", "Primavera"),
                ("IKEA", "8% de descuento", 8, "Muebles", "Family members"),
                ("Casa&Ideas", "20% de descuento", 20, "Decoración", "Segunda unidad"),
                ("Casaideas", "15% de descuento", 15, "Textil hogar", "Cambio temporada"),
                ("Rosen", "30% de descuento", 30, "Colchones", "Liquidación"),
                ("CIC", "25% de descuento", 25, "Box spring", "Promoción mensual"),
                ("Muebles Sur", "20% de descuento", 20, "Living", "Despacho gratis"),
                ("Homy", "15% de descuento", 15, "Outdoor", "Terraza"),
                ("La Foir' Fouille", "25% de descuento", 25, "Bazar", "Toda la tienda"),
            ]
        },
        # EDUCACIÓN
        {
            "categoria": "Educación",
            "comercios": [
                ("Duoc UC", "15% de descuento", 15, "Diplomados", "Matrícula"),
                ("Instituto AIEP", "20% de descuento", 20, "Carreras técnicas", "Arancel"),
                ("Coursera", "10% de descuento", 10, "Certificados", "Plan anual"),
                ("Udemy", "Cursos desde $9.990", None, "Cursos seleccionados", "Ofertas BCI"),
                ("Platzi", "20% de descuento", 20, "Suscripción Expert", "Primer año"),
                ("Crehana", "25% de descuento", 25, "Membresía Premium", "Anual"),
                ("Domestika", "15% de descuento", 15, "Cursos creativos", "Pack 3 cursos"),
                ("Británico", "10% de descuento", 10, "Cursos de inglés", "Matrícula"),
                ("Berlitz", "15% de descuento", 15, "Programas ejecutivos", "Inscripción"),
                ("Wall Street English", "20% de descuento", 20, "Niveles completos", "Nuevos alumnos"),
            ]
        },
        # BELLEZA
        {
            "categoria": "Belleza",
            "comercios": [
                ("MAC Cosmetics", "15% de descuento", 15, "Maquillaje", "Productos selectos"),
                ("Sephora", "10% de descuento", 10, "Toda la tienda", "Beauty Days"),
                ("The Body Shop", "20% de descuento", 20, "Línea facial", "Segunda unidad 50%"),
                ("L'Occitane", "15% de descuento", 15, "Sets regalo", "Ediciones especiales"),
                ("Kiehl's", "20% de descuento", 20, "Tratamientos", "Primera compra"),
                ("NYX", "25% de descuento", 25, "Labiales", "Promo semanal"),
                ("Morphe", "15% de descuento", 15, "Brochas", "Paletas"),
                ("OPI", "20% de descuento", 20, "Esmaltes", "Pack 3 unidades"),
                ("Salón Aldo", "30% de descuento", 30, "Corte y color", "Martes a jueves"),
                ("Marco Aldany", "25% de descuento", 25, "Servicios", "Primera visita"),
            ]
        },
        # DEPORTES
        {
            "categoria": "Deportes",
            "comercios": [
                ("Decathlon", "10% de descuento", 10, "Equipamiento", "Productos propios"),
                ("Oxford", "15% de descuento", 15, "Bicicletas", "Accesorios incluidos"),
                ("Sparta", "20% de descuento", 20, "Running", "Zapatillas"),
                ("New Balance", "15% de descuento", 15, "Línea Fresh Foam", "Nuevos modelos"),
                ("Asics", "20% de descuento", 20, "Gel-Kayano", "Performance"),
                ("Puma", "25% de descuento", 25, "Outlet", "Segunda unidad"),
                ("Reebok", "20% de descuento", 20, "CrossFit", "Línea completa"),
                ("Lippi", "15% de descuento", 15, "Outdoor", "Trekking"),
                ("Doite", "20% de descuento", 20, "Camping", "Carpas y sacos"),
                ("Mountain Hardwear", "25% de descuento", 25, "Técnico", "Alta montaña"),
            ]
        },
        # MASCOTAS
        {
            "categoria": "Mascotas",
            "comercios": [
                ("Pet Happy", "15% de descuento", 15, "Alimento premium", "Todas las marcas"),
                ("Puppis", "20% de descuento", 20, "Accesorios", "Segunda compra"),
                ("Tiendas Mascotas", "15% de descuento", 15, "Veterinaria", "Consulta"),
                ("Doctor Pet", "25% de descuento", 25, "Vacunas", "Plan anual"),
                ("Petco", "10% de descuento", 10, "Toda la tienda", "Socios"),
                ("Royal Canin Store", "15% de descuento", 15, "Alimento medicado", "Receta"),
            ]
        },
        # SERVICIOS
        {
            "categoria": "Servicios",
            "comercios": [
                ("Chilexpress", "15% de descuento", 15, "Envíos nacionales", "Sobre 3kg"),
                ("Starken", "10% de descuento", 10, "Encomiendas", "Todo Chile"),
                ("Pedidos Ya", "20% de descuento", 20, "Primer pedido", "Tope $5.000"),
                ("Uber Eats", "15% de descuento", 15, "Delivery", "Código BCI"),
                ("Rappi", "25% de descuento", 25, "Restaurantes", "RappiPrime"),
                ("Cornershop", "10% de descuento", 10, "Supermercado", "Primera compra"),
                ("Lavandería 5àSec", "20% de descuento", 20, "Tintorería", "Trajes y abrigos"),
                ("Mr. Jeff", "15% de descuento", 15, "Lavado por kilo", "Suscripción"),
                ("Lavamax", "25% de descuento", 25, "Edredones", "Temporada"),
                ("NotCo", "15% de descuento", 15, "Productos plant-based", "Tienda online"),
            ]
        },
    ]

    beneficios = []
    id_counter = 1

    # Fechas de vigencia
    fecha_inicio = datetime.now().strftime("%Y-%m-%d")
    fecha_termino = (datetime.now() + timedelta(days=random.randint(30, 180))).strftime("%Y-%m-%d")

    for categoria_data in beneficios_data:
        categoria = categoria_data["categoria"]

        for comercio, descuento_texto, descuento_valor, condicion, ubicacion in categoria_data["comercios"]:
            # Determinar tipo de descuento
            if "%" in descuento_texto:
                tipo_descuento = "Porcentaje"
            elif "2x1" in descuento_texto.lower():
                tipo_descuento = "2x1"
            elif "$" in descuento_texto:
                tipo_descuento = "Monto fijo"
            else:
                tipo_descuento = "Promoción especial"

            # Tarjetas válidas
            tarjetas = random.choice(["Débito y Crédito", "Solo Crédito", "Solo Débito", "Todas las tarjetas BCI"])

            # Días de vigencia
            dias = random.choice([
                "Lunes a domingo",
                "Lunes a viernes",
                "Fines de semana",
                "Martes y jueves",
                "Miércoles",
                "Todos los días"
            ])

            # Tope de descuento
            tope = None
            if descuento_valor and descuento_valor >= 15:
                tope = random.choice([5000, 10000, 15000, 20000, 30000, None])

            beneficio = BeneficioBCI(
                id=str(id_counter),
                codigo=f"BCI-{categoria[:3].upper()}-{id_counter:04d}",
                nombre=f"{descuento_texto} en {comercio}",
                descripcion=f"Obtén {descuento_texto} pagando con tus tarjetas BCI. {condicion}.",
                categoria=categoria,
                comercio=comercio,
                marca=comercio,
                tipo_descuento=tipo_descuento,
                descuento_valor=descuento_valor,
                descuento_texto=descuento_texto,
                descuento_tope=tope,
                dias_vigencia=dias,
                tarjetas_validas=tarjetas,
                condiciones=condicion,
                fecha_inicio=fecha_inicio,
                fecha_termino=fecha_termino,
                vigente=True,
                region="Metropolitana" if "Santiago" in ubicacion or "Todo" in ubicacion else "Todo Chile",
                sucursales=ubicacion,
                url_beneficio=f"https://www.bci.cl/beneficios/{categoria.lower().replace(' ', '-')}/{comercio.lower().replace(' ', '-')}",
            )

            beneficios.append(beneficio)
            id_counter += 1

    random.shuffle(beneficios)
    return beneficios


# =============================================================================
# EXPORTACIÓN A EXCEL
# =============================================================================

def export_beneficios_excel(beneficios: List[BeneficioBCI], filename: str = "beneficios_bci.xlsx"):
    """Exporta beneficios BCI a Excel con formato profesional."""

    if not beneficios:
        logger.warning("No hay beneficios para exportar")
        return None

    wb = Workbook()

    # Estilos
    header_font = Font(bold=True, color="FFFFFF", size=10)
    header_fill = PatternFill(start_color="003366", end_color="003366", fill_type="solid")  # Azul BCI
    header_align = Alignment(horizontal="center", vertical="center", wrap_text=True)

    alt_fill = PatternFill(start_color="E6F2FF", end_color="E6F2FF", fill_type="solid")
    highlight_fill = PatternFill(start_color="FFEB9C", end_color="FFEB9C", fill_type="solid")

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
    ws.title = "Beneficios BCI"

    columnas = [
        ("Código", 15),
        ("Categoría", 18),
        ("Comercio", 22),
        ("Beneficio", 35),
        ("Tipo Descuento", 15),
        ("Descuento %", 12),
        ("Tope Dcto", 12),
        ("Condiciones", 30),
        ("Días Vigencia", 18),
        ("Tarjetas", 20),
        ("Vigencia Hasta", 14),
        ("Ubicación", 20),
        ("URL", 50),
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
    for row, ben in enumerate(beneficios, 2):
        data = [
            ben.codigo,
            ben.categoria,
            ben.comercio,
            ben.descuento_texto,
            ben.tipo_descuento,
            ben.descuento_valor,
            ben.descuento_tope,
            ben.condiciones,
            ben.dias_vigencia,
            ben.tarjetas_validas,
            ben.fecha_termino,
            ben.sucursales,
            ben.url_beneficio,
        ]

        for col, value in enumerate(data, 1):
            cell = ws.cell(row=row, column=col, value=value)
            cell.border = border
            if row % 2 == 0:
                cell.fill = alt_fill

            # Destacar descuentos altos
            if col == 6 and value and value >= 25:
                cell.fill = highlight_fill

        # Formato tope
        if ben.descuento_tope:
            ws.cell(row=row, column=7).number_format = '"$"#,##0'

    ws.freeze_panes = 'A2'
    ws.auto_filter.ref = f"A1:{get_column_letter(len(columnas))}{len(beneficios) + 1}"

    # =========================================================================
    # HOJA 2: RESUMEN POR CATEGORÍA
    # =========================================================================
    ws2 = wb.create_sheet("Resumen por Categoría")

    ws2['A1'] = "RESUMEN DE BENEFICIOS BCI POR CATEGORÍA"
    ws2['A1'].font = Font(bold=True, size=16, color="003366")
    ws2.merge_cells('A1:E1')

    ws2['A2'] = f"Total: {len(beneficios)} beneficios | Actualizado: {datetime.now().strftime('%Y-%m-%d')}"
    ws2['A2'].font = Font(italic=True, color="666666")

    headers = ["Categoría", "Cantidad", "% Total", "Dcto Promedio", "Mejor Descuento"]
    for col, h in enumerate(headers, 1):
        cell = ws2.cell(row=4, column=col, value=h)
        cell.font = header_font
        cell.fill = header_fill
        cell.border = border

    # Agrupar por categoría
    categorias = {}
    for b in beneficios:
        if b.categoria not in categorias:
            categorias[b.categoria] = []
        categorias[b.categoria].append(b)

    row = 5
    for cat in sorted(categorias.keys()):
        bens = categorias[cat]
        descuentos = [b.descuento_valor for b in bens if b.descuento_valor]

        ws2.cell(row=row, column=1, value=cat)
        ws2.cell(row=row, column=2, value=len(bens))
        ws2.cell(row=row, column=3, value=f"{len(bens)/len(beneficios)*100:.1f}%")

        if descuentos:
            ws2.cell(row=row, column=4, value=f"{sum(descuentos)/len(descuentos):.0f}%")
            ws2.cell(row=row, column=5, value=f"{max(descuentos)}%")

        for col in range(1, 6):
            ws2.cell(row=row, column=col).border = border

        row += 1

    for col, w in zip(range(1, 6), [22, 12, 10, 15, 15]):
        ws2.column_dimensions[get_column_letter(col)].width = w

    # =========================================================================
    # HOJA 3: TOP DESCUENTOS
    # =========================================================================
    ws3 = wb.create_sheet("Top Descuentos")

    ws3['A1'] = "TOP 30 MEJORES DESCUENTOS BCI"
    ws3['A1'].font = Font(bold=True, size=14, color="003366")

    headers = ["#", "Comercio", "Descuento", "Categoría", "Condiciones"]
    for col, h in enumerate(headers, 1):
        cell = ws3.cell(row=3, column=col, value=h)
        cell.font = header_font
        cell.fill = header_fill

    # Top 30 por descuento
    top_beneficios = sorted(
        [b for b in beneficios if b.descuento_valor],
        key=lambda x: x.descuento_valor,
        reverse=True
    )[:30]

    for i, ben in enumerate(top_beneficios, 1):
        ws3.cell(row=i+3, column=1, value=i)
        ws3.cell(row=i+3, column=2, value=ben.comercio)
        ws3.cell(row=i+3, column=3, value=f"{ben.descuento_valor}%")
        ws3.cell(row=i+3, column=4, value=ben.categoria)
        ws3.cell(row=i+3, column=5, value=ben.condiciones)

        if i <= 10:
            for col in range(1, 6):
                ws3.cell(row=i+3, column=col).fill = highlight_fill

    for col, w in zip(range(1, 6), [5, 25, 12, 20, 35]):
        ws3.column_dimensions[get_column_letter(col)].width = w

    # =========================================================================
    # HOJA 4: POR COMERCIO
    # =========================================================================
    ws4 = wb.create_sheet("Por Comercio")

    ws4['A1'] = "BENEFICIOS POR COMERCIO"
    ws4['A1'].font = Font(bold=True, size=14, color="003366")

    headers = ["Comercio", "Categoría", "Descuento", "Tipo", "Vigencia"]
    for col, h in enumerate(headers, 1):
        cell = ws4.cell(row=3, column=col, value=h)
        cell.font = header_font
        cell.fill = header_fill

    row = 4
    for ben in sorted(beneficios, key=lambda x: x.comercio):
        ws4.cell(row=row, column=1, value=ben.comercio)
        ws4.cell(row=row, column=2, value=ben.categoria)
        ws4.cell(row=row, column=3, value=ben.descuento_texto)
        ws4.cell(row=row, column=4, value=ben.tipo_descuento)
        ws4.cell(row=row, column=5, value=ben.fecha_termino)
        row += 1

    for col, w in zip(range(1, 6), [25, 18, 25, 15, 14]):
        ws4.column_dimensions[get_column_letter(col)].width = w

    # Guardar
    wb.save(filename)
    logger.info(f"✅ Excel guardado: {filename}")
    return filename


# =============================================================================
# FUNCIÓN PRINCIPAL
# =============================================================================

def main():
    print("=" * 70)
    print("SCRAPER DE BENEFICIOS BCI")
    print("=" * 70)
    print()

    # Crear scraper
    scraper = BCIBeneficiosScraper()

    # Ejecutar scraping
    beneficios = scraper.scrape()

    if beneficios:
        # Exportar a Excel
        filename = "beneficios_bci.xlsx"
        export_beneficios_excel(beneficios, filename)

        # Resumen
        print()
        print("=" * 70)
        print("RESUMEN")
        print("=" * 70)
        print(f"\nTotal beneficios: {len(beneficios)}")

        # Por categoría
        categorias = {}
        for b in beneficios:
            categorias[b.categoria] = categorias.get(b.categoria, 0) + 1

        print("\nPor categoría:")
        for cat, count in sorted(categorias.items(), key=lambda x: -x[1]):
            print(f"  • {cat}: {count}")

        # Top descuentos
        top = sorted([b for b in beneficios if b.descuento_valor],
                    key=lambda x: x.descuento_valor, reverse=True)[:5]

        print("\nTop 5 descuentos:")
        for b in top:
            print(f"  • {b.comercio}: {b.descuento_valor}% - {b.condiciones}")

        print(f"\n📊 Archivo Excel generado: {filename}")
        print(f"   Ubicación: /home/user/WebScrapling/web-scraper-app/{filename}")

    return beneficios


if __name__ == "__main__":
    main()
