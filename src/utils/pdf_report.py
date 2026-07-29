"""Geração de relatório PDF executivo com seções modulares."""

from __future__ import annotations

from datetime import datetime
from pathlib import Path
from typing import Any

import plotly.express as px
import plotly.graph_objects as go
from PIL import Image as PILImage
from plotly.subplots import make_subplots
from reportlab.lib import colors
from reportlab.lib.pagesizes import A4
from reportlab.lib.styles import getSampleStyleSheet
from reportlab.pdfgen import canvas
from reportlab.platypus import Image, PageBreak, Paragraph, SimpleDocTemplate, Spacer, Table, TableStyle

GRAPH_WIDTH = 520
GRAPH_HEIGHT = 320

IMAGES_DIR = Path(__file__).resolve().parent.parent / "utils" / "pdf_assets"
LOGO_PATH = IMAGES_DIR / "logo.png"


def brl(valor: float) -> str:
    """Formata valores monetarios em BRL."""
    return f"R$ {valor:,.2f}"


def add_page_number(canvas_obj: canvas.Canvas, doc: SimpleDocTemplate) -> None:
    """Desenha cabecalho e rodape nas paginas internas."""
    canvas_obj.saveState()
    if doc.page > 1:
        canvas_obj.setStrokeColor(colors.HexColor("#1E3A8A"))
        canvas_obj.line(40, 785, 555, 785)
        canvas_obj.setFont("Helvetica-Bold", 11)
        canvas_obj.drawString(45, 795, "All Drive Transmission")

        canvas_obj.line(40, 45, 555, 45)
        canvas_obj.setFont("Helvetica", 8)
        canvas_obj.drawRightString(545, 30, "Uso Interno - Diretoria")

    canvas_obj.restoreState()


class NumberedCanvas(canvas.Canvas):
    """Canvas com numeracao total de paginas."""

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self._saved_page_states: list[dict] = []

    def showPage(self) -> None:
        self._saved_page_states.append(dict(self.__dict__))
        self._startPage()

    def save(self) -> None:
        total_pages = len(self._saved_page_states)
        for state in self._saved_page_states:
            self.__dict__.update(state)
            self.draw_page_number(total_pages)
            super().showPage()
        super().save()

    def draw_page_number(self, total_pages: int) -> None:
        if self._pageNumber > 1:
            self.setFont("Helvetica", 8)
            self.drawString(45, 30, f"Página {self._pageNumber} de {total_pages}")


def add_cover_footer(canvas_obj: canvas.Canvas, doc: SimpleDocTemplate) -> None:
    """Desenha rodape da capa."""
    canvas_obj.saveState()
    canvas_obj.setFont("Helvetica", 10)
    canvas_obj.drawCentredString(A4[0] / 2, 30, "Uso Interno - Diretoria")
    canvas_obj.restoreState()


def _build_styles() -> Any:
    """Constroi estilos do relatorio."""
    styles = getSampleStyleSheet()
    styles["Title"].textColor = colors.HexColor("#0F172A")
    styles["Title"].fontSize = 28
    styles["Title"].leading = 34
    styles["Heading1"].textColor = colors.HexColor("#1E40AF")
    styles["Heading1"].fontSize = 18
    styles["Heading1"].leading = 24
    styles["Heading2"].textColor = colors.HexColor("#334155")
    styles["Heading2"].fontSize = 14
    styles["Heading2"].leading = 18
    styles["Heading3"].textColor = colors.HexColor("#334155")
    styles["Heading3"].fontSize = 12
    styles["Heading3"].leading = 14
    return styles


def _append_cover(elements: list[Any], styles: Any) -> None:
    """Adiciona capa do documento."""
    if LOGO_PATH.exists():
        img = PILImage.open(LOGO_PATH)
        img_width, img_height = img.size
        desired_width = 220
        desired_height = desired_width * img_height / img_width
        elements.append(Image(str(LOGO_PATH), width=desired_width, height=desired_height))

    elements.append(Spacer(1, 40))
    elements.append(Paragraph("Painel Gerencial Comercial", styles["Heading2"]))
    elements.append(Spacer(1, 120))
    elements.append(Paragraph("RELATÓRIO EXECUTIVO DE VENDAS", styles["Title"]))
    elements.append(Spacer(1, 100))
    elements.append(Paragraph(f"Gerado em: {datetime.now().strftime('%d/%m/%Y %H:%M')}", styles["Heading3"]))
    elements.append(PageBreak())


