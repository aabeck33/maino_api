import pandas as pd
import numpy as np
from pathlib import Path
from typing import Dict, Any, Tuple

class SalesAnalytics:
    def __init__(self, excel_path: Path):
        self.excel_path = excel_path
        self.df = self._load_data()
        
    def _load_data(self) -> pd.DataFrame:
        """Loads and cleans the sales orders data from the Excel file."""
        if not self.excel_path.exists():
            raise FileNotFoundError(f"Planilha de vendas não encontrada no caminho: {self.excel_path}")

        try:
            df = pd.read_excel(self.excel_path, engine="openpyxl")
        except PermissionError:
            raise PermissionError(
                f"O arquivo '{self.excel_path.name}' está sendo usado por outro programa "
                f"(ex: Excel aberto). Feche o arquivo e tente novamente."
            )
        
        # Ensure correct datatypes
        df["Quantidade"] = pd.to_numeric(df["Quantidade"], errors="coerce").fillna(0.0)
        df["Número do Pedido"] = df["Número do Pedido"].astype(str)
        df["Código do Produto"] = df["Código do Produto"].astype(str).str.strip()
        df["ID da Nota Fiscal"] = df["ID da Nota Fiscal"].astype(str).str.strip()
        df["Status da Nota Fiscal"] = df["Status da Nota Fiscal"].astype(str).str.strip()
        df["URL NFe"] = df["URL NFe"].astype(str).str.strip()
        
        return df

    def get_filtered_data(self, status_filter: str = "Todos", search_product: str = "") -> pd.DataFrame:
        """Applies global filters to the raw DataFrame."""
        filtered_df = self.df.copy()
        
        # Filter by Invoice Status
        if status_filter != "Todos":
            if status_filter == "Com NF Emitida":
                filtered_df = filtered_df[filtered_df["Status da Nota Fiscal"] != "NAO_TRANSMITIDA"]
            elif status_filter == "Sem NF Emitida":
                filtered_df = filtered_df[filtered_df["Status da Nota Fiscal"] == "NAO_TRANSMITIDA"]
            else:
                filtered_df = filtered_df[filtered_df["Status da Nota Fiscal"] == status_filter]
                
        # Search by Product Code
        if search_product:
            filtered_df = filtered_df[filtered_df["Código do Produto"].str.contains(search_product, case=False, na=False)]
            
        return filtered_df

    @staticmethod
    def calculate_kpis(df: pd.DataFrame) -> Dict[str, Any]:
        """Calculates core KPIs from a given DataFrame."""
        if df.empty:
            return {
                "total_orders": 0,
                "total_products": 0,
                "total_qty_sold": 0.0,
                "unique_products": 0,
                "orders_with_nf": 0,
                "orders_without_nf": 0,
                "nf_emission_rate": 0.0
            }
            
        # Unique orders and products
        total_orders = df["Pedido ID"].nunique()
        total_qty_sold = df["Quantidade"].sum()
        unique_products = df["Código do Produto"].nunique()
        
        # Invoice stats are calculated on unique orders to represent real fiscal volume
        df_unique_orders = df.drop_duplicates(subset=["Pedido ID"])
        orders_without_nf = df_unique_orders[df_unique_orders["Status da Nota Fiscal"] == "NAO_TRANSMITIDA"]["Pedido ID"].count()
        orders_with_nf = total_orders - orders_without_nf
        
        nf_emission_rate = (orders_with_nf / total_orders * 100) if total_orders > 0 else 0.0
        
        return {
            "total_orders": total_orders,
            "total_products": unique_products, # Total products (distinct count)
            "total_qty_sold": total_qty_sold,
            "unique_products": unique_products,
            "orders_with_nf": orders_with_nf,
            "orders_without_nf": orders_without_nf,
            "nf_emission_rate": nf_emission_rate
        }

    @staticmethod
    def get_abc_pareto_analysis(df: pd.DataFrame) -> Tuple[pd.DataFrame, Dict[str, Any]]:
        """
        Performs ABC Curve classification and cumulative Pareto analysis on products.
        Returns the classified DataFrame and summary dictionary.
        """
        if df.empty:
            return pd.DataFrame(), {"A": 0, "B": 0, "C": 0}
            
        # Group by product
        df_prod = df.groupby("Código do Produto")["Quantidade"].sum().reset_index()
        df_prod = df_prod.sort_values(by="Quantidade", ascending=False).reset_index(drop=True)
        
        total_qty = df_prod["Quantidade"].sum()
        
        # Pareto and ABC percentages
        df_prod["Participação (%)"] = (df_prod["Quantidade"] / total_qty * 100) if total_qty > 0 else 0.0
        df_prod["Acumulado"] = df_prod["Quantidade"].cumsum()
        df_prod["Acumulado (%)"] = (df_prod["Acumulado"] / total_qty * 100) if total_qty > 0 else 0.0
        
        # Classification into A (<= 80%), B (80% to 95%), C (> 95%)
        classes = []
        for idx, val in enumerate(df_prod["Acumulado (%)"]):
            if idx == 0:
                # Ensure at least the first item is Class A
                classes.append("A")
            elif val <= 80.0:
                classes.append("A")
            elif val <= 95.0:
                classes.append("B")
            else:
                classes.append("C")
                
        df_prod["Classe ABC"] = classes
        
        # Counts per class
        class_counts = df_prod["Classe ABC"].value_counts().to_dict()
        for k in ["A", "B", "C"]:
            class_counts.setdefault(k, 0)
            
        return df_prod, class_counts

    @staticmethod
    def get_order_stats(df: pd.DataFrame) -> Tuple[Dict[str, Any], pd.DataFrame]:
        """
        Calculates distribution statistics for orders and returns a summary 
        along with the sorted list of largest orders.
        """
        if df.empty:
            return {
                "mean": 0.0,
                "median": 0.0,
                "max": 0.0,
                "min": 0.0
            }, pd.DataFrame()
            
        # Group by order to get total items/quantity per order
        df_order = df.groupby(["Pedido ID", "Número do Pedido"])["Quantidade"].sum().reset_index()
        
        stats = {
            "mean": df_order["Quantidade"].mean(),
            "median": df_order["Quantidade"].median(),
            "max": df_order["Quantidade"].max(),
            "min": df_order["Quantidade"].min()
        }
        
        largest_orders = df_order.sort_values(by="Quantidade", ascending=False).reset_index(drop=True)
        
        return stats, largest_orders

    @staticmethod
    def get_fiscal_distribution(df: pd.DataFrame) -> pd.DataFrame:
        """Calculates quantity and percentage distribution for invoice statuses."""
        if df.empty:
            return pd.DataFrame()
            
        df_unique_orders = df.drop_duplicates(subset=["Pedido ID"])
        df_fiscal = df_unique_orders.groupby("Status da Nota Fiscal")["Pedido ID"].count().reset_index(name="Quantidade")
        total_orders = df_fiscal["Quantidade"].sum()
        df_fiscal["Percentual (%)"] = (df_fiscal["Quantidade"] / total_orders * 100) if total_orders > 0 else 0.0
        
        return df_fiscal
