"""
    Módulo de processamento de dados de vendas e análise de KPIs.
    Este módulo fornece a classe SalesAnalytics, que encapsula a lógica de carregamento,
    filtragem e análise de dados de vendas a partir de uma planilha Excel. Ele oferece
    métodos para calcular KPIs, realizar análises ABC/Pareto, estatísticas de pedidos
    e distribuição fiscal, permitindo que o aplicativo Streamlit forneça insights gerenciais
    de forma eficiente e interativa.
"""

import os
from pathlib import Path
from typing import Dict, Any, Tuple, Optional
import unicodedata
import pandas as pd
from dotenv import load_dotenv

from utils.geo import BRAZIL_STATE_CENTROIDS, map_cep_to_uf
from utils.logger import setup_logger

logger = setup_logger("maino_analytics")
load_dotenv()

class SalesAnalytics:
    """
    Classe responsável pelo carregamento, filtragem e análise de dados de vendas.
    """
    def __init__(self, excel_path: Path, products_excel_path: Optional[Path] = None):
        self.excel_path = excel_path
        self.products_excel_path = products_excel_path
        self.products_df = self.load_products_catalog(products_excel_path)
        self.df = self._load_data()

    @classmethod
    def load_products_catalog(cls, products_excel_path: Optional[Path] = None) -> pd.DataFrame:
        """Loads the product catalog from the Excel workbook in the work folder."""
        default_path = Path(__file__).resolve().parent.parent / "work" / "produtos.xlsx"
        path = Path(products_excel_path) if products_excel_path else default_path

        if not path.exists():
            logger.warning("Catálogo de produtos não encontrado em %s. Indicadores financeiros serão limitados.", path)
            return pd.DataFrame(columns=["Código", "PU de entrada", "PU de saída"])

        try:
            df = pd.read_excel(path, engine="openpyxl")
        except Exception as exc:  # pragma: no cover - defensive logging
            logger.error("Erro ao carregar catálogo de produtos em %s: %s", path, exc)
            return pd.DataFrame(columns=["Código", "PU de entrada", "PU de saída"])

        if df.empty:
            return pd.DataFrame(columns=["Código", "PU de entrada", "PU de saída"])

        df = df.copy()
        df["Código"] = df["Código"].astype(str).str.strip().str.upper()
        for col in ["PU de entrada", "PU de saída"]:
            if col in df.columns:
                df[col] = pd.to_numeric(df[col], errors="coerce").fillna(0.0)
            else:
                df[col] = 0.0
        return df

    @staticmethod
    def _coerce_customer_key(df: pd.DataFrame) -> pd.Series:
        """Builds a usable customer identifier from the available columns."""
        if df.empty:
            return pd.Series(dtype="object")

        if "Cliente" in df.columns:
            values = df["Cliente"]
        elif "Nome do Cliente" in df.columns:
            values = df["Nome do Cliente"]
        elif "CEP" in df.columns:
            values = df["CEP"]
        elif "Pedido ID" in df.columns:
            values = df["Pedido ID"]
        else:
            values = pd.Series(["N/A"] * len(df), index=df.index)

        return values.astype(str).str.strip().replace({"": "N/A"}).fillna("N/A")

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
        df["Representante"] = df["Representante"].astype(str).str.strip()

        return df

    @staticmethod
    def _normalize_status(status: Any) -> str:
        if status is None:
            return ""

        text = str(status).strip().upper()
        text = unicodedata.normalize("NFKD", text)
        text = "".join(ch for ch in text if unicodedata.category(ch) != "Mn")
        return text

    def get_filtered_data(
        self,
        status_filter: str = "Todos",
        search_product: str = "",
        date_start: Optional[Any] = None,
        date_end: Optional[Any] = None,
        representative: Optional[str] = None,
        customer: Optional[str] = None,
        region: Optional[str] = None,
    ) -> pd.DataFrame:
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
            filtered_df = filtered_df[filtered_df["Código do Produto"].astype(str).str.contains(search_product, case=False, na=False)]

        # Date filters
        if date_start is not None or date_end is not None:
            date_col = self._find_date_column(filtered_df)
            if date_col and date_col in filtered_df.columns:
                filtered_df[date_col] = pd.to_datetime(filtered_df[date_col], errors="coerce")
                mask = pd.Series(True, index=filtered_df.index)
                if date_start is not None:
                    mask &= filtered_df[date_col] >= pd.Timestamp(date_start)
                if date_end is not None:
                    mask &= filtered_df[date_col] <= pd.Timestamp(date_end)
                filtered_df = filtered_df.loc[mask]

        if representative not in {None, "", "Todos"} and "Representante" in filtered_df.columns:
            filtered_df = filtered_df[filtered_df["Representante"].astype(str).str.strip() == representative]

        if customer not in {None, "", "Todos"}:
            customer_key = self._coerce_customer_key(filtered_df)
            filtered_df = filtered_df[customer_key.astype(str).str.contains(customer, case=False, na=False)]

        if region not in {None, "", "Todos"} and "UF" in filtered_df.columns:
            filtered_df = filtered_df[filtered_df["UF"].astype(str).str.strip().str.upper() == region.upper()]

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
    def _get_variable_cost_percentage(origin: Optional[str]) -> float:
        """Returns the variable cost percentage based on the product origin."""
        if origin is None:
            return float(os.getenv("CUSTO_VARIAVEL_NACIONAL", "0.2615"))

        normalized_origin = str(origin).strip().lower()
        if "estrangeira" in normalized_origin or "import" in normalized_origin:
            if "mercado interno" in normalized_origin or "mercado nacional" in normalized_origin or "adquirida" in normalized_origin:
                return float(os.getenv("CUSTO_VARIAVEL_NACIONAL", "0.2615"))
            return float(os.getenv("CUSTO_VARIAVEL_IMPORTADO", "0.2015"))

        return float(os.getenv("CUSTO_VARIAVEL_NACIONAL", "0.2615"))

    def build_profitability_dataset(self, df: pd.DataFrame) -> pd.DataFrame:
        """Builds a profitability dataset by joining sales rows to the product catalog."""
        if df.empty:
            return pd.DataFrame(columns=[
                "Código do Produto",
                "Descrição do Produto",
                "Quantidade",
                "Faturamento",
                "Custo Total",
                "Lucro Bruto",
                "Margem Bruta (%)",
                "Representante",
                "Cliente",
                "UF",
            ])

        sales_df = df.copy()
        sales_df["Quantidade"] = pd.to_numeric(sales_df["Quantidade"], errors="coerce").fillna(0.0)
        sales_df["Código do Produto"] = sales_df["Código do Produto"].astype(str).str.strip().str.upper()
        sales_df["Cliente"] = self._coerce_customer_key(sales_df)
        sales_df["Representante"] = (
            sales_df.get("Representante", pd.Series(["N/A"] * len(sales_df), index=sales_df.index))
            .astype(str)
            .str.strip()
            .replace({"": "N/A"})
            .fillna("N/A")
        )
        sales_df["UF"] = (
            sales_df.get("UF", pd.Series(["N/A"] * len(sales_df), index=sales_df.index))
            .astype(str)
            .str.strip()
            .str.upper()
            .replace({"": "N/A"})
            .fillna("N/A")
        )

        products_df = self.products_df.copy() if not self.products_df.empty else pd.DataFrame(columns=["Código", "Descrição", "PU de entrada", "PU de saída", "Origem"])
        if not products_df.empty:
            products_df["Código"] = products_df["Código"].astype(str).str.strip().str.upper()
            products_df["Descrição"] = products_df.get("Descrição", pd.Series(["N/A"] * len(products_df), index=products_df.index)).astype(str)
            for col in ["PU de entrada", "PU de saída"]:
                if col in products_df.columns:
                    products_df[col] = pd.to_numeric(products_df[col], errors="coerce").fillna(0.0)
            if "Origem" in products_df.columns:
                products_df["Origem"] = products_df["Origem"].astype(str).fillna("")
            else:
                products_df["Origem"] = ""
        else:
            products_df = pd.DataFrame({"Código": [], "Descrição": [], "PU de entrada": [], "PU de saída": [], "Origem": []})

        profitability = sales_df.merge(
            products_df[["Código", "Descrição", "PU de entrada", "PU de saída", "Origem"]].rename(columns={"Código": "Código do Produto", "Descrição": "Descrição do Produto"}),
            on="Código do Produto",
            how="left",
        )

        profitability["Preço de Entrada"] = pd.to_numeric(profitability.get("PU de entrada", 0.0), errors="coerce").fillna(0.0)
        profitability["Preço de Venda"] = pd.to_numeric(profitability.get("PU de saída", 0.0), errors="coerce").fillna(0.0)
        profitability["Origem"] = profitability.get("Origem", "").astype(str).fillna("")
        profitability["Faturamento"] = profitability["Preço de Venda"] * profitability["Quantidade"]
        profitability["Custo Variável (%)"] = profitability["Origem"].apply(self._get_variable_cost_percentage)
        profitability["Custo Total"] = (profitability["Preço de Entrada"] * profitability["Quantidade"]) + (
            profitability["Faturamento"] * profitability["Custo Variável (%)"]
        )
        profitability["Lucro Bruto"] = profitability["Faturamento"] - profitability["Custo Total"]
        profitability["Margem Bruta (%)"] = pd.Series(0.0, index=profitability.index)
        non_zero = profitability["Faturamento"] > 0
        profitability.loc[non_zero, "Margem Bruta (%)"] = (profitability.loc[non_zero, "Lucro Bruto"] / profitability.loc[non_zero, "Faturamento"] * 100)
        profitability["Descrição do Produto"] = profitability["Descrição do Produto"].fillna("N/A")
        default_rep = os.getenv("NOME_PADRAO_REPRESENTANTE", "").strip()
        if not default_rep or default_rep.upper() in {"N/A", "NA", "NONE", "NULL", "<NA>"}:
            default_rep = "Sem Representante"

        profitability["Representante"] = profitability["Representante"].astype(str).str.strip()
        missing_rep_mask = profitability["Representante"].isin(["", "N/A", "NA", "None", "none", "nan", "NaN", "<NA>"])
        profitability.loc[missing_rep_mask, "Representante"] = default_rep
        profitability["Representante"] = profitability["Representante"].replace({"": default_rep}).fillna(default_rep)
        profitability["UF"] = profitability["UF"].astype(str).str.strip().str.upper().replace({"": "N/A"}).fillna("N/A")
        return profitability

    def calculate_financial_kpis(self, profitability_df: pd.DataFrame) -> Dict[str, Any]:
        """Calculates the main financial KPIs from a profitability dataset."""
        if profitability_df.empty:
            return {
                "revenue_total": 0.0,
                "gross_profit_total": 0.0,
                "gross_margin_avg": 0.0,
                "top_product": "N/A",
                "top_representative": "N/A",
                "top_customer": "N/A",
            }

        gross_profit_total = float(profitability_df["Lucro Bruto"].sum())
        revenue_total = float(profitability_df["Faturamento"].sum())
        gross_margin_avg = (gross_profit_total / revenue_total * 100) if revenue_total > 0 else 0.0

        product_summary = (
            profitability_df.groupby("Código do Produto", dropna=False, as_index=False)
            .agg(Faturamento=("Faturamento", "sum"), Lucro_Bruto=("Lucro Bruto", "sum"))
            .sort_values("Lucro_Bruto", ascending=False)
        )
        top_product = product_summary.iloc[0]["Código do Produto"] if not product_summary.empty else "N/A"

        rep_summary = (
            profitability_df.groupby("Representante", dropna=False, as_index=False)
            .agg(Lucro_Bruto=("Lucro Bruto", "sum"))
            .sort_values("Lucro_Bruto", ascending=False)
        )
        top_representative = rep_summary.iloc[0]["Representante"] if not rep_summary.empty else "N/A"

        customer_summary = (
            profitability_df.groupby("Cliente", dropna=False, as_index=False)
            .agg(Lucro_Bruto=("Lucro Bruto", "sum"))
            .sort_values("Lucro_Bruto", ascending=False)
        )
        top_customer = customer_summary.iloc[0]["Cliente"] if not customer_summary.empty else "N/A"

        return {
            "revenue_total": revenue_total,
            "gross_profit_total": gross_profit_total,
            "gross_margin_avg": gross_margin_avg,
            "top_product": top_product,
            "top_representative": top_representative,
            "top_customer": top_customer,
        }

    def get_profitability_by_product(self, profitability_df: pd.DataFrame) -> pd.DataFrame:
        """Aggregates profitability by product."""
        if profitability_df.empty:
            return pd.DataFrame(columns=["Código do Produto", "Descrição do Produto", "Faturamento", "Lucro Bruto", "Margem Bruta (%)", "Quantidade", "Participação no Lucro (%)", "Participação no Faturamento (%)"])

        summary = (
            profitability_df.groupby(["Código do Produto", "Descrição do Produto"], dropna=False, as_index=False)
            .agg(
                Quantidade=("Quantidade", "sum"),
                Faturamento=("Faturamento", "sum"),
                Lucro_Bruto=("Lucro Bruto", "sum"),
                Custo_Total=("Custo Total", "sum"),
            )
        )
        summary = summary.rename(columns={"Lucro_Bruto": "Lucro Bruto"})
        summary["Margem Bruta (%)"] = pd.Series(0.0, index=summary.index)
        non_zero = summary["Faturamento"] > 0
        summary.loc[non_zero, "Margem Bruta (%)"] = (summary.loc[non_zero, "Lucro Bruto"] / summary.loc[non_zero, "Faturamento"] * 100)
        total_profit = summary["Lucro Bruto"].sum()
        total_revenue = summary["Faturamento"].sum()
        summary["Participação no Lucro (%)"] = (summary["Lucro Bruto"] / total_profit * 100) if total_profit > 0 else 0.0
        summary["Participação no Faturamento (%)"] = (summary["Faturamento"] / total_revenue * 100) if total_revenue > 0 else 0.0
        return summary.sort_values("Lucro Bruto", ascending=False).reset_index(drop=True)

    def get_profitability_by_representative(self, profitability_df: pd.DataFrame) -> pd.DataFrame:
        """Aggregates profitability by representative."""
        if profitability_df.empty:
            return pd.DataFrame(columns=["Representante", "Faturamento", "Lucro Bruto", "Margem Bruta (%)"])

        summary = (
            profitability_df.groupby("Representante", dropna=False, as_index=False)
            .agg(Faturamento=("Faturamento", "sum"), Lucro_Bruto=("Lucro Bruto", "sum"))
        )
        summary = summary.rename(columns={"Lucro_Bruto": "Lucro Bruto"})
        summary["Margem Bruta (%)"] = pd.Series(0.0, index=summary.index)
        non_zero = summary["Faturamento"] > 0
        summary.loc[non_zero, "Margem Bruta (%)"] = (summary.loc[non_zero, "Lucro Bruto"] / summary.loc[non_zero, "Faturamento"] * 100)
        return summary.sort_values("Lucro Bruto", ascending=False).reset_index(drop=True)

    def get_profitability_by_customer(self, profitability_df: pd.DataFrame) -> pd.DataFrame:
        """Aggregates profitability by customer."""
        if profitability_df.empty:
            return pd.DataFrame(columns=["Cliente", "Faturamento", "Lucro Bruto", "Margem Bruta (%)"])

        summary = (
            profitability_df.groupby("Cliente", dropna=False, as_index=False)
            .agg(Faturamento=("Faturamento", "sum"), Lucro_Bruto=("Lucro Bruto", "sum"))
        )
        summary = summary.rename(columns={"Lucro_Bruto": "Lucro Bruto"})
        summary["Margem Bruta (%)"] = pd.Series(0.0, index=summary.index)
        non_zero = summary["Faturamento"] > 0
        summary.loc[non_zero, "Margem Bruta (%)"] = (summary.loc[non_zero, "Lucro Bruto"] / summary.loc[non_zero, "Faturamento"] * 100)
        return summary.sort_values("Lucro Bruto", ascending=False).reset_index(drop=True)

    def get_monthly_profitability(self, profitability_df: pd.DataFrame) -> pd.DataFrame:
        """Builds monthly profitability evolution using the available date column."""
        if profitability_df.empty:
            return pd.DataFrame(columns=["Mês", "Faturamento", "Lucro Bruto", "Margem Bruta (%)"])

        monthly_df = profitability_df.copy()
        date_col = self._find_date_column(monthly_df)
        if date_col and date_col in monthly_df.columns:
            monthly_df[date_col] = pd.to_datetime(monthly_df[date_col], errors="coerce")
            monthly_df = monthly_df[monthly_df[date_col].notna()]
            if monthly_df.empty:
                monthly_df["Mês"] = pd.Timestamp.today().to_period("M").to_timestamp()
            else:
                monthly_df["Mês"] = monthly_df[date_col].dt.to_period("M").dt.to_timestamp()
        else:
            monthly_df["Mês"] = pd.Timestamp.today().to_period("M").to_timestamp()

        monthly = (
            monthly_df.groupby("Mês", dropna=False, as_index=False)
            .agg(Faturamento=("Faturamento", "sum"), Lucro_Bruto=("Lucro Bruto", "sum"))
        )
        monthly = monthly.rename(columns={"Lucro_Bruto": "Lucro Bruto"})
        monthly["Margem Bruta (%)"] = pd.Series(0.0, index=monthly.index)
        non_zero = monthly["Faturamento"] > 0
        monthly.loc[non_zero, "Margem Bruta (%)"] = (monthly.loc[non_zero, "Lucro Bruto"] / monthly.loc[non_zero, "Faturamento"] * 100)
        return monthly.sort_values("Mês").reset_index(drop=True)

    @staticmethod
    def get_abc_analysis(df: pd.DataFrame, value_col: str) -> Tuple[pd.DataFrame, Dict[str, Any]]:
        """Performs an ABC classification on a profitability table using a numeric value column."""
        if df.empty:
            return pd.DataFrame(), {"A": 0, "B": 0, "C": 0}

        abc_df = df.copy()
        abc_df = abc_df.sort_values(by=value_col, ascending=False).reset_index(drop=True)
        total_value = abc_df[value_col].sum()
        abc_df["Participação (%)"] = (abc_df[value_col] / total_value * 100) if total_value > 0 else 0.0
        abc_df["Acumulado (%)"] = abc_df["Participação (%)"].cumsum()

        classes = []
        for value in abc_df["Acumulado (%)"]:
            if value <= 80.0:
                classes.append("A")
            elif value <= 95.0:
                classes.append("B")
            else:
                classes.append("C")
        abc_df["Classe ABC"] = classes
        class_counts = abc_df["Classe ABC"].value_counts().to_dict()
        for key in ["A", "B", "C"]:
            class_counts.setdefault(key, 0)
        return abc_df, class_counts

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
        if "Representante" not in normalized.columns:
            normalized["Representante"] = "N/A"

        summary = normalized.groupby(["Pedido ID", "Número do Pedido"], dropna=False, as_index=False).agg(
            CEP=("CEP", "first"),
            UF=("UF", lambda values: next((v for v in values if v not in {"", "N/A"}), "N/A")),
            Cidade=("Cidade", lambda values: next((v for v in values if v not in {"", "N/A"}), "N/A")),
            Valor_Total=("Valor Total", "first"),
            Status_da_Nota_Fiscal=("Status da Nota Fiscal", "first"),
            Representante=("Representante", "first")
        )
        summary["Valor_Total"] = pd.to_numeric(summary["Valor_Total"], errors="coerce").fillna(0.0)
        return summary

    @staticmethod
    def _find_date_column(df: pd.DataFrame) -> str | None:
        if df.empty:
            return None

        candidates = [col for col in df.columns if "data" in col.lower() or "date" in col.lower()]
        for col in candidates:
            if pd.api.types.is_datetime64_any_dtype(df[col]):
                return col
            parsed = pd.to_datetime(df[col], errors="coerce")
            if parsed.notna().any():
                return col
        return None

    @staticmethod
    def _client_identifier(df: pd.DataFrame) -> pd.Series:
        if "CEP" in df.columns and df["CEP"].notna().any():
            return df["CEP"].astype(str).str.strip().replace({"": "N/A"})
        if "Cliente" in df.columns and df["Cliente"].notna().any():
            return df["Cliente"].astype(str).str.strip().replace({"": "N/A"})
        return df["Pedido ID"].astype(str)

    @staticmethod
    def _ensure_representante_column(df: pd.DataFrame) -> pd.DataFrame:
        """Ensure the `Representante` column exists and non-empty values are set.

        If the column is missing or values are empty/na, fill with 'Leonardo'.
        """
        default_rep = os.getenv("NOME_PADRAO_REPRESENTANTE", "Leonardo")
        if df is None or df.empty:
            return df

        df = df.copy()
        if "Representante" not in df.columns:
            df["Representante"] = default_rep
            return df

        # Normalize strings and replace empty/na with default
        df["Representante"] = df["Representante"].astype(str).str.strip()
        df.loc[df["Representante"].isna(), "Representante"] = ""
        df.loc[df["Representante"] == "", "Representante"] = default_rep
        return df

    @staticmethod
    def get_representative_sales_summary(df: pd.DataFrame) -> pd.DataFrame:
        if df is None or df.empty:
            return pd.DataFrame()

        df = SalesAnalytics._ensure_representante_column(df)
        df = df.copy()
        if "Valor Total" in df.columns:
            df["Valor Total"] = pd.to_numeric(df["Valor Total"], errors="coerce").fillna(0.0)
        else:
            df["Valor Total"] = 0.0
        df["Cliente_Chave"] = SalesAnalytics._client_identifier(df)

        order_levels = (
            df.groupby(["Pedido ID", "Representante"], dropna=False, as_index=False)
            .agg(
                Valor_Total=("Valor Total", "first"),
                Cliente_Chave=("Cliente_Chave", "first"),
                Código_do_Produto=("Código do Produto", lambda values: values.nunique()),
            )
        )

        summary = (
            order_levels.groupby("Representante", dropna=False, as_index=False)
            .agg(
                Receita_Total=("Valor_Total", "sum"),
                Pedidos=("Pedido ID", "count"),
                Clientes_Unicos=("Cliente_Chave", lambda values: values.nunique()),
                Produtos_Distintos=("Código_do_Produto", "sum"),
            )
        )
        summary["Ticket_Medio"] = summary.apply(
            lambda row: row["Receita_Total"] / row["Pedidos"] if row["Pedidos"] > 0 else 0.0,
            axis=1
        )
        summary["Pedidos_por_Cliente"] = summary.apply(
            lambda row: row["Pedidos"] / row["Clientes_Unicos"] if row["Clientes_Unicos"] > 0 else 0.0,
            axis=1
        )
        total_revenue = summary["Receita_Total"].sum()
        summary["Participacao (%)"] = summary.apply(
            lambda row: row["Receita_Total"] / total_revenue * 100 if total_revenue > 0 else 0.0,
            axis=1
        )
        return summary.sort_values(by="Receita_Total", ascending=False).reset_index(drop=True)

    @staticmethod
    def get_representative_repurchase_rate(df: pd.DataFrame) -> pd.DataFrame:
        if df is None or df.empty:
            return pd.DataFrame()

        df = SalesAnalytics._ensure_representante_column(df)
        df = df.copy()
        df["Cliente_Chave"] = SalesAnalytics._client_identifier(df)

        client_orders = (
            df.groupby(["Representante", "Cliente_Chave"], dropna=False)["Pedido ID"]
            .nunique()
            .reset_index(name="Orders_per_Client")
        )
        summary = (
            client_orders.groupby("Representante", dropna=False, as_index=False)
            .agg(
                Clientes_Recorrentes=("Orders_per_Client", lambda values: (values > 1).sum()),
                Clientes_Total=("Orders_per_Client", "count")
            )
        )
        summary["Recompra (%)"] = summary.apply(
            lambda row: row["Clientes_Recorrentes"] / row["Clientes_Total"] * 100 if row["Clientes_Total"] > 0 else 0.0,
            axis=1
        )
        return summary

    @staticmethod
    def get_representative_monthly_evolution(df: pd.DataFrame) -> pd.DataFrame:
        date_col = SalesAnalytics._find_date_column(df)
        if df is None or df.empty or date_col is None:
            return pd.DataFrame()

        df = SalesAnalytics._ensure_representante_column(df)
        df = df.copy()
        df[date_col] = pd.to_datetime(df[date_col], errors="coerce")
        df = df[df[date_col].notna()]
        if df.empty:
            return pd.DataFrame()

        df["Mes"] = df[date_col].dt.to_period("M").dt.to_timestamp()
        orders = SalesAnalytics._build_order_summary(df)
        if orders.empty or "Representante" not in orders.columns:
            return pd.DataFrame()

        result = (
            orders.groupby(["Representante", "Mes"], dropna=False, as_index=False)
            .agg(Receita_Total=("Valor_Total", "sum"))
            .sort_values(["Representante", "Mes"])
        )
        return result

    @staticmethod
    def get_representative_meta(df: pd.DataFrame) -> pd.DataFrame:
        if df is None or df.empty:
            return pd.DataFrame()

        df = SalesAnalytics._ensure_representante_column(df)

        if "Meta" not in df.columns and "meta" not in df.columns:
            return pd.DataFrame()

        meta_column = "Meta" if "Meta" in df.columns else "meta"
        df = df.copy()
        df[meta_column] = pd.to_numeric(df[meta_column], errors="coerce").fillna(0.0)
        summary = (
            df.groupby("Representante", dropna=False, as_index=False)
            .agg(Meta_Valor=(meta_column, "sum"))
        )
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
