'''
    Gera um relatório PDF executivo com base em dados de vendas.

'''
import plotly.express as px
import plotly.graph_objects as go
from PIL import Image as PILImage
from plotly.subplots import make_subplots
from pathlib import Path
from datetime import datetime
from reportlab.pdfgen import canvas
from reportlab.lib import colors
from reportlab.lib.pagesizes import A4
from reportlab.platypus import (
    SimpleDocTemplate,
    Paragraph,
    Spacer,
    PageBreak,
    Table,
    TableStyle,
    Image
)
from reportlab.lib.styles import getSampleStyleSheet
from analytics.processing import SalesAnalytics


GRAPH_WIDTH = 520
GRAPH_HEIGHT = 320

images_dir = (
    Path(__file__).resolve().parent.parent
    / "utils"
    / "pdf_assets"
)

logo_path = images_dir / "logo.png"


def brl(valor):
    return f"R$ {valor:,.2f}"


def add_page_number(canvas, doc):
    canvas.saveState()
    if doc.page > 1:

        # =========================
        # Moldura externa
        # =========================
        '''canvas.setStrokeColor(
            colors.HexColor("#1E3A8A")
        )
        canvas.setLineWidth(2)
        canvas.rect(
            20,
            20,
            555,
            800,
            stroke=1,
            fill=0
        )'''

        # =========================
        # Moldura interna
        # =========================
        '''canvas.setStrokeColor(
            colors.HexColor("#CBD5E1")
        )
        canvas.setLineWidth(0.8)
        canvas.rect(
            30,
            30,
            535,
            780,
            stroke=1,
            fill=0
        )'''

        # =========================
        # Cabeçalho
        # =========================
        canvas.setStrokeColor(colors.HexColor("#1E3A8A"))
        canvas.line(40,785,555,785)
        canvas.setFont("Helvetica-Bold",11)
        canvas.drawString(45,795,"All Drive Transmission")

        # =========================
        # Rodapé
        # =========================
        canvas.line(40,45,555,45)
        canvas.setFont("Helvetica",8)
        '''canvas.drawString(
            45,
            30,
            f"Página {doc.page}"
        )'''
        canvas.drawRightString(
            545,
            30,
            "Uso Interno - Diretoria"
        )

    canvas.restoreState()

class NumberedCanvas(canvas.Canvas):
    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self._saved_page_states = []

    def showPage(self):
        self._saved_page_states.append(
            dict(self.__dict__)
        )
        self._startPage()

    def save(self):
        total_pages = len(
            self._saved_page_states
        )
        for state in self._saved_page_states:
            self.__dict__.update(state)
            self.draw_page_number(
                total_pages
            )
            super().showPage()
        super().save()

    def draw_page_number(self,total_pages):
        if self._pageNumber > 1:
            self.setFont("Helvetica",8)
            self.drawString(
                45,
                30,
                f"Página {self._pageNumber} de {total_pages}"
            )


def add_cover_footer(canvas, doc):
    canvas.saveState()
    canvas.setFont("Helvetica",10)

    # Centralizado horizontalmente
    canvas.drawCentredString(
        A4[0] / 2,
        30,
        "Uso Interno - Diretoria"
    )

    canvas.restoreState()