def _build_monthly_chart(monthly_df: Any) -> Path | None:
    """Gera grafico mensal e salva imagem para uso no PDF."""
    if monthly_df.empty:
        return None

    fig_monthly = make_subplots(specs=[[{"secondary_y": True}]])
    fig_monthly.add_trace(
        go.Bar(x=monthly_df["Mês"], y=monthly_df["Faturamento"], name="Faturamento", marker_color="#1E40AF"),
        secondary_y=False,
    )
    fig_monthly.add_trace(
        go.Scatter(x=monthly_df["Mês"], y=monthly_df["Margem de contribuição"], name="Margem Contribuição", line=dict(color="#16A34A", width=4)),
        secondary_y=False,
    )
    fig_monthly.add_trace(
        go.Scatter(x=monthly_df["Mês"], y=monthly_df["Margem Bruta (%)"], name="Margem %", line=dict(color="#D97706", width=4)),
        secondary_y=True,
    )
    fig_monthly.update_layout(title="Evolução Financeira", height=600, template="plotly_white", legend=dict(orientation="h", y=1.1))
    fig_monthly.update_yaxes(title_text="R$", secondary_y=False)
    fig_monthly.update_yaxes(title_text="Margem (%)", secondary_y=True)

    monthly_png = IMAGES_DIR / "evolucao_mensal.png"
    fig_monthly.write_image(str(monthly_png), width=1600, height=900)
    return monthly_png


def _append_executive_summary(elements: list[Any], styles: Any, financial: dict[str, Any], kpis: dict[str, Any]) -> None:
    """Adiciona bloco de sumario executivo com tabela de indicadores."""
    text = f"""
            O período apresentou faturamento de
            <b>{brl(financial['revenue_total'])}</b>,
            com margem de contribuição média de
            <b>{financial['gross_margin_avg']:.2f}%</b>.
            Considerando uma estrutura de custos
            fixos estimada em
            <b>{financial['fixed_cost_pct']:.2f}%</b>,
            a operação apresenta lucro operacional
            estimado de
            <b>{financial['estimated_operating_profit_pct']:.2f}%</b>
            equivalente a
            <b>{brl(financial['estimated_operating_profit_value'])}</b>.
            """

    summary_table_rows = [
        ["Indicador", "Valor"],
        ["Faturamento Total", brl(financial["revenue_total"])],
        ["Margem de Contribuição", brl(financial["gross_profit_total"])],
        ["Margem Média", f"{financial['gross_margin_avg']:.2f}%"],
        ["Clientes Ativos", f"{kpis['active_customers']:,}"],
        ["Pedidos por Cliente", f"{kpis['orders_per_customer']:.2f}"],
        ["Total de Pedidos", f"{kpis['total_orders']:,}"],
        ["Produtos únicos", f"{kpis['unique_products']:,}"],
        ["Taxa NF", f"{kpis['nf_emission_rate']:.2f}%"],
        ["Lucro Operacional Estimado", brl(financial["estimated_operating_profit_value"])],
        ["Margem Operacional", f"{financial['estimated_operating_profit_pct']:.2f}%"],
    ]

    elements.append(Spacer(1, 20))
    elements.append(Paragraph("Sumário Executivo", styles["Heading1"]))
    elements.append(Paragraph(text, styles["BodyText"]))
    elements.append(Spacer(1, 20))

    table = Table(summary_table_rows, colWidths=[220, 180])
    table.setStyle(
        TableStyle(
            [
                ("BACKGROUND", (0, 0), (-1, 0), colors.HexColor("#1E3A8A")),
                ("TEXTCOLOR", (0, 0), (-1, 0), colors.white),
                ("FONTNAME", (0, 0), (-1, 0), "Helvetica-Bold"),
                ("BOX", (0, 0), (-1, -1), 1.5, colors.HexColor("#1E3A8A")),
                ("INNERGRID", (0, 0), (-1, -1), 0.5, colors.HexColor("#CBD5E1")),
                ("ROWBACKGROUNDS", (0, 1), (-1, -1), [colors.HexColor("#F8FAFC"), colors.white]),
                ("TOPPADDING", (0, 0), (-1, -1), 10),
                ("BOTTOMPADDING", (0, 0), (-1, -1), 10),
            ]
        )
    )
    elements.append(table)


