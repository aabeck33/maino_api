# Maino API Integration — Business Intelligence Suite

Este projeto oferece duas soluções complementares sobre os dados da plataforma ERP Mainô:

1. **Extrator de Pedidos** — consulta a API do Mainô e gera uma planilha Excel com os pedidos de venda e notas fiscais.
2. **Dashboard Executivo** — lê a planilha gerada e exibe um painel interativo de inteligência de negócios para apresentação à diretoria.

---

## Por que Streamlit + Plotly?

| Critério | Escolha |
|---|---|
| **Linguagem única** | Python puro — sem frontend separado |
| **Velocidade de desenvolvimento** | Dashboard completo em poucas horas |
| **Interatividade nativa** | Filtros, sliders e downloads sem JavaScript |
| **Qualidade gráfica** | Plotly oferece gráficos de nível corporativo (hover, zoom, export PNG) |
| **Distribuição interna** | Basta enviar o projeto + `streamlit run src/app.py` |
| **Manutenção** | Qualquer membro da equipe que saiba Python pode alterar o dashboard |

---

## Estrutura do Projeto

```text
Maino_API/
├── src/
│   ├── app.py                        # Entrypoint do Dashboard Executivo
│   ├── analytics/
│   │   └── processing.py             # Cálculo de KPIs, ABC, Pareto, estatísticas
│   ├── dashboard/
│   │   ├── components.py             # CSS, cards KPI, tabelas HTML, cabeçalho
│   │   └── views.py                  # Renderização de cada aba do dashboard
│   ├── utils/
│   │   └── logger.py                 # Logging centralizado
│   ├── export_ncms.py                # Extrator de NCMs (script legado)
│   └── export_orders.py              # Extrator de Pedidos de Venda
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

### Extração de NCMs (script legado)

```bash
python src/export_ncms.py
```

---

## Dashboard — Abas e Funcionalidades

| Aba | Conteúdo |
|---|---|
| 📈 **Visão Geral** | 6 KPIs em cards (pedidos, volume, produtos únicos, compliance fiscal), top 5 produtos |
| 📦 **Produtos** | Top 10/20 produtos (barra horizontal), Gráfico de Pareto, Curva ABC (classificação A/B/C) |
| 🛒 **Pedidos** | Estatísticas de distribuição (média, mediana, min, max), histograma, boxplot, ranking dos maiores pedidos |
| ⚖️ **Fiscal** | Gauge de taxa de emissão de NF, donut chart por status, KPI cards de compliance |
| 💡 **Insights Gerenciais** | Narrativas automáticas sobre produto líder, concentração de vendas, gestão ABC e compliance fiscal |

### Filtros Globais (barra lateral)

- **Status da Nota Fiscal**: Todos / Com NF Emitida / Sem NF Emitida
- **Pesquisa por Produto**: Filtra por código do produto em tempo real
- **Exportar para Excel**: Baixa os dados conforme os filtros aplicados
- **Tema**: Alterna entre modo claro ☀️ e modo escuro 🌙

---

## Testes

```bash
# Testes do módulo de analytics (22 casos)
python -m unittest tests/test_analytics.py -v

# Testes do extrator de pedidos (6 casos)
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
| `URL NFe` | url para abrir a visualização da DANFE |
