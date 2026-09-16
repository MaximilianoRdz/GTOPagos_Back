from io import BytesIO
from datetime import datetime
import pandas as pd
from openpyxl.styles import Font, PatternFill, Alignment, Border, Side

from reportlab.lib import colors
from reportlab.lib.pagesizes import letter
from reportlab.platypus import SimpleDocTemplate, Table, TableStyle, Paragraph, Spacer
from reportlab.lib.styles import getSampleStyleSheet, ParagraphStyle


def generate_dashboard_excel_export(records) -> bytes:
    """Genera un archivo Excel con el listado simple de movimientos de un dashboard."""
    data = []
    for r in records:
        data.append({
            "Fecha": r.record_date,
            "Descripción": r.description,
            "Categoría": r.category.name if r.category else 'Sin categoría',
            "Monto": r.amount if r.record_type.behavior == 'INCOME' else -r.amount,
            "Tipo": r.record_type.behavior
        })

    df = pd.DataFrame(data)
    output = BytesIO()
    with pd.ExcelWriter(output, engine='openpyxl') as writer:
        df.to_excel(writer, index=False, sheet_name='Movimientos')

    output.seek(0)
    return output.read()


def generate_report_excel_export(records) -> bytes:
    """Genera un archivo Excel profesional estilizado para el reporte financiero."""
    data = []
    for r in records:
        is_income = r.record_type.behavior == 'INCOME'
        data.append({
            "Fecha": str(r.record_date),
            "Descripción": r.description,
            "Categoría": r.category.name if r.category else 'Sin categoría',
            "Monto": float(r.amount if is_income else -r.amount),
            "Tipo": 'Ingreso' if is_income else 'Gasto'
        })

    df = pd.DataFrame(data)
    output = BytesIO()

    with pd.ExcelWriter(output, engine='openpyxl') as writer:
        df.to_excel(writer, index=False, sheet_name='Reporte')

        worksheet = writer.sheets['Reporte']

        header_font = Font(bold=True, color="FFFFFF")
        header_fill = PatternFill(start_color="0F172A", end_color="0F172A", fill_type="solid")  # Slate 900
        alignment_center = Alignment(horizontal="center", vertical="center")
        alignment_left = Alignment(horizontal="left", vertical="center")

        border_style = Border(
            left=Side(style='thin', color='E5E7EB'),
            right=Side(style='thin', color='E5E7EB'),
            top=Side(style='thin', color='E5E7EB'),
            bottom=Side(style='thin', color='E5E7EB')
        )

        column_widths = {'A': 15, 'B': 45, 'C': 25, 'D': 15, 'E': 20}
        for col_letter, width in column_widths.items():
            worksheet.column_dimensions[col_letter].width = width

        for cell in worksheet[1]:
            cell.font = header_font
            cell.fill = header_fill
            cell.alignment = alignment_center
            cell.border = border_style

        for row_idx, row in enumerate(worksheet.iter_rows(min_row=2, max_row=len(df) + 1), start=2):
            fill_color = "F8FAFC" if row_idx % 2 == 0 else "FFFFFF"
            row_fill = PatternFill(start_color=fill_color, end_color=fill_color, fill_type="solid")

            for cell in row:
                cell.fill = row_fill
                cell.border = border_style
                cell.alignment = alignment_left

                if cell.column == 5:  # Monto
                    cell.number_format = '"$"#,##0.00'
                    if cell.value is not None:
                        try:
                            val = float(cell.value)
                            cell.font = Font(color="059669") if val > 0 else Font(color="DC2626")
                        except (ValueError, TypeError):
                            pass
                    cell.alignment = Alignment(horizontal="right", vertical="center")

    output.seek(0)
    return output.read()


