# Maino Business Intelligence & Extrator de Vendas Excel

Este projeto oferece uma solução completa para consolidação, inteligência de negócios e análise de KPIs sobre dados de vendas da empresa **All Drive Transmission**, integrando relatórios do ERP Mainô e históricos migrados do sistema Gerensys.

## 🚀 Funcionalidades Principais

1. **Extrator e Consolidador de Vendas (`src/export_orders.py`)**:
   - Lê os arquivos de vendas da All Drive do ERP Mainô (`vendas - All Drive - Maino*.xlsx`).
   - Lê o catálogo de produtos (`produtos.xlsx`).
   - Lê arquivos de histórico do sistema antigo (`*Histórico Gerensys*.xlsx`).
   - Mapeia códigos de produtos do sistema Gerensys para os novos códigos do Mainô utilizando a aba `Códigos`.
   - Filtra movimentações desconsiderando `Entrada de Mercadoria` e processando `Nota Fiscal 55` e `Pedido de Venda`.
   - Trata regras fiscais (como desconsiderar valores de vendas com `Confirmado (sem faturamento)`).
   - Extrai localização e UF do cliente a partir de CEP ou sufixo da Razão Social/Cliente.
   - Trata concorrência de leitura em arquivos abertos no Microsoft Excel usando abertura compartilhada no Windows.
   - Gera a planilha unificada em `work/pedidos_confirmados.xlsx`.

2. **Dashboard Executivo Streamlit (`src/app.py`)**:
   - Painel interativo de BI com suporte a modo claro ☀️ e escuro 🌙.
   - Abas dedicadas: Visão Geral, Rentabilidade, Representantes, Clientes, Produtos, Pedidos, Análise Geográfica, Conformidade Fiscal e Insights Gerenciais.
   - Filtros globais dinâmicos por status de Nota Fiscal, código de produto, representante, UF, cliente e intervalo de datas.
   - Geração automática das planilhas `work/indicadores_financeiros.xlsx` e `work/indicadores_financeiros_resumo.xlsx`.
   - Botão para exportação e download de relatórios executivos em formato PDF (`ReportLab`).

---

## 📁 Estrutura do Projeto

```text
Maino_API/
├── src/
│   ├── app.py                        # Entrypoint do Dashboard Executivo Streamlit
│   ├── export_orders.py              # Consolidador e Extrator de Vendas Excel
│   ├── export_ncms.py                # Extrator de NCMs (utilitário)
│   ├── analytics/
│   │   └── processing.py             # Motor de cálculo de KPIs, Rentabilidade, ABC/Pareto e Geografia
│   ├── dashboard/
│   │   ├── components.py             # CSS, cards KPI, temas e cabeçalho
│   │   └── views.py                  # Componentes visuais das abas do dashboard
│   └── utils/
│       ├── geo.py                    # Leitura compartilhada de Excel, inferência de UF e parser de CEP
│       ├── logger.py                 # Logging centralizado
│       └── pdf_report.py             # Gerador de relatórios gerenciais em PDF
│
├── tests/
│   ├── test_analytics.py             # Testes unitários do módulo de analytics
│   └── test_export_orders.py         # Testes unitários do extrator de vendas
│
├── work/
│   ├── vendas - All Drive - Maino.xlsx         # Fonte de dados Mainô
│   ├── produtos.xlsx                           # Catálogo de produtos com custos e origem
│   ├── vendas - All Drive - Histórico Gerensys.xlsx # Histórico de vendas Gerensys
│   ├── pedidos_confirmados.xlsx                # Resultado consolidado do extrator
│   ├── indicadores_financeiros.xlsx            # Base detalhada de rentabilidade
│   └── indicadores_financeiros_resumo.xlsx     # Resumo financeiro por produto, representante e cliente
│
├── .env.example
├── requirements.txt
└── README.md
```

---

## 🛠️ Instalação

### 1. Criar e ativar o ambiente virtual

**Windows (PowerShell)**:
```powershell
python -m venv .venv
.\.venv\Scripts\Activate.ps1
```

**Linux / macOS**:
```bash
python3 -m venv .venv
source .venv/bin/activate
```

### 2. Instalar as dependências

```bash
pip install -r requirements.txt
```

---

## 💻 Execução

### Step 1: Extração e Consolidação dos Dados

Execute o extrator para ler todas as planilhas de entrada em `work/` e gerar `work/pedidos_confirmados.xlsx`:

```bash
python src/export_orders.py
```

### Step 2: Dashboard Executivo Streamlit

Para iniciar o painel interativo:

```bash
streamlit run src/app.py
```

Acesse no navegador em: **http://localhost:8501**

---

## 📋 Estrutura da Planilha Gerada (`work/pedidos_confirmados.xlsx`)

Cada linha da planilha representa um item de pedido/venda consolidado. As 6 primeiras colunas seguem rigorosamente a ordem exigida:

1. `Pedido ID`
2. `Número do Pedido`
3. `Código do Produto`
4. `Quantidade`
5. `ID da Nota Fiscal`
6. `Status da Nota Fiscal`
7. `Status do Pedido`
8. `Data do Pedido`
9. `URL NFe`
10. `CPF/CNPJ do Cliente`
11. `Nome do Cliente`
12. `CEP`
13. `UF`
14. `Cidade`
15. `Valor Total`
16. `Representante`

---

## 🧪 Execução de Testes Unitários

Para rodar todos os testes automatizados da aplicação:

```bash
python -m unittest discover tests -v
```
