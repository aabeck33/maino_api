'''
    Gera um relatório PDF executivo com base em dados de vendas.

'''
from pathlib import Path
from reportlab.lib import colors
from reportlab.lib.pagesizes import A4
from reportlab.platypus import (
    SimpleDocTemplate,
    Paragraph,
    Spacer,
    PageBreak,
    Table,
    TableStyle
)
from reportlab.lib.styles import getSampleStyleSheet
from analytics.processing import SalesAnalytics


def brl(valor):
    return f"R$ {valor:,.2f}"


def generate_executive_pdf(
    analytics,
    filtered_df,
    output_path="relatorio_gerencial.pdf"
):

    doc = SimpleDocTemplate(
        output_path,
        pagesize=A4
    )

    styles = getSampleStyleSheet()

    elements = []

    # ==================================================
    # CAPA
    # ==================================================

    elements.append(
        Paragraph(
            "Relatório Gerencial Comercial",
            styles["Title"]
        )
    )

    elements.append(Spacer(1, 30))

    elements.append(
        Paragraph(
            "Maino Executivo",
            styles["Heading2"]
        )
    )

    elements.append(PageBreak())

    # ==================================================
    # RESUMO EXECUTIVO
    # ==================================================

    profitability_df = analytics.build_profitability_dataset(
        filtered_df
    )

    financial = analytics.calculate_financial_kpis(
        profitability_df
    )

    kpis = SalesAnalytics.calculate_kpis(
        filtered_df
    )

    resumo = [
        ["Indicador", "Valor"],
        ["Faturamento Total", brl(financial["revenue_total"])],
        ["Margem de Contribuição", brl(financial["gross_profit_total"])],
        ["Margem Média", f'{financial["gross_margin_avg"]:.2f}%'],
        ["Pedidos", f'{kpis["total_orders"]:,}'],
        ["Produtos", f'{kpis["unique_products"]:,}'],
        ["Taxa NF", f'{kpis["nf_emission_rate"]:.2f}%']
    ]

    elements.append(
        Paragraph(
            "Resumo Executivo",
            styles["Heading1"]
        )
    )

    table = Table(resumo, colWidths=[220, 180])

    table.setStyle(
        TableStyle([
            ("BACKGROUND", (0,0),(-1,0), colors.HexColor("#2563eb")),
            ("TEXTCOLOR",(0,0),(-1,0),colors.white),
            ("GRID",(0,0),(-1,-1),1,colors.black),
            ("FONTNAME",(0,0),(-1,0),"Helvetica-Bold"),
        ])
    )

    elements.append(table)

    elements.append(PageBreak())

    # ==================================================
    # PRODUTOS
    # ==================================================

    product_summary = analytics.get_profitability_by_product(
        profitability_df
    )

    elements.append(
        Paragraph(
            "Top 10 Produtos",
            styles["Heading1"]
        )
    )

    dados = [["Produto", "Receita", "Margem"]]

    for _, row in product_summary.head(10).iterrows():

        dados.append([
            str(row["Código do Produto"]),
            brl(row["Faturamento"]),
            brl(row["Margem de contribuição"])
        ])

    tabela = Table(
        dados,
        colWidths=[180,120,120]
    )

    tabela.setStyle(
        TableStyle([
            ("BACKGROUND",(0,0),(-1,0),colors.lightgrey),
            ("GRID",(0,0),(-1,-1),1,colors.black),
        ])
    )

    elements.append(tabela)

    elements.append(PageBreak())

    # ==================================================
    # REPRESENTANTES
    # ==================================================

    rep = SalesAnalytics.get_representative_performance(
        filtered_df
    )

    elements.append(
        Paragraph(
            "Representantes",
            styles["Heading1"]
        )
    )

    dados = [[
        "Representante",
        "Receita",
        "Clientes",
        "% Participação"
    ]]

    for _, row in rep.iterrows():

        dados.append([
            str(row["Representante"]),
            brl(row["Receita_Total"]),
            str(row["Clientes_Unicos"]),
            f'{row["Participacao (%)"]:.1f}%'
        ])

    tabela = Table(
        dados,
        colWidths=[180,120,80,80]
    )

    tabela.setStyle(
        TableStyle([
            ("BACKGROUND",(0,0),(-1,0),colors.lightgrey),
            ("GRID",(0,0),(-1,-1),1,colors.black),
        ])
    )

    elements.append(tabela)

    elements.append(PageBreak())

    # ==================================================
    # GEOGRAFIA
    # ==================================================

    geo = SalesAnalytics.get_state_ticket_average(
        filtered_df
    )

    elements.append(
        Paragraph(
            "Geografia de Vendas",
            styles["Heading1"]
        )
    )

    dados = [[
        "UF",
        "Clientes",
        "Receita",
        "Ticket Médio"
    ]]

    for _, row in geo.iterrows():

        dados.append([
            row["UF"],
            int(row["Clientes"]),
            brl(row["Valor_Total"]),
            brl(row["Ticket Médio"])
        ])

    tabela = Table(
        dados,
        colWidths=[60,80,150,150]
    )

    tabela.setStyle(
        TableStyle([
            ("BACKGROUND",(0,0),(-1,0),colors.lightgrey),
            ("GRID",(0,0),(-1,-1),1,colors.black),
        ])
    )

    elements.append(tabela)

    doc.build(elements)

    return Path(output_path)