def _append_monthly_section(elements: list[Any], styles: Any, monthly_df: Any, monthly_png: Path | None) -> None:
    """Adiciona seção de evolução mensal."""
    if monthly_df.empty or len(monthly_df) <= 1:
        return

    first_revenue = monthly_df.iloc[0]["Faturamento"]
    last_revenue = monthly_df.iloc[-1]["Faturamento"]
    growth = ((last_revenue / first_revenue) - 1) * 100 if first_revenue > 0 else 0.0

    elements.append(PageBreak())
    elements.append(Paragraph("Evolução Mensal", styles["Heading1"]))
    elements.append(
        Paragraph(
            """
                Acompanhamento da receita ao longo do tempo.
                Permite identificar tendências de crescimento,
                sazonalidade e possíveis oscilações de mercado.
                """,
            styles["BodyText"],
        )
    )
    elements.append(Spacer(1, 15))
    elements.append(Paragraph(f"""O faturamento variou {growth:.1f}% entre o primeiro e o último período disponível.""", styles["BodyText"]))
    elements.append(Spacer(1, 15))
    if monthly_png is not None:
        elements.append(Image(str(monthly_png), width=GRAPH_WIDTH, height=GRAPH_HEIGHT))


def _append_products_section(elements: list[Any], styles: Any, product_summary_df: Any) -> None:
    """Adiciona seção de produtos com gráfico e insight de concentração."""
    if product_summary_df.empty:
        return

    top_product = product_summary_df.iloc[0]
    top_products_png = IMAGES_DIR / "top_produtos.png"

    fig = px.bar(
        product_summary_df.head(10),
        x="Código do Produto",
        y="Margem de contribuição",
        color="Margem de contribuição",
        color_continuous_scale="Greens",
        title="Top Produtos por Margem",
    )
    fig.write_image(str(top_products_png), width=1200, height=700)

    top10_revenue_share = (
        product_summary_df.head(10)["Faturamento"].sum() / product_summary_df["Faturamento"].sum() * 100
        if product_summary_df["Faturamento"].sum() > 0
        else 0.0
    )

    elements.append(PageBreak())
    elements.append(Paragraph("Top 10 Produtos", styles["Heading1"]))
    elements.append(
        Paragraph(
            """
            Os produtos abaixo representam a maior
            contribuição financeira do período analisado.
            O acompanhamento contínuo destes itens
            é estratégico para manutenção da rentabilidade.
            """,
            styles["BodyText"],
        )
    )
    elements.append(Spacer(1, 15))
    elements.append(Image(str(top_products_png), width=GRAPH_WIDTH, height=GRAPH_HEIGHT))
    elements.append(Spacer(1, 15))
    elements.append(
        Paragraph(
            f"""
            <b>Insight Executivo</b><br/><br/>
            • O produto {top_product['Código do Produto']}
            apresentou a maior contribuição financeira do período.<br/>
            • Os 10 produtos mais relevantes representam
            <b>{top10_revenue_share:.1f}%</b> do faturamento analisado.
            Isso demonstra o grau de concentração da receita no portfólio atual.<br/>
            """,
            styles["BodyText"],
        )
    )


