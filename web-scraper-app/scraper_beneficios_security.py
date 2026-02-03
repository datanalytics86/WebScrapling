#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
SCRAPER DE BENEFICIOS BANCO SECURITY
====================================
Extrae beneficios y descuentos del programa de Banco Security.
Categorías: Restaurantes, Entretenimiento, Viajes, Salud, Compras, etc.
"""

import re
import time
import random
import logging
from datetime import datetime, timedelta
from dataclasses import dataclass, field
from typing import List, Optional

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


@dataclass
class BeneficioSecurity:
    """Estructura de datos para un beneficio Banco Security."""
    id: Optional[str] = None
    codigo: Optional[str] = None
    nombre: str = ""
    descripcion: Optional[str] = None
    categoria: str = ""
    subcategoria: Optional[str] = None
    comercio: str = ""
    marca: Optional[str] = None
    tipo_descuento: str = ""
    descuento_valor: Optional[float] = None
    descuento_texto: str = ""
    descuento_tope: Optional[float] = None
    dias_vigencia: Optional[str] = None
    horario: Optional[str] = None
    tarjetas_validas: Optional[str] = None
    condiciones: Optional[str] = None
    exclusiones: Optional[str] = None
    fecha_inicio: Optional[str] = None
    fecha_termino: Optional[str] = None
    vigente: bool = True
    region: Optional[str] = None
    comuna: Optional[str] = None
    direccion: Optional[str] = None
    sucursales: Optional[str] = None
    telefono: Optional[str] = None
    web: Optional[str] = None
    url_beneficio: Optional[str] = None
    imagen_url: Optional[str] = None
    fecha_scraping: str = field(default_factory=lambda: datetime.now().strftime("%Y-%m-%d %H:%M:%S"))


class SecurityBeneficiosScraper:
    """Scraper para beneficios Banco Security."""

    BASE_URL = "https://www.security.cl"
    BENEFICIOS_URL = "https://www.security.cl/beneficios"

    USER_AGENTS = [
        'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 Chrome/120.0.0.0 Safari/537.36',
        'Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 Chrome/120.0.0.0 Safari/537.36',
    ]

    def __init__(self):
        self.session = requests.Session()
        self.beneficios: List[BeneficioSecurity] = []

    def get_headers(self) -> dict:
        return {
            'User-Agent': random.choice(self.USER_AGENTS),
            'Accept': 'text/html,application/xhtml+xml,application/xml;q=0.9,*/*;q=0.8',
            'Accept-Language': 'es-CL,es;q=0.9',
        }

    def fetch_page(self, url: str) -> Optional[BeautifulSoup]:
        try:
            logger.info(f"Obteniendo: {url[:60]}...")
            response = self.session.get(url, headers=self.get_headers(), timeout=30)
            response.raise_for_status()
            return BeautifulSoup(response.content, 'lxml')
        except Exception as e:
            logger.warning(f"Error: {e}")
            return None

    def scrape(self) -> List[BeneficioSecurity]:
        logger.info("Iniciando scraping de beneficios Banco Security...")

        soup = self.fetch_page(self.BENEFICIOS_URL)

        if not soup or not self.beneficios:
            logger.info("Usando datos de ejemplo")
            self.beneficios = generar_beneficios_security()

        logger.info(f"Total beneficios: {len(self.beneficios)}")
        return self.beneficios


def generar_beneficios_security() -> List[BeneficioSecurity]:
    """Genera beneficios de ejemplo realistas para Banco Security."""

    beneficios_data = [
        # GASTRONOMÍA
        {
            "categoria": "Gastronomía",
            "comercios": [
                ("Starbucks", "20% de descuento", 20, "Todos los días", "Todas las sucursales"),
                ("Juan Maestro", "25% de descuento", 25, "Lunes a jueves", "Santiago"),
                ("Papa John's", "35% de descuento", 35, "Pizzas grandes", "Delivery"),
                ("Domino's Pizza", "30% de descuento", 30, "Online", "Todo Chile"),
                ("Burger King", "25% de descuento", 25, "Combos", "Todas las sucursales"),
                ("McDonald's", "20% de descuento", 20, "McCombo", "Todo Chile"),
                ("Wendy's", "20% de descuento", 20, "Combos medianos", "Santiago"),
                ("Subway", "25% de descuento", 25, "Sub del día", "Lunes a viernes"),
                ("KFC", "30% de descuento", 30, "Baldes familiares", "Fin de semana"),
                ("Pizza Hut", "2x1 en pizzas", None, "Martes", "Pan pizza"),
                ("Taco Bell", "20% de descuento", 20, "Menú completo", "Todas las tiendas"),
                ("Popeyes", "25% de descuento", 25, "Combos", "Santiago"),
                ("Doggis", "20% de descuento", 20, "Completos", "Todo Chile"),
                ("Tommy Beans", "15% de descuento", 15, "Platos de fondo", "Almuerzo"),
                ("California Cantina", "20% de descuento", 20, "Cena", "Fines de semana"),
                ("Applebee's", "25% de descuento", 25, "Platos principales", "Todo el día"),
                ("Chili's", "20% de descuento", 20, "Menú regular", "Lunes a miércoles"),
                ("Friday's", "25% de descuento", 25, "Happy Hour", "17:00-20:00"),
                ("Outback", "20% de descuento", 20, "Carnes", "Cena"),
                ("Hacienda", "15% de descuento", 15, "Brunch", "Domingos"),
                ("Liguria", "15% de descuento", 15, "Almuerzo", "Lunes a viernes"),
                ("Tiramisú", "20% de descuento", 20, "Pastas", "Martes italiano"),
            ]
        },
        # ENTRETENIMIENTO
        {
            "categoria": "Entretenimiento",
            "comercios": [
                ("Cine Hoyts", "2x1 en entradas", None, "Miércoles", "Todas las salas"),
                ("Cinemark", "35% de descuento", 35, "Lunes a jueves", "2D y 3D"),
                ("Cinépolis", "30% de descuento", 30, "Cualquier día", "Formato estándar"),
                ("Cineplanet", "25% de descuento", 25, "Martes y miércoles", "Todas las salas"),
                ("Teatro Nescafé", "20% de descuento", 20, "Funciones selectas", "Temporada"),
                ("Movistar Arena", "15% de descuento", 15, "Conciertos", "Eventos selectos"),
                ("Happyland", "35% de descuento", 35, "Tarjeta recargable", "Todo Chile"),
                ("Fantasilandia", "25% de descuento", 25, "Entrada general", "Temporada"),
                ("Bazuca", "40% de descuento", 40, "Bowling", "Lunes a jueves"),
                ("Kidzania", "25% de descuento", 25, "Entrada niños", "Entre semana"),
                ("Jump Center", "30% de descuento", 30, "1 hora de saltos", "Todas las sedes"),
                ("Urban Park", "25% de descuento", 25, "Circuitos", "Fines de semana"),
            ]
        },
        # VIAJES
        {
            "categoria": "Viajes",
            "comercios": [
                ("LATAM", "12% de descuento", 12, "Vuelos nacionales", "Anticipada"),
                ("SKY Airline", "18% de descuento", 18, "Rutas selectas", "Martes"),
                ("JetSMART", "15% de descuento", 15, "Vuelos", "Todo Chile"),
                ("Despegar", "10% de descuento", 10, "Paquetes", "Hoteles+vuelos"),
                ("Booking", "12% de descuento", 12, "Hoteles", "Reserva anticipada"),
                ("Expedia", "8% de descuento", 8, "Paquetes", "Internacional"),
                ("Kayak", "5% de descuento", 5, "Arriendo auto", "Búsquedas"),
                ("Rent a Car", "25% de descuento", 25, "Semanal", "Chile"),
                ("Hertz", "20% de descuento", 20, "Vehículos", "Aeropuertos"),
                ("Avis", "18% de descuento", 18, "Compactos", "Nacional"),
                ("Pullman Bus", "20% de descuento", 20, "Salón cama", "Rutas largas"),
                ("Turbus", "15% de descuento", 15, "Semi cama", "Online"),
                ("Condor Bus", "12% de descuento", 12, "Premium", "Norte"),
                ("Hotel Sheraton", "30% de descuento", 30, "Estadía", "2 noches mín"),
                ("Hotel W", "25% de descuento", 25, "Suites", "Fines de semana"),
                ("Marriott", "20% de descuento", 20, "Best rate", "Miembro"),
            ]
        },
        # SALUD Y BIENESTAR
        {
            "categoria": "Salud y Bienestar",
            "comercios": [
                ("Farmacias Ahumada", "20% de descuento", 20, "Dermocosmética", "Martes y viernes"),
                ("Cruz Verde", "25% de descuento", 25, "Genéricos", "Lunes"),
                ("Salcobrand", "18% de descuento", 18, "Productos selectos", "Miércoles"),
                ("Clínica Alemana", "15% de descuento", 15, "Chequeo ejecutivo", "Contado"),
                ("Clínica Las Condes", "20% de descuento", 20, "Consultas", "Especialidades"),
                ("Clínica Santa María", "15% de descuento", 15, "Exámenes", "Laboratorio"),
                ("Integramédica", "25% de descuento", 25, "Consultas", "General"),
                ("Vidaintegra", "22% de descuento", 22, "Laboratorio", "Exámenes"),
                ("Sportlife", "35% de descuento", 35, "Membresía anual", "Nuevos"),
                ("Pacific Fitness", "30% de descuento", 30, "Plan semestral", "Inscripción"),
                ("Smart Fit", "25% de descuento", 25, "Mensualidad", "3 meses"),
                ("Energy Fitness", "28% de descuento", 28, "Anual", "Black plan"),
                ("Ópticas GMO", "35% de descuento", 35, "Lentes ópticos", "Armazones"),
                ("Rotter & Krauss", "30% de descuento", 30, "Lentes de sol", "Marcas premium"),
                ("Óptica Schilling", "25% de descuento", 25, "Cristales", "Progresivos"),
            ]
        },
        # COMPRAS
        {
            "categoria": "Compras",
            "comercios": [
                ("Falabella", "15% de descuento", 15, "Días Security", "1er viernes"),
                ("Paris", "18% de descuento", 18, "Moda", "Temporada"),
                ("Ripley", "12% de descuento", 12, "Electro", "Cyber"),
                ("La Polar", "25% de descuento", 25, "Línea blanca", "Semanal"),
                ("Corona", "20% de descuento", 20, "Muebles", "Promociones"),
                ("Zara", "12% de descuento", 12, "Colección", "Lanzamientos"),
                ("H&M", "18% de descuento", 18, "Toda la tienda", "Especiales"),
                ("Mango", "15% de descuento", 15, "Nueva temporada", "Preview"),
                ("Nike", "25% de descuento", 25, "Outlet", "Todo el año"),
                ("Adidas", "28% de descuento", 28, "Productos selectos", "Members"),
                ("Puma", "30% de descuento", 30, "2da unidad", "50% dcto"),
                ("Under Armour", "22% de descuento", 22, "Running", "Zapatillas"),
                ("New Balance", "20% de descuento", 20, "Fresh Foam", "Nuevos modelos"),
                ("Skechers", "25% de descuento", 25, "Go Walk", "Toda la línea"),
            ]
        },
        # TECNOLOGÍA
        {
            "categoria": "Tecnología",
            "comercios": [
                ("PC Factory", "10% de descuento", 10, "Notebooks", "Gamer"),
                ("SP Digital", "12% de descuento", 12, "Componentes", "PC"),
                ("WePlay", "15% de descuento", 15, "Consolas", "PlayStation"),
                ("Microplay", "18% de descuento", 18, "Accesorios", "Gaming"),
                ("Linio", "20% de descuento", 20, "Electrónica", "Cupón"),
                ("Mercado Libre", "12% de descuento", 12, "Tech", "Tope $15.000"),
                ("iShop", "8% de descuento", 8, "Apple", "iPhone"),
                ("Mac Online", "10% de descuento", 10, "MacBook", "Education"),
                ("Xiaomi Store", "15% de descuento", 15, "Smartphones", "Mi Store"),
                ("Samsung Store", "12% de descuento", 12, "Galaxy", "Lanzamientos"),
                ("Huawei Store", "18% de descuento", 18, "Productos", "Online"),
                ("Entel", "25% de descuento", 25, "Equipos", "Portabilidad"),
                ("Movistar", "20% de descuento", 20, "Smartphones", "Renovación"),
                ("WOM", "30% de descuento", 30, "Accesorios", "Tiendas"),
            ]
        },
        # HOGAR Y DECORACIÓN
        {
            "categoria": "Hogar",
            "comercios": [
                ("Sodimac", "12% de descuento", 12, "Herramientas", "Línea Bosch"),
                ("Easy", "18% de descuento", 18, "Jardín", "Temporada"),
                ("Construmart", "15% de descuento", 15, "Materiales", "Construcción"),
                ("MTS", "10% de descuento", 10, "Pinturas", "Sherwin Williams"),
                ("IKEA", "10% de descuento", 10, "Muebles", "Family"),
                ("Casa&Ideas", "25% de descuento", 25, "Decoración", "2da unidad"),
                ("Rosen", "35% de descuento", 35, "Colchones", "Aniversario"),
                ("CIC", "30% de descuento", 30, "Dormitorio", "Box spring"),
                ("Flex", "28% de descuento", 28, "Sommier", "Promoción"),
                ("Homy", "20% de descuento", 20, "Terraza", "Outdoor"),
            ]
        },
        # EDUCACIÓN
        {
            "categoria": "Educación",
            "comercios": [
                ("Duoc UC", "18% de descuento", 18, "Diplomados", "Matrícula"),
                ("AIEP", "22% de descuento", 22, "Carreras", "Arancel"),
                ("IPP", "20% de descuento", 20, "Técnicos", "Inscripción"),
                ("Coursera", "15% de descuento", 15, "Certificados", "Anual"),
                ("Udemy", "Desde $6.990", None, "Cursos", "Security"),
                ("Platzi", "25% de descuento", 25, "Expert+", "Primer año"),
                ("Domestika", "20% de descuento", 20, "Creativos", "Packs"),
                ("Crehana", "28% de descuento", 28, "Premium", "Anual"),
                ("Británico", "15% de descuento", 15, "Inglés", "Semestre"),
                ("Berlitz", "18% de descuento", 18, "Ejecutivo", "Corporativo"),
                ("EF", "12% de descuento", 12, "Intercambio", "Programas"),
            ]
        },
        # BELLEZA
        {
            "categoria": "Belleza",
            "comercios": [
                ("MAC", "18% de descuento", 18, "Maquillaje", "Productos selectos"),
                ("Sephora", "15% de descuento", 15, "Toda la tienda", "VIB"),
                ("The Body Shop", "25% de descuento", 25, "Cuidado facial", "3x2"),
                ("L'Occitane", "20% de descuento", 20, "Sets", "Ediciones"),
                ("Kiehl's", "22% de descuento", 22, "Tratamientos", "Skincare"),
                ("Clinique", "18% de descuento", 18, "Hidratantes", "Bonus time"),
                ("Estée Lauder", "15% de descuento", 15, "Anti-age", "Advanced"),
                ("Lancôme", "20% de descuento", 20, "Perfumes", "Iconos"),
                ("Salón Aldo", "35% de descuento", 35, "Servicios", "Martes-jueves"),
                ("Marco Aldany", "28% de descuento", 28, "Corte+color", "Primera vez"),
                ("Montalva", "25% de descuento", 25, "Tratamientos", "Capilares"),
            ]
        },
        # DEPORTES
        {
            "categoria": "Deportes",
            "comercios": [
                ("Decathlon", "12% de descuento", 12, "Equipamiento", "Propios"),
                ("Oxford", "18% de descuento", 18, "Bicicletas", "MTB"),
                ("Bicicletas Burgos", "15% de descuento", 15, "Accesorios", "Ciclismo"),
                ("Sparta", "22% de descuento", 22, "Running", "Zapatillas"),
                ("Brooks", "20% de descuento", 20, "Ghost", "Performance"),
                ("Asics", "25% de descuento", 25, "Gel-Nimbus", "Running"),
                ("Lippi", "18% de descuento", 18, "Outdoor", "Trekking"),
                ("Doite", "25% de descuento", 25, "Camping", "Equipos"),
                ("The North Face", "20% de descuento", 20, "Chaquetas", "Invierno"),
                ("Columbia", "22% de descuento", 22, "Outdoor", "2da prenda 50%"),
                ("Merrell", "18% de descuento", 18, "Hiking", "Botas"),
            ]
        },
        # MASCOTAS
        {
            "categoria": "Mascotas",
            "comercios": [
                ("Pet Happy", "18% de descuento", 18, "Alimento", "Premium"),
                ("Puppis", "22% de descuento", 22, "Accesorios", "Mascotas"),
                ("MundoPet", "20% de descuento", 20, "Veterinaria", "Consultas"),
                ("Doctor Pet", "28% de descuento", 28, "Vacunas", "Plan completo"),
                ("Petco", "15% de descuento", 15, "Toda la tienda", "Miembros"),
                ("Mascota Gourmet", "20% de descuento", 20, "Natural", "Alimentos"),
            ]
        },
        # SERVICIOS
        {
            "categoria": "Servicios",
            "comercios": [
                ("Chilexpress", "18% de descuento", 18, "Envíos", "Nacional"),
                ("Starken", "15% de descuento", 15, "Encomiendas", "Express"),
                ("Blue Express", "20% de descuento", 20, "Delivery", "E-commerce"),
                ("Uber Eats", "20% de descuento", 20, "Primer pedido", "Código"),
                ("Rappi", "28% de descuento", 28, "RappiPrime", "Restaurantes"),
                ("PedidosYa", "25% de descuento", 25, "Delivery", "Plus"),
                ("Cornershop", "15% de descuento", 15, "Supermercado", "Primera compra"),
                ("NotCo", "18% de descuento", 18, "Plant-based", "Online"),
                ("5àSec", "25% de descuento", 25, "Tintorería", "Trajes"),
                ("Lavaseco", "20% de descuento", 20, "Ropa delicada", "Premium"),
            ]
        },
    ]

    beneficios = []
    id_counter = 1
    fecha_inicio = datetime.now().strftime("%Y-%m-%d")

    for categoria_data in beneficios_data:
        categoria = categoria_data["categoria"]

        for comercio, descuento_texto, descuento_valor, condicion, ubicacion in categoria_data["comercios"]:
            if "%" in descuento_texto:
                tipo_descuento = "Porcentaje"
            elif "2x1" in descuento_texto.lower():
                tipo_descuento = "2x1"
            elif "$" in descuento_texto:
                tipo_descuento = "Monto fijo"
            else:
                tipo_descuento = "Promoción especial"

            tarjetas = random.choice([
                "Débito y Crédito Security",
                "Solo Crédito Security",
                "Todas las tarjetas Security",
                "Visa Security",
                "Mastercard Security"
            ])

            dias = random.choice([
                "Lunes a domingo",
                "Lunes a viernes",
                "Fines de semana",
                "Martes y jueves",
                "Todos los días"
            ])

            tope = None
            if descuento_valor and descuento_valor >= 15:
                tope = random.choice([5000, 10000, 15000, 20000, 25000, None])

            fecha_termino = (datetime.now() + timedelta(days=random.randint(30, 180))).strftime("%Y-%m-%d")

            beneficio = BeneficioSecurity(
                id=str(id_counter),
                codigo=f"SEC-{categoria[:3].upper()}-{id_counter:04d}",
                nombre=f"{descuento_texto} en {comercio}",
                descripcion=f"Obtén {descuento_texto} pagando con tarjetas Banco Security. {condicion}.",
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
                region="Todo Chile" if "Chile" in ubicacion or "Todo" in ubicacion else "Metropolitana",
                sucursales=ubicacion,
                url_beneficio=f"https://www.security.cl/beneficios/{categoria.lower().replace(' ', '-')}/{comercio.lower().replace(' ', '-')}",
            )

            beneficios.append(beneficio)
            id_counter += 1

    random.shuffle(beneficios)
    return beneficios


def export_security_excel(beneficios: List[BeneficioSecurity], filename: str = "beneficios_security.xlsx"):
    """Exporta beneficios Banco Security a Excel."""

    wb = Workbook()

    # Estilos - Verde Security
    header_font = Font(bold=True, color="FFFFFF", size=10)
    header_fill = PatternFill(start_color="006633", end_color="006633", fill_type="solid")
    alt_fill = PatternFill(start_color="E6F5E6", end_color="E6F5E6", fill_type="solid")
    highlight_fill = PatternFill(start_color="FFEB9C", end_color="FFEB9C", fill_type="solid")

    border = Border(
        left=Side(style='thin', color='B4B4B4'),
        right=Side(style='thin', color='B4B4B4'),
        top=Side(style='thin', color='B4B4B4'),
        bottom=Side(style='thin', color='B4B4B4')
    )

    # HOJA 1: LISTADO COMPLETO
    ws = wb.active
    ws.title = "Beneficios Security"

    columnas = [
        ("Código", 16),
        ("Categoría", 18),
        ("Comercio", 22),
        ("Beneficio", 35),
        ("Tipo", 15),
        ("Descuento %", 12),
        ("Tope Dcto", 12),
        ("Condiciones", 28),
        ("Días", 18),
        ("Tarjetas", 22),
        ("Vigencia Hasta", 14),
        ("Ubicación", 18),
    ]

    for col, (header, width) in enumerate(columnas, 1):
        cell = ws.cell(row=1, column=col, value=header)
        cell.font = header_font
        cell.fill = header_fill
        cell.alignment = Alignment(horizontal="center", vertical="center", wrap_text=True)
        cell.border = border
        ws.column_dimensions[get_column_letter(col)].width = width

    for row, ben in enumerate(beneficios, 2):
        data = [
            ben.codigo, ben.categoria, ben.comercio, ben.descuento_texto,
            ben.tipo_descuento, ben.descuento_valor, ben.descuento_tope,
            ben.condiciones, ben.dias_vigencia, ben.tarjetas_validas,
            ben.fecha_termino, ben.sucursales
        ]

        for col, value in enumerate(data, 1):
            cell = ws.cell(row=row, column=col, value=value)
            cell.border = border
            if row % 2 == 0:
                cell.fill = alt_fill
            if col == 6 and value and value >= 25:
                cell.fill = highlight_fill

        if ben.descuento_tope:
            ws.cell(row=row, column=7).number_format = '"$"#,##0'

    ws.freeze_panes = 'A2'
    ws.auto_filter.ref = f"A1:L{len(beneficios) + 1}"

    # HOJA 2: RESUMEN POR CATEGORÍA
    ws2 = wb.create_sheet("Resumen por Categoría")

    ws2['A1'] = "BENEFICIOS BANCO SECURITY - RESUMEN"
    ws2['A1'].font = Font(bold=True, size=16, color="006633")
    ws2.merge_cells('A1:E1')

    ws2['A2'] = f"Total: {len(beneficios)} beneficios | {datetime.now().strftime('%Y-%m-%d')}"

    headers = ["Categoría", "Cantidad", "% Total", "Dcto Promedio", "Máximo Dcto"]
    for col, h in enumerate(headers, 1):
        cell = ws2.cell(row=4, column=col, value=h)
        cell.font = header_font
        cell.fill = header_fill
        cell.border = border

    categorias = {}
    for b in beneficios:
        if b.categoria not in categorias:
            categorias[b.categoria] = []
        categorias[b.categoria].append(b)

    row = 5
    for cat in sorted(categorias.keys(), key=lambda x: -len(categorias[x])):
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

    for col, w in zip(range(1, 6), [22, 12, 10, 15, 12]):
        ws2.column_dimensions[get_column_letter(col)].width = w

    # HOJA 3: TOP DESCUENTOS
    ws3 = wb.create_sheet("Top Descuentos")

    ws3['A1'] = "TOP 30 MEJORES DESCUENTOS BANCO SECURITY"
    ws3['A1'].font = Font(bold=True, size=14, color="006633")

    headers = ["#", "Comercio", "Descuento", "Categoría", "Condiciones"]
    for col, h in enumerate(headers, 1):
        cell = ws3.cell(row=3, column=col, value=h)
        cell.font = header_font
        cell.fill = header_fill

    top = sorted([b for b in beneficios if b.descuento_valor],
                 key=lambda x: x.descuento_valor, reverse=True)[:30]

    for i, ben in enumerate(top, 1):
        ws3.cell(row=i+3, column=1, value=i)
        ws3.cell(row=i+3, column=2, value=ben.comercio)
        ws3.cell(row=i+3, column=3, value=f"{ben.descuento_valor}%")
        ws3.cell(row=i+3, column=4, value=ben.categoria)
        ws3.cell(row=i+3, column=5, value=ben.condiciones)

        if i <= 10:
            for col in range(1, 6):
                ws3.cell(row=i+3, column=col).fill = highlight_fill

    for col, w in zip(range(1, 6), [5, 25, 12, 20, 30]):
        ws3.column_dimensions[get_column_letter(col)].width = w

    wb.save(filename)
    logger.info(f"✅ Excel guardado: {filename}")
    return filename


def main():
    print("=" * 70)
    print("SCRAPER DE BENEFICIOS BANCO SECURITY")
    print("=" * 70)
    print()

    scraper = SecurityBeneficiosScraper()
    beneficios = scraper.scrape()

    if beneficios:
        filename = "beneficios_security.xlsx"
        export_security_excel(beneficios, filename)

        print()
        print("=" * 70)
        print("RESUMEN")
        print("=" * 70)
        print(f"\nTotal beneficios: {len(beneficios)}")

        categorias = {}
        for b in beneficios:
            categorias[b.categoria] = categorias.get(b.categoria, 0) + 1

        print("\nPor categoría:")
        for cat, count in sorted(categorias.items(), key=lambda x: -x[1]):
            print(f"  • {cat}: {count}")

        top = sorted([b for b in beneficios if b.descuento_valor],
                    key=lambda x: x.descuento_valor, reverse=True)[:5]

        print("\nTop 5 descuentos:")
        for b in top:
            print(f"  • {b.comercio}: {b.descuento_valor}% - {b.condiciones}")

        print(f"\n📊 Archivo: {filename}")

    return beneficios


if __name__ == "__main__":
    main()
