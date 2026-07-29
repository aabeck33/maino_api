# Maino API - Documentacao Tecnica Completa

## 1. Visao Geral

Este projeto consolida vendas de multiplas fontes Excel, enriquece dados cadastrais de clientes e disponibiliza um dashboard executivo em Streamlit com analises operacionais, fiscais, comerciais, geograficas e de rentabilidade.

Fluxo macro:

1. Extracao e consolidacao de dados em [src/export_orders.py](src/export_orders.py)
2. Gravacao da base final em [work/pedidos_confirmados.xlsx](work/pedidos_confirmados.xlsx)
3. Leitura dessa base pelo dashboard em [src/app.py](src/app.py)
4. Aplicacao de filtros globais
5. Calculo de KPIs por dominio na camada [src/analytics/kpis](src/analytics/kpis)
6. Renderizacao das abas em [src/dashboard/views_sections](src/dashboard/views_sections)

## 2. Estrutura Atual Do Projeto

```text
Maino_API/
|-- CALC.md
|-- README.md
|-- requirements.txt
|-- src/
|   |-- app.py
|   |-- export_orders.py
|   |-- export_ncms.py
|   |-- analytics/
|   |   |-- processing.py
|   |   |-- kpis/
|   |       |-- sales_kpis.py
|   |       |-- customer_kpis.py
|   |       |-- representative_kpis.py
|   |       |-- geography_kpis.py
|   |       |-- profitability_kpis.py
|   |       |-- shared.py
|   |-- config/
|   |   |-- settings.py
|   |-- dashboard/
|   |   |-- components.py
|   |   |-- views_sections/
|   |       |-- overview.py
|   |       |-- profitability.py
|   |       |-- representatives.py
|   |       |-- customers.py
|   |       |-- products.py
|   |       |-- geography.py
|   |       |-- fiscal.py
|   |       |-- insights.py
|   |-- repositories/
|   |   |-- sales_repository.py
|   |   |-- product_repository.py
|   |   |-- customer_repository.py
|   |   |-- normalization.py
|   |-- services/
|   |   |-- dashboard_service.py
|   |-- utils/
|       |-- geo.py
|       |-- logger.py
|       |-- pdf_report.py
|-- tests/
|   |-- test_analytics.py
|   |-- test_export_orders.py
|-- work/
    |-- vendas - All Drive - Maino.xlsx
    |-- vendas - All Drive - Historico Gerensys.xlsx
    |-- vendas - FDY - Historico Gerensys.xlsx
    |-- produtos.xlsx
    |-- clientes.xlsx
    |-- pedidos_confirmados.xlsx
```

## 3. Fontes De Dados E Origem De Cada Campo

### 3.1 Fonte Maino

Arquivos com padrao:

- vendas - All Drive - Maino*.xlsx

Abas usadas:

- Relatorio de Pedidos
- Relatorio de Produtos

Campos principais gerados por item de pedido:

- Pedido ID: MAIN-{Numero}
- Numero do Pedido: coluna Numero
- Codigo do Produto: Codigo do Produto
- Quantidade: Quantidade do Pedido
- Valor Total: Preco Total do Produto (com fallback Quantidade x Preco Unitario)
- Status da Nota Fiscal: derivado de Status fiscal e Nota Fiscal
- Nome do Cliente: coluna Cliente
- Representante: coluna Representante (fallback env NOME_PADRAO_REPRESENTANTE)
- UF: extraida do nome do cliente quando possivel

### 3.2 Fonte Historica Gerensys

Arquivos com padrao:

- *Historico Gerensys*.xlsx

Regras:

- Movimentos de Entrada de Mercadoria sao descartados.
- Codigo antigo e mapeado para codigo Maino via aba Codigos em work/produtos.xlsx.
- Valor Total vem de Valor Final (ou Valor Original).
- Documento alimenta CPF/CNPJ do Cliente.
- Razao Social/Cliente alimenta Nome do Cliente.

### 3.3 Nova Fonte De Clientes

Arquivo:

- [work/clientes.xlsx](work/clientes.xlsx)

Fallback suportado:

- clientes.xmlx

Uso no export:

- Apos consolidar Maino + Gerensys, o processo enriquece linhas com dados cadastrais da base de clientes.
- Matching aplicado em [src/export_orders.py](src/export_orders.py):
  - 1) por documento (CNPJ/CPF)
  - 2) por nome normalizado (Razao Social e Nome Fantasia)