def _append_customers_section(elements: list[Any], styles: Any, customer_summary_df: Any) -> None:
    """Adiciona seção de clientes com gráfico e tabela."""
    filtered_customers_df = customer_summary_df[customer_summary_df["Pedidos"] > 3].copy()
    customer_png = IMAGES_DIR / "clientes_top10.png"

    if not filtered_customers_df.empty:
        fig_customer = px.bar(
            filtered_customers_df.head(10),
            x="Cliente_Chave",
            y="Pedidos",
            color="Pedidos",
            color_continuous_scale="Blues",
            title="Top 10 Clientes por Quantidade de Pedidos",
        )
        fig_customer.update_layout(xaxis_title="Cliente", yaxis_title="Pedidos", margin=dict(l=40, r=20, t=60, b=180))
        fig_customer.write_image(str(customer_png), width=1200, height=700)

    elements.append(PageBreak())
    elements.append(Paragraph("Clientes", styles["Heading1"]))
    elements.append(
        Paragraph(
            """
            Análise dos clientes com maior recorrência
            de compras no período selecionado.
            Apenas clientes com mais de 3 pedidos
            foram considerados nesta análise.
            """,
            styles["BodyText"],
        )
    )
    elements.append(Spacer(1, 15))

    if not filtered_customers_df.empty:
        elements.append(Image(str(customer_png), width=GRAPH_WIDTH, height=GRAPH_HEIGHT))
        elements.append(Spacer(1, 15))

    table_rows = [["Cliente", "Pedidos", "Receita", "Ticket Médio"]]
    for _, row in filtered_customers_df.head(20).iterrows():
        table_rows.append([str(row["Cliente_Chave"]), int(row["Pedidos"]), brl(row["Receita_Total"]), brl(row["Ticket Médio"])])

    customer_table = Table(table_rows, colWidths=[170, 70, 120, 120])
    customer_table.setStyle(
        TableStyle(
            [
                ("BACKGROUND", (0, 0), (-1, 0), colors.HexColor("#1E3A8A")),
                ("TEXTCOLOR", (0, 0), (-1, 0), colors.white),
                ("FONTNAME", (0, 0), (-1, 0), "Helvetica-Bold"),
                ("FONTSIZE", (0, 0), (-1, -1), 8),
                ("LEADING", (0, 0), (-1, -1), 10),
                ("TOPPADDING", (0, 0), (-1, -1), 4),
                ("BOTTOMPADDING", (0, 0), (-1, -1), 4),
                ("BOX", (0, 0), (-1, -1), 1, colors.HexColor("#1E3A8A")),
                ("INNERGRID", (0, 0), (-1, -1), 0.5, colors.HexColor("#CBD5E1")),
                ("ROWBACKGROUNDS", (0, 1), (-1, -1), [colors.HexColor("#F8FAFC"), colors.white]),
            ]
        )
    )
    elements.append(customer_table)


def _append_representatives_section(elements: list[Any], styles: Any, representative_df: Any) -> None:
    """Adiciona seção de representantes com gráfico e tabela."""
    if representative_df.empty:
        return

    top_rep = representative_df.iloc[0]
    rep_png = IMAGES_DIR / "representantes.png"

    fig_rep = px.bar(
        representative_df.head(10),
        x="Receita_Total",
        y="Representante",
        orientation="h",
        color="Receita_Total",
        color_continuous_scale="Blues",
        title="Ranking de Representantes",
    )
    fig_rep.write_image(str(rep_png), width=1600, height=900)

    elements.append(PageBreak())
    elements.append(Paragraph("Representantes", styles["Heading1"]))
    elements.append(
        Paragraph(
            f"""
                <b>Desempenho Comercial</b><br/><br/>
                {top_rep['Representante']} lidera o faturamento com
                {brl(top_rep['Receita_Total'])}, representando
                {top_rep['Participacao (%)']:.1f}% da receita total.
                """,
            styles["BodyText"],
        )
    )
    elements.append(Spacer(1, 30))
    elements.append(Image(str(rep_png), width=GRAPH_WIDTH, height=GRAPH_HEIGHT))
    elements.append(Spacer(1, 15))

    table_rows = [["Representante", "Receita", "Clientes", "% Participação"]]
    for _, row in representative_df.iterrows():
        table_rows.append([str(row["Representante"]), brl(row["Receita_Total"]), str(row["Clientes_Unicos"]), f"{row['Participacao (%)']:.1f}%"])

    rep_table = Table(table_rows, colWidths=[180, 120, 80, 80])
    rep_table.setStyle(TableStyle([("BACKGROUND", (0, 0), (-1, 0), colors.lightgrey), ("GRID", (0, 0), (-1, -1), 1, colors.black)]))
    elements.append(rep_table)