def generate_executive_pdf(analytics, filtered_df, output_path="relatorio_gerencial.pdf"):
    doc = SimpleDocTemplate(
        output_path,
        pagesize=A4
    )

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


    elements = []

    # ==================================================
    # CAPA
    # ==================================================
    '''if logo_path.exists():
        elements.append(Spacer(1, 80))
        elements.append(
            Image(
                str(logo_path),
                width=160,
                height=160,
            )
        )'''
    img = PILImage.open(logo_path)
    img_width, img_height = img.size
    desired_width = 220
    desired_height = (
        desired_width * img_height
    ) / img_width
    elements.append(
        Image(
            str(logo_path),
            width=desired_width,
            height=desired_height
        )
    )

    elements.append(Spacer(1, 40))

    elements.append(
        Paragraph(
            "Painel Gerencial Comercial",
            styles["Heading2"]
        )
    )

    elements.append(Spacer(1, 120))

    elements.append(
        Paragraph(
            "RELATÓRIO EXECUTIVO DE VENDAS",
            styles["Title"]
        )
    )

    elements.append(Spacer(1, 100))

    elements.append(
        Paragraph(
            f"Gerado em: {datetime.now().strftime('%d/%m/%Y %H:%M')}",
            styles["Heading3"]
        )
    )

    elements.append(PageBreak())

    # ==================================================
    # SUMÁRIO EXECUTIVO
    # ==================================================
    profitability_df = analytics.build_profitability_dataset(filtered_df)
    financial = analytics.calculate_financial_kpis(profitability_df)
    monthly_df = analytics.get_monthly_profitability(profitability_df)

    show_monthly_section = (
        not monthly_df.empty
        and len(monthly_df) > 1
    )

    if not monthly_df.empty:
        fig_monthly = make_subplots(
            specs=[[{"secondary_y": True}]]
        )

        fig_monthly.add_trace(
            go.Bar(
                x=monthly_df["Mês"],
                y=monthly_df["Faturamento"],
                name="Faturamento",
                marker_color="#1E40AF"
            ),
            secondary_y=False
        )

        fig_monthly.add_trace(
            go.Scatter(
                x=monthly_df["Mês"],
                y=monthly_df["Margem de contribuição"],
                name="Margem Contribuição",
                line=dict(
                    color="#16A34A",
                    width=4
                )
            ),
            secondary_y=False
        )

        fig_monthly.add_trace(
            go.Scatter(
                x=monthly_df["Mês"],
                y=monthly_df["Margem Bruta (%)"],
                name="Margem %",
                line=dict(
                    color="#D97706",
                    width=4
                )
            ),
            secondary_y=True
        )

        fig_monthly.update_layout(
            title="Evolução Financeira",
            height=600,
            template="plotly_white",
            legend=dict(
                orientation="h",
                y=1.1
            )
        )

        fig_monthly.update_yaxes(
            title_text="R$",
            secondary_y=False
        )

        fig_monthly.update_yaxes(
            title_text="Margem (%)",
            secondary_y=True
        )

        monthly_png = (
            images_dir /
            "evolucao_mensal.png"
        )

        fig_monthly.write_image(
            str(monthly_png),
            width=1600,
            height=900
        )

    ultimo_faturamento = monthly_df.iloc[-1]["Faturamento"]
    primeiro_faturamento = monthly_df.iloc[0]["Faturamento"]
    if primeiro_faturamento > 0:
        crescimento = (
            (
                ultimo_faturamento
                /
                primeiro_faturamento
            ) - 1
        ) * 100
    else:
        crescimento = 0

    elements.append(Spacer(1, 20))

    texto = f"""
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
    kpis = SalesAnalytics.calculate_kpis(filtered_df)

    resumo = [
        ["Indicador", "Valor"],
        ["Faturamento Total", brl(financial["revenue_total"])],
        ["Margem de Contribuição", brl(financial["gross_profit_total"])],
        ["Margem Média", f'{financial["gross_margin_avg"]:.2f}%'],
        ["Clientes Ativos", f"{kpis['active_customers']:,}"],
        ["Pedidos por Cliente", f"{kpis['orders_per_customer']:.2f}"],
        ["Total de Pedidos", f'{kpis["total_orders"]:,}'],
        ["Produtos únicos", f'{kpis["unique_products"]:,}'],
        ["Taxa NF", f'{kpis["nf_emission_rate"]:.2f}%'],
        ["Lucro Operacional Estimado", brl(financial["estimated_operating_profit_value"])],
        ["Margem Operacional",(f"{financial['estimated_operating_profit_pct']:.2f}%")],
    ]

    elements.append(
        Paragraph(
            "Sumário Executivo",
            styles["Heading1"]
        )
    )

    elements.append(
        Paragraph(
            texto,
            styles["BodyText"]
        )
    )

    elements.append(Spacer(1, 20))

    table = Table(resumo, colWidths=[220, 180])

    table.setStyle(
        TableStyle([
            ("BACKGROUND",(0,0),(-1,0),colors.HexColor("#1E3A8A")),
            ("TEXTCOLOR",(0,0),(-1,0),colors.white),
            ("FONTNAME",(0,0),(-1,0),"Helvetica-Bold"),
            ("BOX",(0,0),(-1,-1),1.5,colors.HexColor("#1E3A8A")),
            ("INNERGRID",(0,0),(-1,-1),0.5,colors.HexColor("#CBD5E1")),
            ("ROWBACKGROUNDS",
            (0,1),
            (-1,-1),
            [
                colors.HexColor("#F8FAFC"),
                colors.white
            ]),

            ("TOPPADDING",(0,0),(-1,-1),10),
            ("BOTTOMPADDING",(0,0),(-1,-1),10),
        ])
    )

    elements.append(table)

    # ==================================================
    # EVOLUÇÃO MENSAL
    # ==================================================
    if show_monthly_section:
        elements.append(PageBreak())
        elements.append(
            Paragraph(
                "Evolução Mensal",
                styles["Heading1"]
            )
        )

        elements.append(
            Paragraph(
                """
                Acompanhamento da receita ao longo do tempo.
                Permite identificar tendências de crescimento,
                sazonalidade e possíveis oscilações de mercado.
                """,
                styles["BodyText"]
            )
        )

        elements.append(Spacer(1, 15))

        elements.append(
            Paragraph(
                f"""
                O faturamento variou
                {crescimento:.1f}%
                entre o primeiro e o último período disponível.
                """,
                styles["BodyText"]
            )
        )

        elements.append(Spacer(1, 15))

        if not monthly_df.empty:
            elements.append(
                Image(
                    str(monthly_png),
                    width=GRAPH_WIDTH,
                    height=GRAPH_HEIGHT
                )
            )


    # ==================================================
    # PRODUTOS
    # ==================================================
    elements.append(PageBreak())
    product_summary = analytics.get_profitability_by_product(profitability_df)
    top_produto = product_summary.iloc[0]

    fig = px.bar(
        product_summary.head(10),
        x="Código do Produto",
        y="Margem de contribuição",
        color="Margem de contribuição",
        color_continuous_scale="Greens",
        title="Top Produtos por Margem"
    )

    produto_png = (
        images_dir /
        "top_produtos.png"
    )

    fig.write_image(
        str(produto_png),
        width=1200,
        height=700
    )

    elements.append(
        Paragraph(
            "Top 10 Produtos",
            styles["Heading1"]
        )
    )

    elements.append(
        Paragraph(
            """
            Os produtos abaixo representam a maior
            contribuição financeira do período analisado.
            O acompanhamento contínuo destes itens
            é estratégico para manutenção da rentabilidade.
            """,
            styles["BodyText"]
        )
    )

    elements.append(Spacer(1, 15))

    elements.append(
        Image(
            str(produto_png),
            width=GRAPH_WIDTH,
            height=GRAPH_HEIGHT
        )
    )


    '''dados = [["Produto", "Receita", "Margem"]]
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
    elements.append(tabela)'''

    participacao_top10 = (
        product_summary.head(10)["Faturamento"].sum()
        /
        product_summary["Faturamento"].sum()
        * 100
    )
    elements.append(Spacer(1, 15))
    elements.append(
        Paragraph(
            f"""
            <b>Insight Executivo</b><br/><br/>
            • O produto
            {top_produto['Código do Produto']}
            apresentou a maior contribuição financeira
            do período.<br/>
            • Os 10 produtos mais relevantes representam
            <b>{participacao_top10:.1f}%</b>
            do faturamento analisado.
            Isso demonstra o grau de concentração
            da receita no portfólio atual.<br/>
            """,
            styles["BodyText"]
        )
    )


    # ==================================================
    # CLIENTES
    # ==================================================
    elements.append(PageBreak())
    customer_summary = (SalesAnalytics.get_customer_summary(filtered_df))
    customer_summary = customer_summary[customer_summary["Pedidos"] > 3].copy()

    customer_png = (
        images_dir /
        "clientes_top10.png"
    )
    if not customer_summary.empty:
        fig_customer = px.bar(
            customer_summary.head(10),
            x="Cliente_Chave",
            y="Pedidos",
            #orientation="h",
            color="Pedidos",
            color_continuous_scale="Blues",
            title="Top 10 Clientes por Quantidade de Pedidos"
        )
        fig_customer.update_layout(
            xaxis_title="Cliente",
            yaxis_title="Pedidos",
            margin=dict(
                l=40,
                r=20,
                t=60,
                b=180
            )
        )
        fig_customer.write_image(
            str(customer_png),
            width=1200,
            height=700
        )

    elements.append(
        Paragraph(
            "Clientes",
            styles["Heading1"]
        )
    )

    elements.append(
        Paragraph(
            """
            Análise dos clientes com maior recorrência
            de compras no período selecionado.
            Apenas clientes com mais de 3 pedidos
            foram considerados nesta análise.
            """,
            styles["BodyText"]
        )
    )

    elements.append(Spacer(1, 15))

    if not customer_summary.empty:
        elements.append(
            Image(
                str(customer_png),
                width=GRAPH_WIDTH,
                height=GRAPH_HEIGHT
            )
        )
        elements.append(Spacer(1, 15))
    
    dados = [[
        "Cliente",
        "Pedidos",
        "Receita",
        "Ticket Médio"
    ]]

    for _, row in customer_summary.head(20).iterrows():
        dados.append([
            str(row["Cliente_Chave"]),
            int(row["Pedidos"]),
            brl(row["Receita_Total"]),
            brl(row["Ticket Médio"])
        ])

    tabela_clientes = Table(
        dados,
        colWidths=[170, 70, 120, 120]
    )

    tabela_clientes.setStyle(
        TableStyle([

            ("BACKGROUND", (0, 0), (-1, 0),
            colors.HexColor("#1E3A8A")),

            ("TEXTCOLOR", (0, 0), (-1, 0),
            colors.white),

            ("FONTNAME", (0, 0), (-1, 0),
            "Helvetica-Bold"),

            ("FONTSIZE", (0, 0), (-1, -1), 8),

            ("LEADING", (0, 0), (-1, -1), 10),

            ("TOPPADDING", (0, 0), (-1, -1), 4),

            ("BOTTOMPADDING", (0, 0), (-1, -1), 4),

            ("BOX", (0, 0), (-1, -1), 1, colors.HexColor("#1E3A8A")),

            ("INNERGRID", (0, 0), (-1, -1), 0.5, colors.HexColor("#CBD5E1")),

            ("ROWBACKGROUNDS", (0, 1), (-1, -1),
            [
                colors.HexColor("#F8FAFC"),
                colors.white
            ])
        ])
    )

    elements.append(tabela_clientes)


    # ==================================================
    # REPRESENTANTES
    # ==================================================
    elements.append(PageBreak())
    rep = SalesAnalytics.get_representative_performance(
        filtered_df
    )

    top_rep = rep.iloc[0]

    rep_png = (
        images_dir /
        "representantes.png"
    )

    fig_rep = px.bar(
        rep.head(10),
        x="Receita_Total",
        y="Representante",
        orientation="h",
        color="Receita_Total",
        color_continuous_scale="Blues",
        title="Ranking de Representantes"
    )

    fig_rep.write_image(
        str(rep_png),
        width=1600,
        height=900
    )

    elements.append(
        Paragraph(
            "Representantes",
            styles["Heading1"]
        )
    )

    elements.append(
            Paragraph(
                f"""
                <b>Desempenho Comercial</b><br/><br/>
                {top_rep['Representante']}
                lidera o faturamento com
                {brl(top_rep['Receita_Total'])},
                representando
                {top_rep['Participacao (%)']:.1f}%
                da receita total.
                """,
                styles["BodyText"]
            )
        )

    elements.append(Spacer(1, 30))

    elements.append(
        Image(
            str(rep_png),
            width=GRAPH_WIDTH,
            height=GRAPH_HEIGHT
        )
    )

    elements.append(Spacer(1, 15))

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


    # ==================================================
    # CONCLUSÕES EXECUTIVAS
    # ==================================================
    elements.append(PageBreak())
    top5_concentracao = (
        product_summary
        .head(5)["Faturamento"]
        .sum()
        /
        product_summary["Faturamento"].sum()
        * 100
    )

    if top5_concentracao >= 70:
        risco_portfolio = (
            f"""
            Existe um nível elevado de concentração
            de receita.

            Os cinco principais produtos representam
            {top5_concentracao:.1f}% do faturamento
            total analisado.

            A companhia apresenta forte dependência
            desse grupo de produtos.
            """
        )
    elif top5_concentracao >= 50:
        risco_portfolio = (
            f"""
            Existe uma concentração moderada de receita.

            Os cinco principais produtos representam
            {top5_concentracao:.1f}% do faturamento.

            Recomenda-se monitorar o comportamento
            desses produtos para evitar aumento da
            dependência comercial.
            """
        )
    else:
        risco_portfolio = (
            f"""
            O faturamento apresenta boa distribuição
            entre os produtos comercializados.

            Os cinco principais produtos representam
            {top5_concentracao:.1f}% do faturamento.

            O risco de concentração atualmente é baixo.
            """
        )
    
    elements.append(
            Paragraph(
                "Conclusões Executivas",
                styles["Heading1"]
            )
        )

    insights = [
        f"<b>Produto mais rentável:</b> {financial['top_product']}",
        f"<b>Representante com maior resultado:</b> {financial['top_representative']}",
        f"<b>Cliente com maior contribuição:</b> {financial['top_customer']}",
    ]

    for item in insights:
        elements.append(
            Paragraph(
                f"• {item}",
                styles["BodyText"]
            )
        )

    elements.append(Spacer(1, 15))

    elements.append(
        Paragraph(
            "Recomendações:",
            styles["Heading2"]
        )
    )

    elements.append(
        Paragraph(
            """
            • Monitorar produtos líderes.<br/>
            • Expandir regiões com maior ticket médio.<br/>
            • Priorizar retenção dos clientes mais rentáveis.<br/>
            """,
            styles["BodyText"]
        )
    )

    elements.append(Spacer(1, 35))

    elements.append(
        Paragraph(
            "Riscos e Oportunidades",
            styles["Heading1"]
        )
    )

    elements.append(
        Paragraph(
            f"""
            <b>Principais Riscos</b>
            <br/><br/>
            • {risco_portfolio}
            <br/>
            • Dependência dos principais representantes comerciais para geração de receita.<br/>
            • Possível concentração geográfica em regiões específicas do país.<br/>
            """,
            styles["BodyText"]
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
            styles["BodyText"]
        )
    )


    # ==================================================
    # GEOGRAFIA
    # ==================================================
    elements.append(PageBreak())
    geo = SalesAnalytics.get_state_ticket_average(filtered_df)
    top_estado = geo.iloc[0]
    state_revenue = SalesAnalytics.get_state_revenue(filtered_df)
    state_geo = SalesAnalytics.get_state_geo_coordinates(filtered_df)

    if not state_revenue.empty:
        fig = px.bar(
            state_revenue.head(10),
            x="UF",
            y="Valor_Total",
            color="Valor_Total",
            color_continuous_scale="Blues",
            title="Receita por Estado"
        )

        receita_estado_png = (
            images_dir /
            "receita_estado.png"
        )

        fig.write_image(
            str(receita_estado_png),
            width=1200,
            height=700
        )

    if not state_geo.empty:
        fig_map = px.scatter_geo(
            state_geo,
            lat="Latitude",
            lon="Longitude",
            size="Valor_Total",
            size_max=60,
            color="Valor_Total",
            hover_name="UF",
            scope="south america",
            projection="mercator",  # natural earth, mercator
            color_continuous_scale="Blues",
            title="Vendas por região"
        )
        fig_map.update_geos(
            fitbounds="locations",
            showcountries=True,
            showcoastlines=True,
            showland=True,
            landcolor="#F8FAFC",
            lataxis_range=[-35, 6],
            lonaxis_range=[-75, -30]
        )
        fig_map.update_traces(
            marker=dict(
                opacity=0.85,
                line=dict(
                    width=1,
                    color="black"
                )
            )
        )

        mapa_png = (
            images_dir /
            "mapa_brasil.png"
        )

        fig_map.write_image(
            str(mapa_png),
            width=1600,
            height=900
        )

    elements.append(
        Paragraph(
            "Geografia de Vendas",
            styles["Heading1"]
        )
    )

    elements.append(Spacer(1, 10))

    elements.append(
        Paragraph(
            """
            Para garantir consistência estatística,
            estados com menos de 3 pedidos foram
            excluídos dos cálculos de ticket médio.
            """,
            styles["BodyText"]
        )
    )

    elements.append(Spacer(1, 10))

    elements.append(
        Image(
            str(receita_estado_png),
            width=GRAPH_WIDTH,
            height=GRAPH_HEIGHT
        )
    )

    elements.append(Spacer(1, 15))

    if not state_geo.empty:
        elements.append(
            Image(
                str(mapa_png),
                width=GRAPH_WIDTH,
                height=GRAPH_HEIGHT
            )
        )

    elements.append(Spacer(1, 15))

    dados = [[
        "UF",
        "Pedidos",
        "Clientes",
        "Receita",
        "Ticket Médio"
    ]]

    for _, row in geo.iterrows():
        dados.append([
            row["UF"],
            int(row["Pedidos"]),
            int(row["Clientes"]),
            brl(row["Valor_Total"]),
            brl(row["Ticket Médio"])
        ])

    tabela = Table(
        dados,
        colWidths=[50,60,70,140,140]
    )

    tabela.setStyle(
        TableStyle([
            ("BACKGROUND",(0,0),(-1,0),colors.lightgrey),
            ("GRID",(0,0),(-1,-1),1,colors.black),
        ])
    )

    elements.append(
        Paragraph(
            f"""
            <b>Destaque Geográfico</b><br/><br/>

            O estado de {top_estado['UF']} concentra
            a maior receita do período,
            totalizando {brl(top_estado['Valor_Total'])}.

            O ticket médio da região é de
            {brl(top_estado['Ticket Médio'])}.
            """,
            styles["BodyText"]
        )
    )

    elements.append(Spacer(1, 15))

    elements.append(tabela)


    # ==================================================
    # IMPRESSÃO DO RELATÓRIO
    # ==================================================
    doc.build(
        elements,
        onFirstPage=add_cover_footer,
        onLaterPages=add_page_number,
        canvasmaker=NumberedCanvas
    )

    return Path(output_path)