Campos preenchidos quando faltantes:

- CPF/CNPJ do Cliente
- Nome do Cliente
- CEP
- UF
- Cidade
- Representante

Observacoes:

- Apenas clientes ativos sao priorizados.
- UF pode ser inferida por CEP (fallback).
- Representante vazio usa NOME_PADRAO_REPRESENTANTE.

## 4. Pipeline De Extracao

Implementado em [src/export_orders.py](src/export_orders.py).

Etapas:

1. Leitura compartilhada de arquivos Excel com lock-safe no Windows.
2. Extracao de itens Maino.
3. Extracao de itens Gerensys.
4. Uniao das linhas em uma base unica.
5. Enriquecimento com base de clientes.
6. Gravacao final em [work/pedidos_confirmados.xlsx](work/pedidos_confirmados.xlsx).

Colunas finais esperadas na planilha consolidada:

1. Pedido ID
2. Numero do Pedido
3. Codigo do Produto
4. Quantidade
5. ID da Nota Fiscal
6. Status da Nota Fiscal
7. Status do Pedido
8. Data do Pedido
9. URL NFe
10. CPF/CNPJ do Cliente
11. Nome do Cliente
12. CEP
13. UF
14. Cidade
15. Valor Total
16. Representante

## 5. Dashboard - Fluxo De Carregamento E Performance

Arquivo principal: [src/app.py](src/app.py)

### 5.1 Carregamento

- A classe SalesAnalytics e carregada por cache_resource com TTL de 900s.
- A invalidacao usa assinatura de arquivos (mtime e size) de:
  - pedidos_confirmados.xlsx
  - produtos.xlsx
  - clientes.xlsx

### 5.2 Filtros Globais

Filtros da sidebar:

- Status da Nota Fiscal
- Pesquisa de Codigo do Produto
- Representante
- Regiao/UF
- Cliente (parcial)
- Data inicial/final

A aplicacao usa assinatura de filtro em session_state para evitar recalc desnecessario.

### 5.3 Otimizacoes Atuais

- Pre-colunas normalizadas de filtro em [src/analytics/processing.py](src/analytics/processing.py)
- Rentabilidade lazy (calculada sob demanda)
- Derivados de rentabilidade cacheados por assinatura
- Export Excel preparado sob demanda

## 6. Regras De Calculo Por Dominio

## 6.1 KPIs Operacionais E Fiscais

Implementacao: [src/analytics/kpis/sales_kpis.py](src/analytics/kpis/sales_kpis.py)

- Total de Pedidos = DISTINCT Pedido ID
- Volume Total Vendido = SUM Quantidade
- Produtos Unicos = DISTINCT Codigo do Produto
- Pedidos sem NF = pedidos unicos com status normalizado em {NAO_TRANSMITIDA, NAO EMITIDA}
- Pedidos com NF = Total de Pedidos - Pedidos sem NF
- Clientes ativos = cardinalidade da chave de cliente normalizada
- Pedidos por cliente = Total de Pedidos / Clientes ativos
- Taxa de emissao NF = Pedidos com NF / Total de Pedidos * 100

ABC/Pareto de produtos:

- Baseado em Quantidade vendida por Codigo do Produto
- Classe A ate acumulado 80%
- Classe B de 80% a 95%
- Classe C acima de 95%

## 6.2 KPIs De Clientes

Implementacao: [src/analytics/kpis/customer_kpis.py](src/analytics/kpis/customer_kpis.py)

Agrupamento por Cliente_Chave:

- Pedidos = nunique Pedido ID
- Receita_Total = sum Valor Total
- Ticket Medio = Receita_Total / Pedidos

## 6.3 KPIs De Representantes

Implementacao: [src/analytics/kpis/representative_kpis.py](src/analytics/kpis/representative_kpis.py)

Base:

- Primeiro consolida por pedido (Pedido ID + Numero do Pedido) usando Valor_Total first.

Resumo por representante:

- Receita_Total = sum Valor_Total
- Pedidos = nunique Pedido ID
- Clientes_Unicos = nunique Cliente_Chave
- Produtos_Distintos = nunique Codigo do Produto
- Ticket_Medio = Receita_Total / Pedidos
- Pedidos_por_Cliente = Pedidos / Clientes_Unicos
- Participacao (%) = Receita_Total / Receita_Total geral * 100