def _append_conclusions_section(elements: list[Any], styles: Any, product_summary_df: Any, financial: dict[str, Any]) -> None:
    """Adiciona seção de conclusões, riscos e oportunidades."""
    if product_summary_df.empty:
        return

    top5_concentration = (
        product_summary_df.head(5)["Faturamento"].sum() / product_summary_df["Faturamento"].sum() * 100
        if product_summary_df["Faturamento"].sum() > 0
        else 0.0
    )

    if top5_concentration >= 70:
        portfolio_risk = f"Existe um nível elevado de concentração de receita. Os cinco principais produtos representam {top5_concentration:.1f}% do faturamento total analisado."
    elif top5_concentration >= 50:
        portfolio_risk = f"Existe uma concentração moderada de receita. Os cinco principais produtos representam {top5_concentration:.1f}% do faturamento."
    else:
        portfolio_risk = f"O faturamento apresenta boa distribuição entre os produtos comercializados. Os cinco principais produtos representam {top5_concentration:.1f}% do faturamento."

    elements.append(PageBreak())
    elements.append(Paragraph("Conclusões Executivas", styles["Heading1"]))

    insights = [
        f"<b>Produto mais rentável:</b> {financial['top_product']}",
        f"<b>Representante com maior resultado:</b> {financial['top_representative']}",
        f"<b>Cliente com maior contribuição:</b> {financial['top_customer']}",
    ]
    for item in insights:
        elements.append(Paragraph(f"• {item}", styles["BodyText"]))

    elements.append(Spacer(1, 15))
    elements.append(Paragraph("Recomendações:", styles["Heading2"]))
    elements.append(
        Paragraph(
            """
            • Monitorar produtos líderes.<br/>
            • Expandir regiões com maior ticket médio.<br/>
            • Priorizar retenção dos clientes mais rentáveis.<br/>
            """,
            styles["BodyText"],
        )
    )

    elements.append(Spacer(1, 35))
    elements.append(Paragraph("Riscos e Oportunidades", styles["Heading1"]))
    elements.append(
        Paragraph(
            f"""
            <b>Principais Riscos</b>
            <br/><br/>
            • {portfolio_risk}<br/>
            • Dependência dos principais representantes comerciais para geração de receita.<br/>
            • Possível concentração geográfica em regiões específicas do país.<br/>
            """,
            styles["BodyText"],
        )
    )
    elements.append(Spacer(1, 20))
    elements.append(
        Paragraph(
            """
            <b>Principais Oportunidades</b>
            <br/><br/>
            • Expansão comercial em estados com menor participação.<br/>
            • Aumento de vendas em produtos Classe B.<br/>
            • Ampliação da base de clientes recorrentes.<br/><br/>
            """,
            styles["BodyText"],
        )
    )


