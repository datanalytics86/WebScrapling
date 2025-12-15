#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Generador de Excel con datos de ejemplo de arriendos en Las Condes.
Simula datos realistas basados en el mercado inmobiliario de Las Condes, Chile.
"""

import random
from datetime import datetime
from dataclasses import dataclass
from typing import List, Optional

from openpyxl import Workbook
from openpyxl.styles import Font, Alignment, PatternFill, Border, Side
from openpyxl.chart import LineChart, Reference


@dataclass
class Propiedad:
    """Estructura de datos para una propiedad."""
    titulo: str
    precio: Optional[float]
    moneda: str
    ubicacion: str
    metros_cuadrados: Optional[int]
    dormitorios: Optional[int]
    banos: Optional[int]
    url: str
    imagen_url: Optional[str]
    tipo_propiedad: Optional[str]
    gastos_comunes: Optional[float]
    fecha_scraping: str


def generar_propiedades_ejemplo() -> List[Propiedad]:
    """
    Genera datos de ejemplo realistas de arriendos en Las Condes.
    Basado en precios y características del mercado real.
    """

    # Sectores de Las Condes
    sectores = [
        "Las Condes, Estoril",
        "Las Condes, El Golf",
        "Las Condes, Kennedy",
        "Las Condes, Apoquindo",
        "Las Condes, Los Dominicos",
        "Las Condes, Av. Colón",
        "Las Condes, Manquehue",
        "Las Condes, Nueva Las Condes",
        "Las Condes, Rotonda Atenas",
        "Las Condes, Isidora Goyenechea",
    ]

    # Tipos de propiedad y sus características típicas
    tipos_config = {
        "Departamento": {
            "m2_range": (35, 180),
            "dorm_range": (1, 4),
            "precio_m2_clp": (12000, 25000),  # Por m2 mensual
            "precio_uf_range": (15, 80),
            "gc_range": (80000, 350000),
        },
        "Estudio": {
            "m2_range": (20, 45),
            "dorm_range": (1, 1),
            "precio_m2_clp": (15000, 28000),
            "precio_uf_range": (12, 30),
            "gc_range": (50000, 150000),
        },
        "Casa": {
            "m2_range": (150, 400),
            "dorm_range": (3, 6),
            "precio_m2_clp": (8000, 18000),
            "precio_uf_range": (60, 200),
            "gc_range": (0, 100000),
        },
        "Oficina": {
            "m2_range": (30, 200),
            "dorm_range": (0, 0),
            "precio_m2_clp": (10000, 22000),
            "precio_uf_range": (20, 100),
            "gc_range": (100000, 400000),
        },
    }

    propiedades = []
    fecha_scraping = datetime.now().strftime("%Y-%m-%d %H:%M:%S")

    # Generar propiedades por tipo
    distribucion = [
        ("Departamento", 55),
        ("Estudio", 15),
        ("Casa", 20),
        ("Oficina", 10),
    ]

    id_counter = 1

    for tipo, cantidad in distribucion:
        config = tipos_config[tipo]

        for _ in range(cantidad):
            m2 = random.randint(*config["m2_range"])
            dorms = random.randint(*config["dorm_range"])
            banos = max(1, dorms) if tipo != "Oficina" else random.randint(1, 3)

            # 70% en CLP, 30% en UF
            if random.random() < 0.7:
                moneda = "CLP"
                precio_m2 = random.randint(*config["precio_m2_clp"])
                precio = m2 * precio_m2
                # Redondear a miles
                precio = round(precio / 10000) * 10000
            else:
                moneda = "UF"
                precio = random.uniform(*config["precio_uf_range"])
                precio = round(precio, 1)

            sector = random.choice(sectores)
            gc = random.randint(*config["gc_range"]) if config["gc_range"][1] > 0 else None
            if gc:
                gc = round(gc / 10000) * 10000

            # Generar título descriptivo
            if tipo == "Departamento":
                titulo = f"Departamento {dorms}D {banos}B {m2}m² en {sector.split(', ')[1]}"
                if random.random() < 0.3:
                    titulo += " con estacionamiento"
                if random.random() < 0.2:
                    titulo += " amoblado"
            elif tipo == "Estudio":
                titulo = f"Estudio {m2}m² en {sector.split(', ')[1]}"
                if random.random() < 0.4:
                    titulo += " amoblado"
            elif tipo == "Casa":
                titulo = f"Casa {dorms}D {banos}B {m2}m² en {sector.split(', ')[1]}"
                if random.random() < 0.2:
                    titulo += " con piscina"
                if random.random() < 0.3:
                    titulo += " con jardín"
            else:
                titulo = f"Oficina {m2}m² en {sector.split(', ')[1]}"
                if random.random() < 0.4:
                    titulo += " implementada"

            propiedad = Propiedad(
                titulo=titulo,
                precio=precio,
                moneda=moneda,
                ubicacion=sector,
                metros_cuadrados=m2,
                dormitorios=dorms if tipo != "Oficina" else None,
                banos=banos,
                url=f"https://inmuebles.mercadolibre.cl/MLC-{1000000 + id_counter}",
                imagen_url=f"https://http2.mlstatic.com/D_NQ_NP_{random.randint(100000, 999999)}-MLC{random.randint(10000000, 99999999)}_O.webp",
                tipo_propiedad=tipo,
                gastos_comunes=gc,
                fecha_scraping=fecha_scraping
            )
            propiedades.append(propiedad)
            id_counter += 1

    # Mezclar aleatoriamente
    random.shuffle(propiedades)

    return propiedades


def export_to_excel(propiedades: List[Propiedad], filename: str = "arriendos_las_condes.xlsx"):
    """
    Exporta las propiedades a un archivo Excel con formato profesional.
    """
    wb = Workbook()
    ws = wb.active
    ws.title = "Arriendos Las Condes"

    # Estilos
    header_font = Font(bold=True, color="FFFFFF", size=11)
    header_fill = PatternFill(start_color="2E86AB", end_color="2E86AB", fill_type="solid")
    header_alignment = Alignment(horizontal="center", vertical="center", wrap_text=True)

    alt_fill = PatternFill(start_color="F0F8FF", end_color="F0F8FF", fill_type="solid")

    border = Border(
        left=Side(style='thin', color='CCCCCC'),
        right=Side(style='thin', color='CCCCCC'),
        top=Side(style='thin', color='CCCCCC'),
        bottom=Side(style='thin', color='CCCCCC')
    )

    # Headers
    headers = [
        "ID", "Título", "Precio", "Moneda", "Ubicación", "M²",
        "Dormitorios", "Baños", "Tipo", "Gastos Comunes", "URL"
    ]

    for col, header in enumerate(headers, 1):
        cell = ws.cell(row=1, column=col, value=header)
        cell.font = header_font
        cell.fill = header_fill
        cell.alignment = header_alignment
        cell.border = border

    # Datos
    for row, prop in enumerate(propiedades, 2):
        ws.cell(row=row, column=1, value=row - 1)
        ws.cell(row=row, column=2, value=prop.titulo)
        ws.cell(row=row, column=3, value=prop.precio)
        ws.cell(row=row, column=4, value=prop.moneda)
        ws.cell(row=row, column=5, value=prop.ubicacion)
        ws.cell(row=row, column=6, value=prop.metros_cuadrados)
        ws.cell(row=row, column=7, value=prop.dormitorios if prop.dormitorios else "N/A")
        ws.cell(row=row, column=8, value=prop.banos)
        ws.cell(row=row, column=9, value=prop.tipo_propiedad)
        ws.cell(row=row, column=10, value=prop.gastos_comunes)
        ws.cell(row=row, column=11, value=prop.url)

        # Aplicar bordes y colores alternados
        for col in range(1, 12):
            cell = ws.cell(row=row, column=col)
            cell.border = border
            if row % 2 == 0:
                cell.fill = alt_fill

    # Ajustar anchos de columna
    column_widths = [5, 55, 15, 8, 30, 8, 12, 8, 15, 15, 50]
    for i, width in enumerate(column_widths, 1):
        col_letter = chr(64 + i) if i <= 26 else 'A' + chr(64 + i - 26)
        ws.column_dimensions[col_letter].width = width

    # Formato de precio CLP
    for row in range(2, len(propiedades) + 2):
        cell = ws.cell(row=row, column=3)
        moneda = ws.cell(row=row, column=4).value
        if cell.value:
            if moneda == "CLP":
                cell.number_format = '"$"#,##0'
            else:
                cell.number_format = '#,##0.0" UF"'

        # Formato gastos comunes
        gc_cell = ws.cell(row=row, column=10)
        if gc_cell.value:
            gc_cell.number_format = '"$"#,##0'

    # Congelar primera fila
    ws.freeze_panes = 'A2'

    # =====================
    # HOJA DE RESUMEN
    # =====================
    ws_summary = wb.create_sheet("Resumen")

    # Título
    ws_summary.merge_cells('A1:D1')
    ws_summary['A1'] = "RESUMEN DE ARRIENDOS - LAS CONDES"
    ws_summary['A1'].font = Font(bold=True, size=16, color="2E86AB")
    ws_summary['A1'].alignment = Alignment(horizontal="center")

    ws_summary['A2'] = f"Fecha de scraping: {propiedades[0].fecha_scraping}"
    ws_summary['A2'].font = Font(italic=True, color="666666")

    # Totales
    ws_summary['A4'] = "ESTADÍSTICAS GENERALES"
    ws_summary['A4'].font = Font(bold=True, size=12)

    ws_summary['A5'] = "Total Propiedades:"
    ws_summary['B5'] = len(propiedades)
    ws_summary['B5'].font = Font(bold=True)

    # Por tipo
    tipos = {}
    for p in propiedades:
        tipo = p.tipo_propiedad or "Sin especificar"
        tipos[tipo] = tipos.get(tipo, 0) + 1

    ws_summary['A7'] = "POR TIPO DE PROPIEDAD"
    ws_summary['A7'].font = Font(bold=True, size=12)

    row = 8
    for tipo, count in sorted(tipos.items(), key=lambda x: -x[1]):
        ws_summary[f'A{row}'] = tipo
        ws_summary[f'B{row}'] = count
        ws_summary[f'C{row}'] = f"{count/len(propiedades)*100:.1f}%"
        row += 1

    # Por sector
    sectores = {}
    for p in propiedades:
        sector = p.ubicacion.split(", ")[1] if ", " in p.ubicacion else p.ubicacion
        sectores[sector] = sectores.get(sector, 0) + 1

    row += 1
    ws_summary[f'A{row}'] = "POR SECTOR"
    ws_summary[f'A{row}'].font = Font(bold=True, size=12)
    row += 1

    for sector, count in sorted(sectores.items(), key=lambda x: -x[1]):
        ws_summary[f'A{row}'] = sector
        ws_summary[f'B{row}'] = count
        row += 1

    # Precios
    row += 1
    ws_summary[f'A{row}'] = "ANÁLISIS DE PRECIOS"
    ws_summary[f'A{row}'].font = Font(bold=True, size=12)
    row += 1

    # CLP
    precios_clp = [p.precio for p in propiedades if p.moneda == "CLP" and p.precio]
    if precios_clp:
        ws_summary[f'A{row}'] = "Precios en CLP:"
        ws_summary[f'A{row}'].font = Font(bold=True)
        row += 1
        ws_summary[f'A{row}'] = "  Mínimo:"
        ws_summary[f'B{row}'] = min(precios_clp)
        ws_summary[f'B{row}'].number_format = '"$"#,##0'
        row += 1
        ws_summary[f'A{row}'] = "  Máximo:"
        ws_summary[f'B{row}'] = max(precios_clp)
        ws_summary[f'B{row}'].number_format = '"$"#,##0'
        row += 1
        ws_summary[f'A{row}'] = "  Promedio:"
        ws_summary[f'B{row}'] = round(sum(precios_clp) / len(precios_clp))
        ws_summary[f'B{row}'].number_format = '"$"#,##0'
        row += 1
        ws_summary[f'A{row}'] = "  Cantidad:"
        ws_summary[f'B{row}'] = len(precios_clp)
        row += 2

    # UF
    precios_uf = [p.precio for p in propiedades if p.moneda == "UF" and p.precio]
    if precios_uf:
        ws_summary[f'A{row}'] = "Precios en UF:"
        ws_summary[f'A{row}'].font = Font(bold=True)
        row += 1
        ws_summary[f'A{row}'] = "  Mínimo:"
        ws_summary[f'B{row}'] = min(precios_uf)
        ws_summary[f'B{row}'].number_format = '#,##0.0" UF"'
        row += 1
        ws_summary[f'A{row}'] = "  Máximo:"
        ws_summary[f'B{row}'] = max(precios_uf)
        ws_summary[f'B{row}'].number_format = '#,##0.0" UF"'
        row += 1
        ws_summary[f'A{row}'] = "  Promedio:"
        ws_summary[f'B{row}'] = round(sum(precios_uf) / len(precios_uf), 1)
        ws_summary[f'B{row}'].number_format = '#,##0.0" UF"'
        row += 1
        ws_summary[f'A{row}'] = "  Cantidad:"
        ws_summary[f'B{row}'] = len(precios_uf)

    # Ajustar anchos
    ws_summary.column_dimensions['A'].width = 25
    ws_summary.column_dimensions['B'].width = 15
    ws_summary.column_dimensions['C'].width = 10

    # =====================
    # HOJA POR TIPO
    # =====================
    ws_tipo = wb.create_sheet("Análisis por Tipo")

    ws_tipo['A1'] = "ANÁLISIS DETALLADO POR TIPO DE PROPIEDAD"
    ws_tipo['A1'].font = Font(bold=True, size=14)

    row = 3
    for tipo in ["Departamento", "Estudio", "Casa", "Oficina"]:
        props_tipo = [p for p in propiedades if p.tipo_propiedad == tipo]
        if not props_tipo:
            continue

        ws_tipo[f'A{row}'] = tipo.upper()
        ws_tipo[f'A{row}'].font = Font(bold=True, size=12, color="2E86AB")
        row += 1

        ws_tipo[f'A{row}'] = "Cantidad:"
        ws_tipo[f'B{row}'] = len(props_tipo)
        row += 1

        # M2 promedio
        m2_list = [p.metros_cuadrados for p in props_tipo if p.metros_cuadrados]
        if m2_list:
            ws_tipo[f'A{row}'] = "M² promedio:"
            ws_tipo[f'B{row}'] = round(sum(m2_list) / len(m2_list))
            row += 1

        # Precio promedio CLP
        precios = [p.precio for p in props_tipo if p.moneda == "CLP" and p.precio]
        if precios:
            ws_tipo[f'A{row}'] = "Precio promedio (CLP):"
            ws_tipo[f'B{row}'] = round(sum(precios) / len(precios))
            ws_tipo[f'B{row}'].number_format = '"$"#,##0'
            row += 1

        # Precio promedio UF
        precios_uf = [p.precio for p in props_tipo if p.moneda == "UF" and p.precio]
        if precios_uf:
            ws_tipo[f'A{row}'] = "Precio promedio (UF):"
            ws_tipo[f'B{row}'] = round(sum(precios_uf) / len(precios_uf), 1)
            ws_tipo[f'B{row}'].number_format = '#,##0.0" UF"'
            row += 1

        row += 1

    ws_tipo.column_dimensions['A'].width = 25
    ws_tipo.column_dimensions['B'].width = 15

    # Guardar
    wb.save(filename)
    print(f"✅ Archivo Excel guardado: {filename}")
    return filename


def main():
    """Función principal."""
    print("=" * 60)
    print("GENERADOR DE DATOS DE ARRIENDOS - LAS CONDES")
    print("=" * 60)
    print()

    # Generar datos de ejemplo
    print("Generando datos de ejemplo basados en el mercado real...")
    propiedades = generar_propiedades_ejemplo()

    print(f"✅ Generadas {len(propiedades)} propiedades de ejemplo")
    print()

    # Exportar a Excel
    filename = "arriendos_las_condes.xlsx"
    export_to_excel(propiedades, filename)

    # Mostrar resumen
    print()
    print("=" * 60)
    print("RESUMEN")
    print("=" * 60)

    # Por tipo
    tipos = {}
    for p in propiedades:
        tipo = p.tipo_propiedad or "Sin especificar"
        tipos[tipo] = tipos.get(tipo, 0) + 1

    print("\nPor tipo de propiedad:")
    for tipo, count in sorted(tipos.items(), key=lambda x: -x[1]):
        print(f"  • {tipo}: {count} ({count/len(propiedades)*100:.1f}%)")

    # Rango de precios CLP
    precios_clp = [p.precio for p in propiedades if p.moneda == "CLP" and p.precio]
    if precios_clp:
        print(f"\nPrecios en CLP ({len(precios_clp)} propiedades):")
        print(f"  • Mínimo: ${min(precios_clp):,.0f}")
        print(f"  • Máximo: ${max(precios_clp):,.0f}")
        print(f"  • Promedio: ${sum(precios_clp)/len(precios_clp):,.0f}")

    # Rango de precios UF
    precios_uf = [p.precio for p in propiedades if p.moneda == "UF" and p.precio]
    if precios_uf:
        print(f"\nPrecios en UF ({len(precios_uf)} propiedades):")
        print(f"  • Mínimo: {min(precios_uf):.1f} UF")
        print(f"  • Máximo: {max(precios_uf):.1f} UF")
        print(f"  • Promedio: {sum(precios_uf)/len(precios_uf):.1f} UF")

    print()
    print(f"📊 Archivo Excel generado: {filename}")
    print("   Incluye 3 hojas:")
    print("   1. Arriendos Las Condes - Listado completo")
    print("   2. Resumen - Estadísticas generales")
    print("   3. Análisis por Tipo - Desglose detallado")

    return propiedades


if __name__ == "__main__":
    propiedades = main()
