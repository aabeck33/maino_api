"""
    Módulo de processamento de dados de vendas e análise de KPIs.
    Este módulo fornece a classe SalesAnalytics, que encapsula a lógica de carregamento,
    filtragem e análise de dados de vendas a partir de uma planilha Excel. Ele oferece
    métodos para calcular KPIs, realizar análises ABC/Pareto, estatísticas de pedidos
    e distribuição fiscal, permitindo que o aplicativo Streamlit forneça insights gerenciais
    de forma eficiente e interativa.
"""

from pathlib import Path
from typing import Dict, Any, Tuple
import unicodedata
import pandas as pd

from utils.geo import BRAZIL_STATE_CENTROIDS, map_cep_to_uf

class SalesAnalytics:
    """
    Classe responsável pelo carregamento, filtragem e análise de dados de vendas.
    """
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
        df["CEP"] = df["CEP"].astype(str).str.strip()

        return df

    @staticmethod
    def _normalize_status(status: Any) -> str:
        if status is None:
            return ""

        text = str(status).strip().upper()
        text = unicodedata.normalize("NFKD", text)
        text = "".join(ch for ch in text if unicodedata.category(ch) != "Mn")
        return text

    def get_filtered_data(self, status_filter: str = "Todos", search_product: str = "") -> pd.DataFrame:
        """Applies global filters to the raw DataFrame."""
        filtered_df = self.df.copy()

        # Filter by Invoice Status
        if status_filter != "Todos":
            normalized_status = filtered_df["Status da Nota Fiscal"].apply(SalesAnalytics._normalize_status)
            non_emitted = normalized_status.isin(["NAO_TRANSMITIDA", "NAO EMITIDA"])

            if status_filter == "Com NF Emitida":
                filtered_df = filtered_df[~non_emitted]
            elif status_filter == "Sem NF Emitida":
                filtered_df = filtered_df[non_emitted]
            else:
                filtered_df = filtered_df[filtered_df["Status da Nota Fiscal"].apply(SalesAnalytics._normalize_status) == SalesAnalytics._normalize_status(status_filter)]

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
        normalized_status = df_unique_orders["Status da Nota Fiscal"].apply(SalesAnalytics._normalize_status)
        orders_without_nf = df_unique_orders[normalized_status.isin(["NAO_TRANSMITIDA", "NAO EMITIDA"])]["Pedido ID"].count()
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

    @staticmethod
    def _normalize_geo_data(df: pd.DataFrame) -> pd.DataFrame:
        if df.empty:
            return df.copy()

        normalized = df.copy()
        normalized["CEP"] = normalized["CEP"].astype(str).str.strip().fillna("")
        if "UF" not in normalized.columns:
            normalized["UF"] = "N/A"
        if "Cidade" not in normalized.columns:
            normalized["Cidade"] = "N/A"
        if "Valor Total" not in normalized.columns:
            normalized["Valor Total"] = 0.0

        normalized["UF"] = normalized["UF"].astype(str).str.strip().str.upper().replace({"": "N/A", "NONE": "N/A", "N/A": "N/A"})
        normalized["Cidade"] = normalized["Cidade"].astype(str).str.strip().replace({"": "N/A", "None": "N/A", "nan": "N/A"})
        normalized.loc[normalized["Cidade"] == "", "Cidade"] = "N/A"
        normalized["Valor Total"] = pd.to_numeric(normalized["Valor Total"], errors="coerce").fillna(0.0)

        def resolve_uf(row: pd.Series) -> str:
            if row["UF"] not in {"", "N/A", "NONE"}:
                return row["UF"]
            return map_cep_to_uf(row["CEP"])

        normalized["UF"] = normalized.apply(resolve_uf, axis=1)
        normalized.loc[normalized["UF"] == "", "UF"] = "N/A"
        normalized["Cidade"] = normalized["Cidade"].replace({"": "N/A"})

        return normalized

    @staticmethod
    def _build_order_summary(df: pd.DataFrame) -> pd.DataFrame:
        if df.empty:
            return pd.DataFrame()

        normalized = SalesAnalytics._normalize_geo_data(df)
        summary = normalized.groupby(["Pedido ID", "Número do Pedido"], dropna=False, as_index=False).agg(
            CEP=("CEP", "first"),
            UF=("UF", lambda values: next((v for v in values if v not in {"", "N/A"}), "N/A")),
            Cidade=("Cidade", lambda values: next((v for v in values if v not in {"", "N/A"}), "N/A")),
            Valor_Total=("Valor Total", "first"),
            Status_da_Nota_Fiscal=("Status da Nota Fiscal", "first")
        )
        summary["Valor_Total"] = pd.to_numeric(summary["Valor_Total"], errors="coerce").fillna(0.0)
        return summary

    @staticmethod
    def get_revenue_by_city(df: pd.DataFrame) -> pd.DataFrame:
        orders = SalesAnalytics._build_order_summary(df)
        if orders.empty:
            return pd.DataFrame()

        result = orders.groupby("Cidade", dropna=False, as_index=False).agg(
            Valor_Total=("Valor_Total", "sum"),
            Clientes=("Pedido ID", "nunique")
        )
        return result.sort_values("Valor_Total", ascending=False)

    @staticmethod
    def get_clients_by_state(df: pd.DataFrame) -> pd.DataFrame:
        orders = SalesAnalytics._build_order_summary(df)
        if orders.empty:
            return pd.DataFrame()

        result = orders.groupby("UF", dropna=False, as_index=False).agg(
            Clientes=("Pedido ID", "nunique")
        )
        return result.sort_values("Clientes", ascending=False)

    @staticmethod
    def get_state_revenue(df: pd.DataFrame) -> pd.DataFrame:
        orders = SalesAnalytics._build_order_summary(df)
        if orders.empty:
            return pd.DataFrame()

        result = orders.groupby("UF", dropna=False, as_index=False).agg(
            Valor_Total=("Valor_Total", "sum"),
            Clientes=("Pedido ID", "nunique")
        )
        return result.sort_values("Valor_Total", ascending=False)

    @staticmethod
    def get_state_ticket_average(df: pd.DataFrame) -> pd.DataFrame:
        state_df = SalesAnalytics.get_state_revenue(df)
        if state_df.empty:
            return pd.DataFrame()

        state_df["Ticket Médio"] = state_df.apply(
            lambda row: row["Valor_Total"] / row["Clientes"] if row["Clientes"] > 0 else 0.0,
            axis=1
        )
        state_df["Participação Clientes (%)"] = (
            state_df["Clientes"] / state_df["Clientes"].sum() * 100
        )
        state_df["Participação Receita (%)"] = (
            state_df["Valor_Total"] / state_df["Valor_Total"].sum() * 100
        )
        return state_df.sort_values("Ticket Médio", ascending=False)

    @staticmethod
    def get_top_cities_by_revenue(df: pd.DataFrame, top_n: int = 10) -> pd.DataFrame:
        city_revenue = SalesAnalytics.get_revenue_by_city(df)
        return city_revenue.head(top_n)

    @staticmethod
    def get_top_cities_by_customers(df: pd.DataFrame, top_n: int = 10) -> pd.DataFrame:
        city_data = SalesAnalytics.get_revenue_by_city(df)
        return city_data.sort_values("Clientes", ascending=False).head(top_n)

    @staticmethod
    def get_state_geo_coordinates(df: pd.DataFrame) -> pd.DataFrame:
        state_df = SalesAnalytics.get_state_ticket_average(df)
        if state_df.empty:
            return pd.DataFrame()

        coords = []
        for uf in state_df["UF"]:
            coords.append(BRAZIL_STATE_CENTROIDS.get(uf, (None, None)))

        state_df["Latitude"] = [c[0] for c in coords]
        state_df["Longitude"] = [c[1] for c in coords]
        return state_df[state_df["Latitude"].notna() & state_df["Longitude"].notna()].copy()