Adicionais:

- Recompra (%) por representante
- Atingimento (%) se houver coluna Meta
- Evolucao mensal por representante usando coluna de data detectada

## 6.4 KPIs Geograficos

Implementacao: [src/analytics/kpis/geography_kpis.py](src/analytics/kpis/geography_kpis.py)

Base:

- Consolida por pedido usando Valor_Total first
- Resolve UF por campo UF ou fallback por CEP
- Usa Cliente_Chave para contagem de clientes unicos

Indicadores:

- Receita por estado
- Clientes por estado
- Ticket medio por estado
- Participacoes de clientes e receita
- Top cidades por receita
- Top cidades por clientes
- Coordenadas por UF para mapa

## 6.5 KPIs De Rentabilidade

Implementacao: [src/analytics/kpis/profitability_kpis.py](src/analytics/kpis/profitability_kpis.py)

Mudanca importante vigente:

- Faturamento nao usa mais PU de saida como fonte primaria.
- Fonte de verdade de faturamento = Valor Total do pedido.
- Para manter analise por item/produto, o valor do pedido e rateado por linha:
  - proporcional a quantidade
  - se quantidade total do pedido for zero, rateio uniforme por numero de linhas

Formulas:

- Faturamento (linha) = rateio do Valor Total do pedido
- Custo Variavel (%) = por Origem do produto:
  - nacional: CUSTO_VARIAVEL_NACIONAL (default 0.2615)
  - importado: CUSTO_VARIAVEL_IMPORTADO (default 0.2015)
- Custo Total = (PU entrada * Quantidade) + (Faturamento * Custo Variavel %)
- Margem de contribuicao = Faturamento - Custo Total
- Margem Bruta (%) = Margem de contribuicao / Faturamento * 100

KPIs financeiros:

- revenue_total = sum Faturamento
- gross_profit_total = sum Margem de contribuicao
- gross_margin_avg = gross_profit_total / revenue_total * 100
- top_product, top_representative, top_customer por maior margem
- estimated_operating_profit_pct = gross_margin_avg - fixed_cost_pct
- estimated_operating_profit_value = revenue_total * estimated_operating_profit_pct / 100

fixed_cost_pct vem de LUCRO_OPERACIONAL_CUSTO_FIXO (default 25).

## 7. Mapa De Abas E Cartoes

Fonte das abas: [src/dashboard/views_sections](src/dashboard/views_sections)

### 7.1 Visao Geral

Arquivo: [src/dashboard/views_sections/overview.py](src/dashboard/views_sections/overview.py)

Cartoes:

- Total de Pedidos
- Volume Total Vendido (Itens)
- Faturamento Total
- Pedidos com Nota Fiscal
- Pedidos sem Nota Fiscal
- Taxa de Emissao de NF

Secao adicional:

- Top 5 produtos por volume (ABC/Pareto)

### 7.2 Rentabilidade

Arquivo: [src/dashboard/views_sections/profitability.py](src/dashboard/views_sections/profitability.py)

Cartoes:

- Faturamento Total
- Margem de contribuicao
- Margem Bruta Media
- Produto Mais Lucrativo
- Representante Mais Lucrativo
- Cliente Mais Lucrativo
- Lucro Operacional Estimado
- Margem Operacional

Analises:

- Evolucao mensal faturamento/lucro/margem
- Comparativo faturamento x lucro por produto
- Top produtos por lucro e receita
- Curvas ABC por receita e lucro
- Tabelas de top produtos, representantes e clientes

### 7.3 Representantes De Vendas

Arquivo: [src/dashboard/views_sections/representatives.py](src/dashboard/views_sections/representatives.py)

Cartoes:

- Representantes Ativos
- Clientes Atendidos
- Pedidos Totais
- Maior Mix por Representantes

Analises:

- Ranking por faturamento
- Tabela detalhada por representante
- Evolucao mensal de vendas por representante

### 7.4 Clientes

Arquivo: [src/dashboard/views_sections/customers.py](src/dashboard/views_sections/customers.py)

Cartoes:

- Clientes Ativos
- Pedidos por Cliente

Analises:

- Top 10 clientes por pedidos
- Tabela base de clientes

### 7.5 Produtos

Arquivo: [src/dashboard/views_sections/products.py](src/dashboard/views_sections/products.py)

Cartoes:

- Produtos Unicos Comercializados

Analises:

- Ranking de produtos mais vendidos
- Pareto 80/20
- Distribuicao ABC
- Tabela de classificacao ABC

### 7.6 Pedidos

Arquivo: [src/dashboard/views_sections/products.py](src/dashboard/views_sections/products.py)

Cartoes:

- Media de Itens/Pedido
- Mediana de Itens/Pedido
- Volume Maximo em Pedido
- Volume Minimo em Pedido

Analises:

- Histograma de volumes
- Boxplot de dispersao/outliers
- Ranking de pedidos de maior volume

### 7.7 Geo

Arquivo: [src/dashboard/views_sections/geography.py](src/dashboard/views_sections/geography.py)

Cartoes:

- Estados com Clientes
- Estados com Receita
- Cidades com Receita

Analises:

- Receita por estado
- Clientes por estado
- Ticket medio por estado
- Top cidades por receita
- Top cidades por clientes
- Mapa de calor por estado
- Pie de participacao da receita

### 7.8 Fiscal

Arquivo: [src/dashboard/views_sections/fiscal.py](src/dashboard/views_sections/fiscal.py)

Cartoes:

- Pedidos com Nota Fiscal
- Pedidos sem Nota Fiscal
- Taxa de Emissao de NF

Analises:

- Gauge de cobertura fiscal
- Donut por status de NF

### 7.9 Insights Gerenciais

Arquivo: [src/dashboard/views_sections/insights.py](src/dashboard/views_sections/insights.py)

Conteudo:

- Narrativas executivas baseadas na curva ABC fisica
- Alertas de concentracao
- Recomendacoes de diretoria

## 8. De Onde Cada Dado E Selecionado Para Cada Calculo

Resumo de lineage:

1. Base consolidada de pedidos em [work/pedidos_confirmados.xlsx](work/pedidos_confirmados.xlsx)
2. SalesRepository normaliza schema basico
3. SalesAnalytics aplica mapeamento de codigo de produto historico
4. CustomerRepository enriquece com base de clientes
5. SalesAnalytics precomputa colunas auxiliares de filtro
6. Cada modulo KPI agrupa e transforma de acordo com seu dominio
7. Views consomem resultados agregados para cartoes e graficos

Campos mais importantes:

- Quantidade: usado em volume, pareto, pedidos e custos
- Valor Total: fonte de receita de pedidos e base para rentabilidade (via rateio)
- Status da Nota Fiscal: compliance fiscal
- Pedido ID + Numero do Pedido: chaves de deduplicacao por pedido
- Codigo do Produto: analises de produto e rentabilidade
- Representante: analise comercial
- Cliente_Chave: analise de clientes e recorrencia
- CEP/UF/Cidade: analises geograficas

## 9. Variaveis De Ambiente Relevantes

- NOME_PADRAO_REPRESENTANTE (default Leonardo)
- CUSTO_VARIAVEL_NACIONAL (default 0.2615)
- CUSTO_VARIAVEL_IMPORTADO (default 0.2015)
- LUCRO_OPERACIONAL_CUSTO_FIXO (default 25)
- MIN_PED_TICKET_MEDIO (default 1)

## 10. Como Executar

### 10.1 Instalar dependencias

```bash
pip install -r requirements.txt
```

### 10.2 Gerar base consolidada

```bash
python src/export_orders.py
```

### 10.3 Subir dashboard

```bash
streamlit run src/app.py
```

## 11. Testes

### 11.1 Suite de analytics

```bash
python -m unittest tests.test_analytics -v
```

### 11.2 Suite de exportacao

```bash
python -m unittest tests.test_export_orders -v
```

## 12. Notas Operacionais

- O Streamlit reexecuta o script a cada interacao de UI; isso e esperado.
- O projeto usa cache e assinatura de filtros para minimizar recalc.
- Exportacoes de Excel e geracao de PDF sao sob demanda.
- Se o arquivo Excel estiver aberto, o export trata lock com fallback de gravacao.

## 13. Checklist De Consistencia Apos Mudancas

1. Rodar export_orders e verificar arquivo final em [work/pedidos_confirmados.xlsx](work/pedidos_confirmados.xlsx)
2. Subir o dashboard e validar filtros globais
3. Conferir cards principais por aba
4. Rodar suites de teste
5. Revisar logs de warnings de enriquecimento de clientes