def _append_geography_section(elements: list[Any], styles: Any, state_ticket_df: Any, state_revenue_df: Any, state_geo_df: Any) -> None:
    """Adiciona seção de geografia com gráficos e tabela."""
    if state_ticket_df.empty:
        return

    if state_revenue_df.empty:
        return

    top_state = state_ticket_df.iloc[0]

    state_revenue_png = IMAGES_DIR / "receita_estado.png"
    fig = px.bar(
        state_revenue_df.head(10),
        x="UF",
        y="Valor_Total",
        color="Valor_Total",
        color_continuous_scale="Blues",
        title="Receita por Estado",
    )
    fig.write_image(str(state_revenue_png), width=1200, height=700)

    map_png = None
    if not state_geo_df.empty:
        fig_map = px.scatter_geo(
            state_geo_df,
            lat="Latitude",
            lon="Longitude",
            size="Valor_Total",
            size_max=60,
            color="Valor_Total",
            hover_name="UF",
            scope="south america",
            projection="mercator",
            color_continuous_scale="Blues",
            title="Vendas por região",
        )
        fig_map.update_geos(
            fitbounds="locations",
            showcountries=True,
            showcoastlines=True,
            showland=True,
            landcolor="#F8FAFC",
            lataxis_range=[-35, 6],
            lonaxis_range=[-75, -30],
        )
        fig_map.update_traces(marker=dict(opacity=0.85, line=dict(width=1, color="black")))
        map_png = IMAGES_DIR / "mapa_brasil.png"
        fig_map.write_image(str(map_png), width=1600, height=900)

    elements.append(PageBreak())
    elements.append(Paragraph("Geografia de Vendas", styles["Heading1"]))
    elements.append(Spacer(1, 10))
    elements.append(
        Paragraph(
            """
            Para garantir consistência estatística,
            estados com menos de 3 pedidos foram
            excluídos dos cálculos de ticket médio.
            """,
            styles["BodyText"],
        )
    )
    elements.append(Spacer(1, 10))
    elements.append(Image(str(state_revenue_png), width=GRAPH_WIDTH, height=GRAPH_HEIGHT))
    elements.append(Spacer(1, 15))

    if map_png is not None:
        elements.append(Image(str(map_png), width=GRAPH_WIDTH, height=GRAPH_HEIGHT))

    elements.append(Spacer(1, 15))

    geo_rows = [["UF", "Pedidos", "Clientes", "Receita", "Ticket Médio"]]
    for _, row in state_ticket_df.iterrows():
        geo_rows.append([row["UF"], int(row["Pedidos"]), int(row["Clientes"]), brl(row["Valor_Total"]), brl(row["Ticket Médio"])])

    geo_table = Table(geo_rows, colWidths=[50, 60, 70, 140, 140])
    geo_table.setStyle(TableStyle([("BACKGROUND", (0, 0), (-1, 0), colors.lightgrey), ("GRID", (0, 0), (-1, -1), 1, colors.black)]))

    elements.append(
        Paragraph(
            f"""
            <b>Destaque Geográfico</b><br/><br/>
            O estado de {top_state['UF']} concentra
            a maior receita do período,
            totalizando {brl(top_state['Valor_Total'])}.
            O ticket médio da região é de
            {brl(top_state['Ticket Médio'])}.
            """,
            styles["BodyText"],
        )
    )
    elements.append(Spacer(1, 15))
    elements.append(geo_table)


def generate_executive_pdf(
    analytics: Any,
    filtered_df: Any,
    output_path: str = "relatorio_gerencial.pdf",
    profitability_df: Any = None,
    core_kpis: dict[str, Any] | None = None,
    financial_kpis: dict[str, Any] | None = None,
    monthly_profitability_df: Any = None,
    product_profitability_df: Any = None,
    representative_performance_df: Any = None,
    state_ticket_df: Any = None,
) -> Path:
    """Gera relatório executivo em PDF usando datasets já calculados quando fornecidos."""
    doc = SimpleDocTemplate(output_path, pagesize=A4)
    styles = _build_styles()
    elements: list = []

    profitability_df = profitability_df if profitability_df is not None else analytics.build_profitability_dataset(filtered_df)
    financial = financial_kpis if financial_kpis is not None else analytics.calculate_financial_kpis(profitability_df)
    monthly_df = monthly_profitability_df if monthly_profitability_df is not None else analytics.get_monthly_profitability(profitability_df)
    kpis = core_kpis if core_kpis is not None else analytics.calculate_kpis(filtered_df)
    product_summary_df = product_profitability_df if product_profitability_df is not None else analytics.get_profitability_by_product(profitability_df)
    customer_summary_df = analytics.get_customer_summary(filtered_df)
    representative_df = representative_performance_df if representative_performance_df is not None else analytics.get_representative_performance(filtered_df)
    geo_ticket_df = state_ticket_df if state_ticket_df is not None else analytics.get_state_ticket_average(filtered_df)
    geo_revenue_df = analytics.get_state_revenue(filtered_df)
    geo_map_df = analytics.get_state_geo_coordinates(filtered_df)

    _append_cover(elements, styles)
    monthly_png = _build_monthly_chart(monthly_df)
    _append_executive_summary(elements, styles, financial, kpis)
    _append_monthly_section(elements, styles, monthly_df, monthly_png)
    _append_products_section(elements, styles, product_summary_df)
    _append_customers_section(elements, styles, customer_summary_df)
    _append_representatives_section(elements, styles, representative_df)
    _append_conclusions_section(elements, styles, product_summary_df, financial)
    _append_geography_section(elements, styles, geo_ticket_df, geo_revenue_df, geo_map_df)

    doc.build(elements, onFirstPage=add_cover_footer, onLaterPages=add_page_number, canvasmaker=NumberedCanvas)
    return Path(output_path)
