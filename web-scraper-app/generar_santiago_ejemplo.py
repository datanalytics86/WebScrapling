#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Generador de datos de ejemplo - Arriendos Santiago Completo
Simula datos realistas del mercado inmobiliario de Santiago.
"""

import random
from datetime import datetime, timedelta
from dataclasses import dataclass
from typing import List, Optional

from openpyxl import Workbook
from openpyxl.styles import Font, Alignment, PatternFill, Border, Side
from openpyxl.chart import BarChart, Reference


@dataclass
class Propiedad:
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


# Configuración de comunas de Santiago con precios promedio por m2
COMUNAS_CONFIG = {
    "Las Condes": {"precio_m2": (18000, 28000), "uf_ratio": 0.35, "cantidad": 45},
    "Providencia": {"precio_m2": (17000, 26000), "uf_ratio": 0.30, "cantidad": 40},
    "Vitacura": {"precio_m2": (22000, 35000), "uf_ratio": 0.45, "cantidad": 30},
    "Ñuñoa": {"precio_m2": (14000, 20000), "uf_ratio": 0.20, "cantidad": 35},
    "Santiago Centro": {"precio_m2": (12000, 18000), "uf_ratio": 0.15, "cantidad": 50},
    "La Reina": {"precio_m2": (15000, 22000), "uf_ratio": 0.25, "cantidad": 25},
    "Peñalolén": {"precio_m2": (10000, 15000), "uf_ratio": 0.10, "cantidad": 20},
    "La Florida": {"precio_m2": (9000, 14000), "uf_ratio": 0.10, "cantidad": 30},
    "Maipú": {"precio_m2": (7000, 11000), "uf_ratio": 0.05, "cantidad": 25},
    "Puente Alto": {"precio_m2": (6000, 10000), "uf_ratio": 0.05, "cantidad": 20},
    "Lo Barnechea": {"precio_m2": (20000, 32000), "uf_ratio": 0.40, "cantidad": 20},
    "Huechuraba": {"precio_m2": (9000, 14000), "uf_ratio": 0.10, "cantidad": 15},
    "Macul": {"precio_m2": (10000, 15000), "uf_ratio": 0.10, "cantidad": 18},
    "San Miguel": {"precio_m2": (11000, 16000), "uf_ratio": 0.12, "cantidad": 22},
    "Recoleta": {"precio_m2": (8000, 12000), "uf_ratio": 0.08, "cantidad": 15},
}

# Calles por comuna
CALLES = {
    "Las Condes": ["Av. Apoquindo", "Av. Las Condes", "Av. Kennedy", "El Golf", "Isidora Goyenechea", "Av. Colón", "Rosario Norte", "Av. Manquehue"],
    "Providencia": ["Av. Providencia", "Av. 11 de Septiembre", "Los Leones", "Pedro de Valdivia", "Manuel Montt", "Av. Suecia", "Av. Ricardo Lyon"],
    "Vitacura": ["Av. Vitacura", "Av. Kennedy", "Av. Bicentenario", "Nueva Costanera", "Alonso de Córdova", "Av. Américo Vespucio"],
    "Ñuñoa": ["Av. Irarrázaval", "Av. Grecia", "José Domingo Cañas", "Av. Ossa", "Av. Marathon", "Rodrigo de Araya"],
    "Santiago Centro": ["Alameda", "Av. Libertador Bernardo O'Higgins", "Morandé", "Teatinos", "San Pablo", "Rosas", "Catedral"],
    "La Reina": ["Av. Larraín", "Av. Príncipe de Gales", "Av. Tobalaba", "Av. Ossa"],
    "Peñalolén": ["Av. Grecia", "Av. Tobalaba", "Av. José Arrieta", "Av. Consistorial"],
    "La Florida": ["Av. Vicuña Mackenna", "Av. La Florida", "Av. Walker Martínez", "Av. Trinidad"],
    "Maipú": ["Av. Pajaritos", "Av. 5 de Abril", "Av. Américo Vespucio", "Av. Los Pajaritos"],
    "Puente Alto": ["Av. Concha y Toro", "Av. Camilo Henríquez", "Av. Tocornal"],
    "Lo Barnechea": ["Av. La Dehesa", "Av. Las Condes", "Camino El Alba", "Av. Pie Andino"],
    "Huechuraba": ["Av. Recoleta", "Av. Pedro Fontova", "Ciudad Empresarial"],
    "Macul": ["Av. Macul", "Av. Quilín", "Av. Departamental"],
    "San Miguel": ["Av. Lo Ovalle", "Gran Avenida", "Av. Santa Rosa"],
    "Recoleta": ["Av. Recoleta", "Av. El Salto", "Av. Perú"],
}


def generar_propiedades() -> List[Propiedad]:
    """Genera propiedades de ejemplo para todo Santiago."""
    propiedades = []
    fecha_scraping = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    id_counter = 1

    for comuna, config in COMUNAS_CONFIG.items():
        calles = CALLES.get(comuna, ["Calle Principal"])

        for _ in range(config["cantidad"]):
            # Tipo de propiedad
            tipo = random.choices(
                ["Departamento", "Estudio", "Casa", "Oficina"],
                weights=[70, 15, 10, 5]
            )[0]

            # Metros cuadrados según tipo
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
            else:  # Oficina
                m2 = random.randint(30, 200)
                dorms = None
                banos = random.randint(1, 3)

            # Precio
            precio_m2 = random.randint(*config["precio_m2"])

            if random.random() < config["uf_ratio"]:
                # Precio en UF (valor UF aprox 37,000 CLP)
                precio_clp = m2 * precio_m2
                precio = round(precio_clp / 37000, 1)
                moneda = "UF"
            else:
                precio = round((m2 * precio_m2) / 10000) * 10000
                moneda = "CLP"

            # Dirección
            calle = random.choice(calles)
            numero = random.randint(100, 9999)
            direccion = f"{calle} {numero}"

            # Título
            if tipo == "Departamento":
                titulo = f"Departamento {dorms}D {banos}B {m2}m² en {comuna}"
                extras = []
                if random.random() < 0.3:
                    extras.append("amoblado")
                if random.random() < 0.4:
                    extras.append("con estacionamiento")
                if random.random() < 0.2:
                    extras.append("vista")
                if extras:
                    titulo += " " + ", ".join(extras)
            elif tipo == "Estudio":
                titulo = f"Estudio {m2}m² en {comuna}"
                if random.random() < 0.5:
                    titulo += " amoblado"
            elif tipo == "Casa":
                titulo = f"Casa {dorms}D {banos}B {m2}m² en {comuna}"
                if random.random() < 0.2:
                    titulo += " con piscina"
                if random.random() < 0.3:
                    titulo += " con jardín"
            else:
                titulo = f"Oficina {m2}m² en {comuna}"
                if random.random() < 0.3:
                    titulo += " implementada"

            # Estacionamientos
            estac = None
            if tipo != "Estudio":
                if random.random() < 0.6:
                    estac = random.randint(1, 2)

            # Fecha publicación (últimos 30 días)
            dias_atras = random.randint(0, 30)
            fecha_pub = (datetime.now() - timedelta(days=dias_atras)).strftime("%Y-%m-%d")

            propiedad = Propiedad(
                titulo=titulo,
                precio=precio,
                moneda=moneda,
                comuna=comuna,
                direccion=direccion,
                metros_cuadrados=m2,
                metros_utiles=int(m2 * 0.85) if random.random() < 0.3 else None,
                dormitorios=dorms,
                banos=banos,
                estacionamientos=estac,
                tipo_propiedad=tipo,
                url=f"https://www.chilepropiedades.cl/propiedad/{1000000 + id_counter}",
                imagen_url=f"https://images.chilepropiedades.cl/{random.randint(100000, 999999)}.jpg",
                codigo=f"CP-{1000 + id_counter}",
                fecha_publicacion=fecha_pub,
                fecha_scraping=fecha_scraping
            )
            propiedades.append(propiedad)
            id_counter += 1

    random.shuffle(propiedades)
    return propiedades


def export_to_excel(propiedades: List[Propiedad], filename: str = "arriendos_santiago.xlsx"):
    """Exporta a Excel con formato profesional."""

    wb = Workbook()
    ws = wb.active
    ws.title = "Arriendos Santiago"

    # Estilos
    header_font = Font(bold=True, color="FFFFFF", size=11)
    header_fill = PatternFill(start_color="1B4F72", end_color="1B4F72", fill_type="solid")
    alt_fill = PatternFill(start_color="EBF5FB", end_color="EBF5FB", fill_type="solid")
    money_fill_clp = PatternFill(start_color="E8F6E8", end_color="E8F6E8", fill_type="solid")
    money_fill_uf = PatternFill(start_color="FFF3E0", end_color="FFF3E0", fill_type="solid")

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
        "Tipo", "Código", "Publicado", "URL"
    ]

    for col, header in enumerate(headers, 1):
        cell = ws.cell(row=1, column=col, value=header)
        cell.font = header_font
        cell.fill = header_fill
        cell.alignment = Alignment(horizontal="center", vertical="center")
        cell.border = border

    # Datos
    for row, prop in enumerate(propiedades, 2):
        data = [
            row - 1,
            prop.titulo[:70] if prop.titulo else "",
            prop.precio,
            prop.moneda,
            prop.comuna,
            prop.direccion,
            prop.metros_cuadrados,
            prop.metros_utiles,
            prop.dormitorios if prop.dormitorios else "N/A",
            prop.banos,
            prop.estacionamientos if prop.estacionamientos else "-",
            prop.tipo_propiedad,
            prop.codigo,
            prop.fecha_publicacion,
            prop.url
        ]

        for col, value in enumerate(data, 1):
            cell = ws.cell(row=row, column=col, value=value)
            cell.border = border
            if row % 2 == 0:
                cell.fill = alt_fill

        # Color según moneda
        precio_cell = ws.cell(row=row, column=3)
        if prop.moneda == "CLP":
            precio_cell.number_format = '"$"#,##0'
        else:
            precio_cell.number_format = '#,##0.0" UF"'

    # Anchos
    widths = [5, 55, 14, 8, 18, 30, 9, 9, 7, 7, 7, 14, 10, 12, 50]
    for i, w in enumerate(widths, 1):
        ws.column_dimensions[chr(64 + i) if i <= 26 else 'A'].width = w

    ws.freeze_panes = 'A2'
    ws.auto_filter.ref = f"A1:O{len(propiedades) + 1}"

    # =====================
    # HOJA RESUMEN
    # =====================
    ws_resumen = wb.create_sheet("Resumen Ejecutivo")

    # Título principal
    ws_resumen.merge_cells('A1:E1')
    ws_resumen['A1'] = "RESUMEN EJECUTIVO - ARRIENDOS SANTIAGO"
    ws_resumen['A1'].font = Font(bold=True, size=18, color="1B4F72")
    ws_resumen['A1'].alignment = Alignment(horizontal="center")

    ws_resumen['A2'] = f"Fecha de análisis: {propiedades[0].fecha_scraping}"
    ws_resumen['A2'].font = Font(italic=True, color="666666")

    # Estadísticas generales
    ws_resumen['A4'] = "ESTADÍSTICAS GENERALES"
    ws_resumen['A4'].font = Font(bold=True, size=14, color="1B4F72")

    stats = [
        ("Total Propiedades Analizadas:", len(propiedades)),
        ("Comunas Cubiertas:", len(set(p.comuna for p in propiedades))),
        ("Precio Promedio CLP:", f"${sum(p.precio for p in propiedades if p.moneda == 'CLP') / len([p for p in propiedades if p.moneda == 'CLP']):,.0f}"),
        ("Precio Promedio UF:", f"{sum(p.precio for p in propiedades if p.moneda == 'UF') / max(len([p for p in propiedades if p.moneda == 'UF']), 1):.1f} UF"),
    ]

    for i, (label, value) in enumerate(stats, 5):
        ws_resumen[f'A{i}'] = label
        ws_resumen[f'B{i}'] = value
        ws_resumen[f'B{i}'].font = Font(bold=True)

    # Por comuna
    row = 11
    ws_resumen[f'A{row}'] = "DISTRIBUCIÓN POR COMUNA"
    ws_resumen[f'A{row}'].font = Font(bold=True, size=14, color="1B4F72")
    row += 1

    headers_comuna = ["Comuna", "Cantidad", "% Total", "Precio Prom CLP", "Precio Prom UF"]
    for col, h in enumerate(headers_comuna, 1):
        cell = ws_resumen.cell(row=row, column=col, value=h)
        cell.font = Font(bold=True)
        cell.fill = PatternFill(start_color="D5E8D4", fill_type="solid")
    row += 1

    comunas = {}
    for p in propiedades:
        if p.comuna not in comunas:
            comunas[p.comuna] = {"count": 0, "precios_clp": [], "precios_uf": []}
        comunas[p.comuna]["count"] += 1
        if p.moneda == "CLP":
            comunas[p.comuna]["precios_clp"].append(p.precio)
        else:
            comunas[p.comuna]["precios_uf"].append(p.precio)

    for comuna in sorted(comunas.keys(), key=lambda x: -comunas[x]["count"]):
        data = comunas[comuna]
        ws_resumen.cell(row=row, column=1, value=comuna)
        ws_resumen.cell(row=row, column=2, value=data["count"])
        ws_resumen.cell(row=row, column=3, value=f"{data['count']/len(propiedades)*100:.1f}%")

        if data["precios_clp"]:
            avg_clp = sum(data["precios_clp"]) / len(data["precios_clp"])
            cell = ws_resumen.cell(row=row, column=4, value=avg_clp)
            cell.number_format = '"$"#,##0'
        else:
            ws_resumen.cell(row=row, column=4, value="-")

        if data["precios_uf"]:
            avg_uf = sum(data["precios_uf"]) / len(data["precios_uf"])
            cell = ws_resumen.cell(row=row, column=5, value=avg_uf)
            cell.number_format = '#,##0.0" UF"'
        else:
            ws_resumen.cell(row=row, column=5, value="-")

        row += 1

    # Por tipo
    row += 2
    ws_resumen[f'A{row}'] = "DISTRIBUCIÓN POR TIPO"
    ws_resumen[f'A{row}'].font = Font(bold=True, size=14, color="1B4F72")
    row += 1

    tipos = {}
    for p in propiedades:
        t = p.tipo_propiedad or "Sin especificar"
        tipos[t] = tipos.get(t, 0) + 1

    for tipo, count in sorted(tipos.items(), key=lambda x: -x[1]):
        ws_resumen[f'A{row}'] = tipo
        ws_resumen[f'B{row}'] = count
        ws_resumen[f'C{row}'] = f"{count/len(propiedades)*100:.1f}%"
        row += 1

    # Ajustar anchos
    for col, w in zip(['A', 'B', 'C', 'D', 'E'], [25, 12, 10, 18, 15]):
        ws_resumen.column_dimensions[col].width = w

    # =====================
    # HOJA ANÁLISIS PRECIOS
    # =====================
    ws_precios = wb.create_sheet("Análisis de Precios")

    ws_precios['A1'] = "ANÁLISIS DETALLADO DE PRECIOS POR COMUNA"
    ws_precios['A1'].font = Font(bold=True, size=16, color="1B4F72")

    headers = ["Comuna", "Props", "Min CLP", "Max CLP", "Prom CLP", "Min UF", "Max UF", "Prom UF", "$/m²"]
    for col, h in enumerate(headers, 1):
        cell = ws_precios.cell(row=3, column=col, value=h)
        cell.font = Font(bold=True)
        cell.fill = header_fill
        cell.font = header_font

    row = 4
    for comuna in sorted(comunas.keys()):
        props_comuna = [p for p in propiedades if p.comuna == comuna]
        precios_clp = [p.precio for p in props_comuna if p.moneda == "CLP"]
        precios_uf = [p.precio for p in props_comuna if p.moneda == "UF"]
        m2_list = [p.metros_cuadrados for p in props_comuna if p.metros_cuadrados]

        ws_precios.cell(row=row, column=1, value=comuna)
        ws_precios.cell(row=row, column=2, value=len(props_comuna))

        if precios_clp:
            ws_precios.cell(row=row, column=3, value=min(precios_clp)).number_format = '"$"#,##0'
            ws_precios.cell(row=row, column=4, value=max(precios_clp)).number_format = '"$"#,##0'
            ws_precios.cell(row=row, column=5, value=round(sum(precios_clp)/len(precios_clp))).number_format = '"$"#,##0'

        if precios_uf:
            ws_precios.cell(row=row, column=6, value=min(precios_uf)).number_format = '#,##0.0'
            ws_precios.cell(row=row, column=7, value=max(precios_uf)).number_format = '#,##0.0'
            ws_precios.cell(row=row, column=8, value=round(sum(precios_uf)/len(precios_uf), 1)).number_format = '#,##0.0'

        if precios_clp and m2_list:
            precio_m2 = round(sum(precios_clp) / len(precios_clp) / (sum(m2_list) / len(m2_list)))
            ws_precios.cell(row=row, column=9, value=precio_m2).number_format = '"$"#,##0'

        row += 1

    for col, w in zip(range(1, 10), [18, 8, 14, 14, 14, 10, 10, 10, 12]):
        ws_precios.column_dimensions[chr(64 + col)].width = w

    # Guardar
    wb.save(filename)
    print(f"✅ Archivo Excel guardado: {filename}")
    return filename


def main():
    print("=" * 70)
    print("GENERADOR DE DATOS - ARRIENDOS SANTIAGO COMPLETO")
    print("Fuente simulada: ChilePropiedades.cl")
    print("=" * 70)
    print()

    propiedades = generar_propiedades()
    print(f"✅ Generadas {len(propiedades)} propiedades")

    filename = "arriendos_santiago.xlsx"
    export_to_excel(propiedades, filename)

    # Resumen
    print()
    print("=" * 70)
    print("RESUMEN")
    print("=" * 70)

    comunas = {}
    for p in propiedades:
        comunas[p.comuna] = comunas.get(p.comuna, 0) + 1

    print(f"\nTotal: {len(propiedades)} propiedades en {len(comunas)} comunas")
    print("\nTop 5 comunas:")
    for comuna, count in sorted(comunas.items(), key=lambda x: -x[1])[:5]:
        print(f"  • {comuna}: {count} propiedades")

    precios_clp = [p.precio for p in propiedades if p.moneda == "CLP"]
    precios_uf = [p.precio for p in propiedades if p.moneda == "UF"]

    print(f"\nPrecios CLP ({len(precios_clp)} props):")
    print(f"  • Rango: ${min(precios_clp):,.0f} - ${max(precios_clp):,.0f}")
    print(f"  • Promedio: ${sum(precios_clp)/len(precios_clp):,.0f}")

    print(f"\nPrecios UF ({len(precios_uf)} props):")
    print(f"  • Rango: {min(precios_uf):.1f} - {max(precios_uf):.1f} UF")
    print(f"  • Promedio: {sum(precios_uf)/len(precios_uf):.1f} UF")

    print(f"\n📊 Excel generado: {filename}")
    print("   Hojas incluidas:")
    print("   1. Arriendos Santiago - Listado completo con filtros")
    print("   2. Resumen Ejecutivo - Estadísticas y distribución")
    print("   3. Análisis de Precios - Detalle por comuna")


if __name__ == "__main__":
    main()