def generate_report_pdf_export(records, dashboard_name: str, user_name: str, start_date: str = None, end_date: str = None) -> bytes:
    """Genera el reporte financiero en PDF con la identidad visual moderna de GTOPagos."""
    output = BytesIO()
    doc = SimpleDocTemplate(
        output,
        pagesize=letter,
        rightMargin=36,
        leftMargin=36,
        topMargin=36,
        bottomMargin=36
    )
    elements = []
    styles = getSampleStyleSheet()

    generado = datetime.now().strftime("%d/%m/%Y %H:%M")

    # Estilos tipográficos
    brand_style = ParagraphStyle(
        'BrandHeader',
        parent=styles['Normal'],
        fontName='Helvetica-Bold',
        fontSize=14,
        textColor=colors.HexColor('#059669'),
        leading=18,
    )

    title_style = ParagraphStyle(
        'ModernTitle',
        parent=styles['Normal'],
        fontName='Helvetica-Bold',
        fontSize=20,
        textColor=colors.HexColor('#0f172a'),
        leading=24,
        spaceAfter=4
    )

    meta_style = ParagraphStyle(
        'MetaText',
        parent=styles['Normal'],
        fontName='Helvetica',
        fontSize=9,
        textColor=colors.HexColor('#475569'),
        leading=13,
    )

    meta_right_style = ParagraphStyle(
        'MetaRightText',
        parent=styles['Normal'],
        fontName='Helvetica',
        fontSize=9,
        textColor=colors.HexColor('#475569'),
        leading=14,
        alignment=2
    )

    # Encabezado con branding de GTOPagos
    left_header = [
        Paragraph('<font color="#10b981">&#9679;</font> <b>GTOPagos</b> &nbsp;<font color="#94a3b8">| Control Financiero</font>', brand_style),
        Spacer(1, 4),
        Paragraph("Reporte Financiero", title_style),
        Paragraph(f"<b>Cuenta / Espacio:</b> {dashboard_name} &nbsp;&bull;&nbsp; <b>Titular:</b> {user_name}", meta_style)
    ]

    right_header = [
        Paragraph(f"<b>Período:</b> {start_date or 'Inicio'} al {end_date or 'Fin'}", meta_right_style),
        Paragraph(f"<b>Generado:</b> {generado}", meta_right_style),
        Paragraph(f"<b>Movimientos:</b> {records.count() if hasattr(records, 'count') else len(records)}", meta_right_style)
    ]

    header_table = Table([[left_header, right_header]], colWidths=[350, 190])
    header_table.setStyle(TableStyle([
        ('VALIGN', (0, 0), (-1, -1), 'TOP'),
        ('BOTTOMPADDING', (0, 0), (-1, -1), 10),
        ('LINEBELOW', (0, 0), (-1, -1), 1.5, colors.HexColor('#10b981')),
    ]))
    elements.append(header_table)
    elements.append(Spacer(1, 14))

    # Totales y filas
    total_income = 0
    total_expense = 0
    rows_data = []

    for r in records:
        is_income = r.record_type.behavior == 'INCOME'
        if is_income:
            total_income += r.amount
            amt_formatted = f"+${r.amount:,.2f}"
        else:
            total_expense += r.amount
            amt_formatted = f"-${r.amount:,.2f}"

        rows_data.append({
            'date': str(r.record_date),
            'desc': r.description[:42] + ('...' if len(r.description) > 42 else ''),
            'cat': r.category.name if r.category else 'General',
            'type': 'Ingreso' if is_income else 'Gasto',
            'amount': amt_formatted,
            'is_income': is_income
        })

    balance = total_income - total_expense
    balance_color = '#15803d' if balance >= 0 else '#b91c1c'
    balance_bg = '#f0fdf4' if balance >= 0 else '#fef2f2'
    balance_box = '#bbf7d0' if balance >= 0 else '#fecaca'

    # KPI Cards (Estilo Dashboard del sistema)
    kpi_label_income = ParagraphStyle('KpiLabelInc', fontName='Helvetica-Bold', fontSize=8, textColor=colors.HexColor('#166534'), leading=10)
    kpi_val_income = ParagraphStyle('KpiValInc', fontName='Helvetica-Bold', fontSize=14, textColor=colors.HexColor('#15803d'), leading=18)

    kpi_label_expense = ParagraphStyle('KpiLabelExp', fontName='Helvetica-Bold', fontSize=8, textColor=colors.HexColor('#991b1b'), leading=10)
    kpi_val_expense = ParagraphStyle('KpiValExp', fontName='Helvetica-Bold', fontSize=14, textColor=colors.HexColor('#b91c1c'), leading=18)

    kpi_label_bal = ParagraphStyle('KpiLabelBal', fontName='Helvetica-Bold', fontSize=8, textColor=colors.HexColor('#1e293b'), leading=10)
    kpi_val_bal = ParagraphStyle('KpiValBal', fontName='Helvetica-Bold', fontSize=14, textColor=colors.HexColor(balance_color), leading=18)

    card_income = [Paragraph('TOTAL INGRESOS', kpi_label_income), Spacer(1, 4), Paragraph(f"+${total_income:,.2f}", kpi_val_income)]
    card_expense = [Paragraph('TOTAL GASTOS', kpi_label_expense), Spacer(1, 4), Paragraph(f"-${total_expense:,.2f}", kpi_val_expense)]
    card_balance = [Paragraph('BALANCE NETO', kpi_label_bal), Spacer(1, 4), Paragraph(f"${balance:,.2f}", kpi_val_bal)]

    kpi_table = Table([[card_income, '', card_expense, '', card_balance]], colWidths=[172, 12, 172, 12, 172])
    kpi_table.setStyle(TableStyle([
        ('BACKGROUND', (0, 0), (0, 0), colors.HexColor('#f0fdf4')),
        ('BOX', (0, 0), (0, 0), 1, colors.HexColor('#bbf7d0')),
        ('TOPPADDING', (0, 0), (0, 0), 8),
        ('BOTTOMPADDING', (0, 0), (0, 0), 8),
        ('LEFTPADDING', (0, 0), (0, 0), 10),
        ('RIGHTPADDING', (0, 0), (0, 0), 10),

        ('BACKGROUND', (2, 0), (2, 0), colors.HexColor('#fef2f2')),
        ('BOX', (2, 0), (2, 0), 1, colors.HexColor('#fecaca')),
        ('TOPPADDING', (2, 0), (2, 0), 8),
        ('BOTTOMPADDING', (2, 0), (2, 0), 8),
        ('LEFTPADDING', (2, 0), (2, 0), 10),
        ('RIGHTPADDING', (2, 0), (2, 0), 10),

        ('BACKGROUND', (4, 0), (4, 0), colors.HexColor(balance_bg)),
        ('BOX', (4, 0), (4, 0), 1, colors.HexColor(balance_box)),
        ('TOPPADDING', (4, 0), (4, 0), 8),
        ('BOTTOMPADDING', (4, 0), (4, 0), 8),
        ('LEFTPADDING', (4, 0), (4, 0), 10),
        ('RIGHTPADDING', (4, 0), (4, 0), 10),
    ]))
    elements.append(kpi_table)
    elements.append(Spacer(1, 16))

    # Tabla de Movimientos
    table_data = [['FECHA', 'DESCRIPCIÓN', 'CATEGORÍA', 'TIPO', 'MONTO']]
    table_styles = [
        ('BACKGROUND', (0, 0), (-1, 0), colors.HexColor('#0f172a')),
        ('TEXTCOLOR', (0, 0), (-1, 0), colors.white),
        ('ALIGN', (0, 0), (-1, 0), 'LEFT'),
        ('ALIGN', (-1, 0), (-1, -1), 'RIGHT'),
        ('FONTNAME', (0, 0), (-1, 0), 'Helvetica-Bold'),
        ('FONTSIZE', (0, 0), (-1, 0), 8.5),
        ('BOTTOMPADDING', (0, 0), (-1, 0), 8),
        ('TOPPADDING', (0, 0), (-1, 0), 8),
    ]

    if not rows_data:
        table_data.append(['', 'No se encontraron movimientos registrados en este período', '', '', ''])
        table_styles.append(('SPAN', (1, 1), (3, 1)))
        table_styles.append(('ALIGN', (1, 1), (3, 1), 'CENTER'))
        table_styles.append(('TEXTCOLOR', (1, 1), (3, 1), colors.HexColor('#94a3b8')))
        table_styles.append(('FONTNAME', (1, 1), (3, 1), 'Helvetica-Oblique'))
        table_styles.append(('TOPPADDING', (0, 1), (-1, 1), 16))
        table_styles.append(('BOTTOMPADDING', (0, 1), (-1, 1), 16))
    else:
        for idx, row in enumerate(rows_data, start=1):
            table_data.append([
                row['date'],
                row['desc'],
                row['cat'],
                row['type'],
                row['amount']
            ])
            bg_color = colors.white if idx % 2 != 0 else colors.HexColor('#f8fafc')
            table_styles.append(('BACKGROUND', (0, idx), (-1, idx), bg_color))
            table_styles.append(('FONTNAME', (0, idx), (-1, idx), 'Helvetica'))
            table_styles.append(('FONTSIZE', (0, idx), (-1, idx), 8.5))
            table_styles.append(('TEXTCOLOR', (0, idx), (2, idx), colors.HexColor('#334155')))
            table_styles.append(('TEXTCOLOR', (3, idx), (3, idx), colors.HexColor('#059669' if row['is_income'] else '#dc2626')))
            table_styles.append(('FONTNAME', (3, idx), (3, idx), 'Helvetica-Bold'))
            table_styles.append(('TEXTCOLOR', (4, idx), (4, idx), colors.HexColor('#059669' if row['is_income'] else '#dc2626')))
            table_styles.append(('FONTNAME', (4, idx), (4, idx), 'Helvetica-Bold'))
            table_styles.append(('BOTTOMPADDING', (0, idx), (-1, idx), 6.5))
            table_styles.append(('TOPPADDING', (0, idx), (-1, idx), 6.5))
            table_styles.append(('LINEBELOW', (0, idx), (-1, idx), 0.5, colors.HexColor('#f1f5f9')))

    main_table = Table(table_data, colWidths=[75, 190, 115, 65, 95])
    main_table.setStyle(TableStyle(table_styles))
    elements.append(main_table)
    elements.append(Spacer(1, 24))

    # Pie de Página Profesional
    footer_style = ParagraphStyle(
        'FooterText',
        parent=styles['Normal'],
        fontName='Helvetica',
        fontSize=8,
        textColor=colors.HexColor('#94a3b8'),
        alignment=1
    )
    elements.append(Paragraph('GTOPagos &bull; Sistema de Gestión Financiera Personal &bull; Documento Oficial', footer_style))

    doc.build(elements)
    output.seek(0)
    return output.read()
