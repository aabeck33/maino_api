from pathlib import Path
import sys
sys.path.insert(0, str(Path(__file__).resolve().parent.parent / 'src'))

import pandas as pd
from analytics.processing import SalesAnalytics

# Simulated dataset with missing/empty representante
data = [
    {'Pedido ID':'1','Valor Total':100.0,'Quantidade':1,'Código do Produto':'P1','CEP':'12345','Cliente':'C1','Representante':'','Data':'2026-01-01'},
    {'Pedido ID':'2','Valor Total':200.0,'Quantidade':2,'Código do Produto':'P2','CEP':'12345','Cliente':'C1','Data':'2026-02-01'},
    {'Pedido ID':'3','Valor Total':150.0,'Quantidade':1,'Código do Produto':'P3','CEP':'67890','Cliente':'C2','Representante':None,'Data':'2026-01-15'},
]

# DataFrame without the Representante column
# data2 = [
#     {'Pedido ID':'4','Valor Total':120.0,'Quantidade':1,'Código do Produto':'P4','CEP':'11111','Cliente':'C3','Data':'2026-03-01'}
# ]

# df2 = pd.DataFrame(data2)

df = pd.DataFrame(data)

rep_rebuy = SalesAnalytics.get_representative_repurchase_rate(df)
rep_summary = SalesAnalytics.get_representative_sales_summary(df)

print('Rep Rebuy:')
print(rep_rebuy)
print('\nRep Summary:')
print(rep_summary)

# Merge as in views
rep_rebuy_subset = rep_rebuy[[col for col in ["Representante","Clientes_Recorrentes","Clientes_Total","Recompra (%)"] if col in rep_rebuy.columns]]
merged = rep_summary.merge(rep_rebuy_subset, on='Representante', how='left')

print('\nMerged:')
print(merged)
