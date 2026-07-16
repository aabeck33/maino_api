# Maino API Integration — Business Intelligence Suite

Este projeto oferece duas soluções complementares sobre os dados da plataforma ERP Mainô:

1. **Extrator de Pedidos** — consulta a API do Mainô e gera uma planilha Excel com os pedidos de venda, cliente e dados fiscais.
2. **Dashboard Executivo** — lê as planilhas geradas e exibe um painel interativo de inteligência de negócios para apresentação à diretoria, incluindo indicadores financeiros, rentabilidade, ranking de produtos e análise por representante/cliente.

O dashboard inclui análises geográficas por estado e cidade, usando centroídes de UF e inferência de UF por CEP sem dependência de APIs externas.

---

## Por que Streamlit + Plotly?

| Critério | Escolha |
|---|---|
| **Linguagem única** | Python puro — sem frontend separado |
| **Velocidade de desenvolvimento** | Interface pronta em poucas horas |
| **Interatividade nativa** | Filtros, tabs, exportação e tema sem JavaScript |
| **Qualidade gráfica** | Plotly oferece gráficos corporativos com hover e zoom |
| **Distribuição interna** | Basta executar `streamlit run src/app.py` |
| **Manutenção** | Qualquer membro da equipe que saiba Python pode alterar facilmente |

---

## Estrutura do Projeto

```text
Maino_API/
├── src/
│   ├── app.py                        # Entrypoint do Dashboard Executivo
│   ├── analytics/
│   │   └── processing.py             # Cálculo de KPIs, ABC, Pareto, estatísticas e geografia
│   ├── dashboard/
│   │   ├── components.py             # CSS, cards KPI, tabelas HTML e cabeçalho
│   │   └── views.py                  # Renderização de cada aba do dashboard
│   ├── utils/
│   │   ├── geo.py                    # Helpers de CEP, mapeamento UF e normalização numérica
│   │   └── logger.py                 # Logging centralizado
│   ├── export_ncms.py                # Extrator de NCMs (script legado)
│   └── export_orders.py              # Extrator de Pedidos de Venda e geração de Excel
│
├── tests/
│   ├── test_analytics.py             # Testes unitários do módulo de analytics
│   └── test_export_orders.py         # Testes unitários do extrator
│
├── work/
│   ├── ncms_export.xlsx              # Resultado do extrator de NCMs
│   └── pedidos_confirmados.xlsx      # Planilha de entrada do dashboard
│
├── .env.example                      # Modelo de variáveis de ambiente
├── requirements.txt                  # Dependências Python
└── README.md
```

---

## Instalação

### 1. Criar e ativar o ambiente virtual

```powershell
# Windows (PowerShell)
python -m venv venv
.\venv\Scripts\Activate.ps1
```

```bash
# Linux / macOS
python3 -m venv venv
source venv/bin/activate
```

### 2. Instalar dependências

```bash
pip install -r requirements.txt
```

### 3. Configurar variáveis de ambiente

```bash
# Copiar o arquivo de exemplo
cp .env.example .env
```

Edite `.env` e preencha:

```env
MAINO_API_TOKEN=seu_token_jwt_aqui
MAINO_ORDER_STATUS=Pedido gerado
```

---

## Execução

### Extração de Pedidos (gera a planilha de entrada)

```bash
python src/export_orders.py
```

A planilha será salva em `work/pedidos_confirmados.xlsx`.

### Dashboard Executivo

```bash
streamlit run src/app.py
```

Acesse no navegador: **http://localhost:8501**

O painel gera automaticamente arquivos de resultado em [work](work), incluindo:
- [work/indicadores_financeiros.xlsx](work/indicadores_financeiros.xlsx) com a base detalhada de rentabilidade
- [work/indicadores_financeiros_resumo.xlsx](work/indicadores_financeiros_resumo.xlsx) com resumos por produto, representante e cliente

### Extração de NCMs (script legado)

```bash
python src/export_ncms.py
```

---

## Dashboard — Abas e Funcionalidades

| Aba | Conteúdo |
|---|---|
| 📈 **Visão Geral** | KPIs de pedidos, volume, produtos únicos, compliance fiscal e top 5 produtos |
| � **Rentabilidade** | Faturamento, lucro bruto, margem bruta, ranking de produtos e curvas ABC financeiras |
| 👥 **Representantes de Vendas** | Performance comercial por representante, receita e rentabilidade |
| �📦 **Produtos** | Ranking de produtos, Gráfico de Pareto e Curva ABC |
| 🛒 **Pedidos** | Estatísticas de pedido, histograma, boxplot e ranking dos maiores pedidos |
| 🌍 **Geo** | Receita por estado, clientes por estado, ticket médio, top cidades e mapa de calor regional |
| ⚖️ **Fiscal** | Gauge de emissão de NF, distribuição por status e indicadores de compliance |
| 💡 **Insights Gerenciais** | Narrativas automáticas sobre concentração de receita e performance fiscal |

### Filtros Globais (barra lateral)

- **Status da Nota Fiscal**: Todos / Com NF Emitida / Sem NF Emitida
- **Pesquisa por Produto**: Filtra por código do produto em tempo real
- **Exportar para Excel**: Baixa os dados filtrados
- **Tema**: Alterna entre modo claro ☀️ e modo escuro 🌙

---

## Testes

```bash
# Testes do módulo de analytics
python -m unittest tests/test_analytics.py -v

# Testes do extrator de pedidos
python -m unittest tests/test_export_orders.py -v
```

---

## Colunas da Planilha de Entrada

| Coluna | Descrição |
|---|---|
| `Pedido ID` | UUID único do pedido |
| `Número do Pedido` | Número sequencial do pedido |
| `Status do Pedido` | `Pedido gerado`, `Orçamento gerado`, etc. |
| `Código do Produto` | Código do SKU comercializado |
| `Quantidade` | Quantidade de unidades do item |
| `ID da Nota Fiscal` | UUID da NF-e ou `N/A` |
| `Status da Nota Fiscal` | `ACEITA`, `Não emitida`, etc. |
| `URL NFe` | URL para visualização da DANFE |
| `CEP` | CEP do cliente usado para geografia e inferência de UF |
| `UF` | Unidade federativa do cliente |
| `Cidade` | Município ou cidade do cliente |
| `Valor Total` | Total do pedido somando todas as parcelas de cobrança |
