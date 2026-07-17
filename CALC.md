# Documentação dos Indicadores e Cálculos

## 1. Indicadores Operacionais Gerais

### Total de Pedidos
**Fórmula**
```text
COUNT(DISTINCT Pedido ID)
```

### Volume Total Vendido
**Fórmula**
```text
Σ Quantidade
```

### Produtos Únicos Comercializados
**Fórmula**
```text
COUNT(DISTINCT Código do Produto)
```

---

## 2. Indicadores de Conformidade Fiscal

### Pedidos com Nota Fiscal
```text
Pedidos com NF = Total de Pedidos - Pedidos sem NF
```

### Pedidos sem Nota Fiscal
Considera os status:

- NAO_TRANSMITIDA
- NAO EMITIDA

### Taxa de Emissão de NF
```text
(Pedidos com NF / Total de Pedidos) × 100
```

### Distribuição Fiscal por Status
```text
(Qtd do Status / Total de Pedidos) × 100
```

---

## 3. Indicadores de Produtos (ABC/Pareto)

### Quantidade Vendida por Produto
```text
Σ Quantidade do Produto
```

### Participação do Produto
```text
(Qtd Produto / Quantidade Total) × 100
```

### Participação Acumulada
```text
Acumulado (%) = Soma das participações até o item atual
```

### Classificação ABC

**Classe A**
```text
Acumulado ≤ 80%
```

**Classe B**
```text
80% < Acumulado ≤ 95%
```

**Classe C**
```text
Acumulado > 95%
```

---

## 4. Indicadores de Pedidos

### Média de Itens por Pedido
```text
AVG(Itens por Pedido)
```

### Mediana de Itens por Pedido
```text
MEDIAN(Itens por Pedido)
```

### Maior Pedido
```text
MAX(Itens por Pedido)
```

### Menor Pedido
```text
MIN(Itens por Pedido)
```

---

## 5. Indicadores Financeiros e Rentabilidade

### Faturamento
```text
Preço de Venda × Quantidade
```

### Custo Variável

- Nacional: 26,15%
- Importado: 20,15%

### Custo Total
```text
(Custo Unitário × Quantidade)
+
(Faturamento × % Custo Variável)
```

### Lucro Bruto
```text
Faturamento - Custo Total
```

### Margem Bruta
```text
(Lucro Bruto / Faturamento) × 100
```

### Faturamento Total
```text
Σ Faturamento
```

### Lucro Bruto Total
```text
Σ Lucro Bruto
```

### Margem Bruta Média
```text
(Lucro Bruto Total / Faturamento Total) × 100
```

### Participação no Lucro
```text
(Lucro Produto / Lucro Total) × 100
```

### Participação no Faturamento
```text
(Faturamento Produto / Faturamento Total) × 100
```

### Produto Mais Lucrativo
```text
MAX(Lucro Bruto por Produto)
```

### Representante Mais Lucrativo
```text
MAX(Lucro Bruto por Representante)
```

### Cliente Mais Lucrativo
```text
MAX(Lucro Bruto por Cliente)
```

---

## 6. Indicadores Comerciais por Representante

### Receita Total
```text
Σ Valor Total dos Pedidos
```

### Clientes Únicos
```text
COUNT(DISTINCT Cliente)
```

### Pedidos
```text
COUNT(Pedido ID)
```

### Ticket Médio
```text
Receita Total / Pedidos
```

### Pedidos por Cliente
```text
Pedidos / Clientes Únicos
```

### Participação do Representante
```text
Receita Representante / Receita Total × 100
```

### Atingimento de Meta
```text
Receita Total / Meta × 100
```

### Taxa de Recompra
```text
Clientes Recorrentes / Clientes Totais × 100
```

---

## 7. Indicadores Geográficos

### Clientes por Estado
```text
COUNT(DISTINCT Pedido ID)
```

> Observação: atualmente o sistema contabiliza pedidos únicos e não clientes reais.

### Receita por Estado
```text
Σ Valor Total
```

### Ticket Médio por Estado
```text
Receita Estado / Clientes Estado
```

### Participação de Clientes por Estado
```text
Clientes Estado / Clientes Totais × 100
```

### Participação da Receita por Estado
```text
Receita Estado / Receita Total × 100
```

### Top Cidades por Receita
```text
Σ Valor Total
```

### Top Cidades por Clientes
```text
COUNT(DISTINCT Pedido ID)
```

---

# Melhorias Recomendadas

## 1. Unificar o conceito de faturamento

Atualmente existem duas fontes de receita:

- Valor Total do Pedido
- Preço de Venda × Quantidade

Recomenda-se utilizar uma única definição de faturamento em todo o dashboard.

## 2. Corrigir Clientes por Estado

Substituir:

```text
COUNT(DISTINCT Pedido ID)
```

Por:

```text
COUNT(DISTINCT Cliente)
```

## 3. Criar Curvas ABC adicionais

- ABC por Quantidade
- ABC por Receita
- ABC por Lucro

## 4. Evoluir a análise de rentabilidade

Incluir:

- Frete
- Comissão
- Impostos reais
- Despesas financeiras
- Devoluções

Permitindo cálculo de:

- Margem de Contribuição
- EBITDA Comercial

## 5. Incluir indicadores temporais

- Crescimento Mês x Mês (MoM)
- Crescimento Ano x Ano (YoY)
- Rolling 12 meses
- Ticket Médio mensal
- Margem mensal
- Lucro mensal