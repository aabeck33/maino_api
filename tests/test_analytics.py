import os
import unittest
import pandas as pd
import numpy as np
from pathlib import Path
import sys

# Adjust path to import from src
sys.path.insert(0, str(Path(__file__).resolve().parent.parent / "src"))

from analytics.processing import SalesAnalytics

# Build a small in-memory test DataFrame that mimics the Excel file
def make_df():
    return pd.DataFrame({
        "Pedido ID":           ["p1", "p1", "p1", "p2", "p2", "p3", "p4"],
        "Número do Pedido":    ["001", "001", "001", "002", "002", "003", "004"],
        "Código do Produto":   ["A01", "B02", "A01", "B02", "C03", "A01", "D04"],
        "Quantidade":          [10.0, 5.0, 8.0, 3.0, 2.0, 6.0, 1.0],
        "ID da Nota Fiscal":   ["nf1", "nf1", "nf1", "N/A", "N/A", "nf3", "nf4"],
        "Status da Nota Fiscal": ["ACEITA", "ACEITA", "ACEITA", "Não emitida", "Não emitida", "ACEITA", "ACEITA"],
        "Valor Total":         [1000.0, 1000.0, 1000.0, 600.0, 600.0, 200.0, 150.0],
        "CEP":                 ["13044-480", "13044-480", "13044-480", "20010-000", "20010-000", "60000-000", "99900-000"],
        "UF":                  ["SP", "SP", "SP", "RJ", "RJ", "CE", "RS"],
        "Cidade":              ["Campinas", "Campinas", "Campinas", "Rio de Janeiro", "Rio de Janeiro", "Fortaleza", "Porto Alegre"],
        "Representante":       ["Leonardo", "Leonardo", "Leonardo", "Sealtiel", "Sealtiel", "Leonardo", "Alvaro"],
    })


class TestKPIs(unittest.TestCase):
    def setUp(self):
        self.df = make_df()

    def test_total_orders(self):
        kpis = SalesAnalytics.calculate_kpis(self.df)
        self.assertEqual(kpis["total_orders"], 4)  # p1, p2, p3, p4

    def test_total_qty_sold(self):
        kpis = SalesAnalytics.calculate_kpis(self.df)
        self.assertAlmostEqual(kpis["total_qty_sold"], 35.0)

    def test_unique_products(self):
        kpis = SalesAnalytics.calculate_kpis(self.df)
        self.assertEqual(kpis["unique_products"], 4)  # A01, B02, C03, D04

    def test_orders_with_nf(self):
        kpis = SalesAnalytics.calculate_kpis(self.df)
        # p1 has ACEITA, p2 has Não emitida, p3 has ACEITA, p4 has ACEITA
        self.assertEqual(kpis["orders_with_nf"], 3)

    def test_orders_without_nf(self):
        kpis = SalesAnalytics.calculate_kpis(self.df)
        self.assertEqual(kpis["orders_without_nf"], 1)  # Only p2

    def test_nf_emission_rate(self):
        kpis = SalesAnalytics.calculate_kpis(self.df)
        self.assertAlmostEqual(kpis["nf_emission_rate"], 75.0)

    def test_empty_df(self):
        kpis = SalesAnalytics.calculate_kpis(pd.DataFrame())
        self.assertEqual(kpis["total_orders"], 0)
        self.assertEqual(kpis["nf_emission_rate"], 0.0)


class TestABCCurve(unittest.TestCase):
    def setUp(self):
        self.df = make_df()

    def test_abc_classification_returns_dataframe(self):
        df_prod, class_counts = SalesAnalytics.get_abc_pareto_analysis(self.df)
        self.assertIsInstance(df_prod, pd.DataFrame)
        self.assertFalse(df_prod.empty)

    def test_abc_columns_present(self):
        df_prod, _ = SalesAnalytics.get_abc_pareto_analysis(self.df)
        for col in ["Código do Produto", "Quantidade", "Participação (%)", "Acumulado (%)", "Classe ABC"]:
            self.assertIn(col, df_prod.columns)

    def test_abc_sorted_descending(self):
        df_prod, _ = SalesAnalytics.get_abc_pareto_analysis(self.df)
        qtys = df_prod["Quantidade"].tolist()
        self.assertEqual(qtys, sorted(qtys, reverse=True))

    def test_class_counts_keys(self):
        _, class_counts = SalesAnalytics.get_abc_pareto_analysis(self.df)
        for k in ["A", "B", "C"]:
            self.assertIn(k, class_counts)

    def test_pareto_sum_is_100(self):
        df_prod, _ = SalesAnalytics.get_abc_pareto_analysis(self.df)
        self.assertAlmostEqual(df_prod["Participação (%)"].sum(), 100.0, places=1)

    def test_empty_df(self):
        df_prod, class_counts = SalesAnalytics.get_abc_pareto_analysis(pd.DataFrame())
        self.assertTrue(df_prod.empty)
        self.assertEqual(class_counts["A"], 0)


class TestOrderStats(unittest.TestCase):
    def setUp(self):
        self.df = make_df()

    def test_stats_keys(self):
        stats, _ = SalesAnalytics.get_order_stats(self.df)
        for key in ["mean", "median", "max", "min"]:
            self.assertIn(key, stats)

    def test_max_order(self):
        stats, _ = SalesAnalytics.get_order_stats(self.df)
        # p1: 10+5+8=23, p2: 3+2=5, p3: 6, p4: 1
        self.assertAlmostEqual(stats["max"], 23.0)

    def test_min_order(self):
        stats, _ = SalesAnalytics.get_order_stats(self.df)
        self.assertAlmostEqual(stats["min"], 1.0)

    def test_largest_orders_sorted(self):
        _, largest = SalesAnalytics.get_order_stats(self.df)
        qtys = largest["Quantidade"].tolist()
        self.assertEqual(qtys, sorted(qtys, reverse=True))

    def test_empty_df(self):
        stats, largest = SalesAnalytics.get_order_stats(pd.DataFrame())
        self.assertEqual(stats["mean"], 0.0)
        self.assertTrue(largest.empty)


class TestFiltering(unittest.TestCase):
    def setUp(self):
        self.analytics = SalesAnalytics.__new__(SalesAnalytics)
        self.analytics.df = make_df()

    def test_filter_no_nf(self):
        result = self.analytics.get_filtered_data("Sem NF Emitida")
        statuses = result["Status da Nota Fiscal"].unique()
        self.assertListEqual(list(statuses), ["Não emitida"])

    def test_filter_with_nf(self):
        result = self.analytics.get_filtered_data("Com NF Emitida")
        # No "Não emitida" in results
        self.assertNotIn("Não emitida", result["Status da Nota Fiscal"].unique())

    def test_search_product(self):
        result = self.analytics.get_filtered_data(search_product="A01")
        for code in result["Código do Produto"].unique():
            self.assertIn("A01", code)

    def test_all_filter_returns_all(self):
        result = self.analytics.get_filtered_data("Todos")
        self.assertEqual(len(result), len(self.analytics.df))


class TestFinancialAnalytics(unittest.TestCase):
    def setUp(self):
        self.df = make_df()
        self.products_df = pd.DataFrame({
            "Código": ["A01", "B02", "C03", "D04"],
            "Descrição": ["Produto A", "Produto B", "Produto C", "Produto D"],
            "PU de entrada": [10.0, 20.0, 30.0, 40.0],
            "PU de saída": [20.0, 30.0, 40.0, 50.0],
        })

    def test_build_profitability_dataset(self):
        analytics = SalesAnalytics.__new__(SalesAnalytics)
        analytics.products_df = self.products_df
        analytics.df = self.df

        profitability = analytics.build_profitability_dataset(self.df)

        self.assertIn("Lucro Bruto", profitability.columns)
        self.assertIn("Margem Bruta (%)", profitability.columns)
        self.assertIn("Faturamento", profitability.columns)
        self.assertGreater(profitability["Lucro Bruto"].sum(), 0.0)
        self.assertAlmostEqual(profitability.loc[profitability["Código do Produto"] == "A01", "Lucro Bruto"].sum(), 114.48)
        self.assertAlmostEqual(
            profitability.loc[profitability["Código do Produto"] == "A01", "Margem Bruta (%)"].iloc[0],
            23.85,
            places=2,
        )

    def test_calculate_financial_kpis(self):
        analytics = SalesAnalytics.__new__(SalesAnalytics)
        analytics.products_df = self.products_df
        analytics.df = self.df

        profitability = analytics.build_profitability_dataset(self.df)
        kpis = analytics.calculate_financial_kpis(profitability)

        self.assertGreater(kpis["revenue_total"], 0.0)
        self.assertGreater(kpis["gross_profit_total"], 0.0)
        self.assertGreaterEqual(kpis["gross_margin_avg"], 0.0)
        self.assertEqual(kpis["top_product"], "A01")

    def test_build_profitability_dataset_uses_variable_costs_by_origin(self):
        analytics = SalesAnalytics.__new__(SalesAnalytics)
        analytics.products_df = pd.DataFrame({
            "Código": ["A01", "B02", "C03"],
            "Descrição": ["Produto A", "Produto B", "Produto C"],
            "PU de entrada": [10.0, 20.0, 40.0],
            "PU de saída": [20.0, 25.0, 50.0],
            "Origem": [
                "Nacional",
                "Estrangeira - Adquirida no mercado interno",
                "Estrangeira - Importacao direta",
            ],
        })
        analytics.df = pd.DataFrame({
            "Pedido ID": ["p1", "p2", "p3"],
            "Número do Pedido": ["001", "002", "003"],
            "Código do Produto": ["A01", "B02", "C03"],
            "Quantidade": [10.0, 5.0, 3.0],
            "ID da Nota Fiscal": ["nf1", "nf2", "nf3"],
            "Status da Nota Fiscal": ["ACEITA", "ACEITA", "ACEITA"],
            "CEP": ["13044-480", "13044-480", "13044-480"],
            "UF": ["SP", "SP", "SP"],
            "Cidade": ["Campinas", "Campinas", "Campinas"],
            "Representante": ["Leonardo", "Leonardo", "Leonardo"],
        })

        os.environ["CUSTO_VARIAVEL_NACIONAL"] = "0.2615"
        os.environ["CUSTO_VARIAVEL_IMPORTADO"] = "0.2015"

        profitability = analytics.build_profitability_dataset(analytics.df)

        national_cost = profitability.loc[profitability["Código do Produto"] == "A01", "Custo Total"].iloc[0]
        treated_as_national_cost = profitability.loc[profitability["Código do Produto"] == "B02", "Custo Total"].iloc[0]
        imported_cost = profitability.loc[profitability["Código do Produto"] == "C03", "Custo Total"].iloc[0]

        self.assertAlmostEqual(national_cost, 152.30)
        self.assertAlmostEqual(treated_as_national_cost, 132.6875)
        self.assertAlmostEqual(imported_cost, 150.225)

    def test_build_profitability_dataset_uses_default_representative_for_missing_values(self):
        analytics = SalesAnalytics.__new__(SalesAnalytics)
        analytics.products_df = pd.DataFrame({
            "Código": ["A01"],
            "Descrição": ["Produto A"],
            "PU de entrada": [10.0],
            "PU de saída": [20.0],
            "Origem": ["Nacional"],
        })
        analytics.df = pd.DataFrame({
            "Pedido ID": ["p1", "p2", "p3"],
            "Número do Pedido": ["001", "002", "003"],
            "Código do Produto": ["A01", "A01", "A01"],
            "Quantidade": [1.0, 1.0, 1.0],
            "ID da Nota Fiscal": ["nf1", "nf2", "nf3"],
            "Status da Nota Fiscal": ["ACEITA", "ACEITA", "ACEITA"],
            "CEP": ["13044-480", "13044-480", "13044-480"],
            "UF": ["SP", "SP", "SP"],
            "Cidade": ["Campinas", "Campinas", "Campinas"],
            "Representante": ["", "N/A", "Joana"],
        })

        os.environ["NOME_PADRAO_REPRESENTANTE"] = "Rep Padrão"

        profitability = analytics.build_profitability_dataset(analytics.df)

        self.assertEqual(profitability["Representante"].tolist(), ["Rep Padrão", "Rep Padrão", "Joana"])


class TestRepresentativeAnalytics(unittest.TestCase):
    def setUp(self):
        self.df = make_df()

    def test_representative_sales_summary(self):
        summary = SalesAnalytics.get_representative_sales_summary(self.df)
        self.assertAlmostEqual(summary.loc[summary['Representante'] == 'Leonardo', 'Receita_Total'].iloc[0], 1200.0)
        self.assertEqual(summary.loc[summary['Representante'] == 'Leonardo', 'Pedidos'].iloc[0], 2)
        self.assertEqual(summary.loc[summary['Representante'] == 'Leonardo', 'Clientes_Unicos'].iloc[0], 2)
        self.assertAlmostEqual(summary.loc[summary['Representante'] == 'Leonardo', 'Ticket_Medio'].iloc[0], 600.0)

    def test_representative_repurchase_rate(self):
        summary = SalesAnalytics.get_representative_repurchase_rate(self.df)
        self.assertGreaterEqual(summary.loc[summary['Representante'] == 'Leonardo', 'Recompra (%)'].iloc[0], 0.0)
        self.assertEqual(summary.loc[summary['Representante'] == 'Sealtiel', 'Clientes_Total'].iloc[0], 1)

    def test_representative_meta_empty(self):
        meta = SalesAnalytics.get_representative_meta(self.df)
        self.assertTrue(meta.empty)

    def test_representative_monthly_evolution_empty(self):
        monthly = SalesAnalytics.get_representative_monthly_evolution(self.df)
        self.assertTrue(monthly.empty)


class TestGeoAnalytics(unittest.TestCase):
    def setUp(self):
        self.df = pd.DataFrame({
            "Pedido ID": ["p1", "p2", "p3", "p4"],
            "Número do Pedido": ["001", "002", "003", "004"],
            "CEP": ["13044-480", "20010-000", "60000-000", "99900-000"],
            "UF": ["SP", "RJ", "CE", "RS"],
            "Cidade": ["Campinas", "Rio de Janeiro", "Fortaleza", "Porto Alegre"],
            "Valor Total": [1000.0, 500.0, 800.0, 200.0],
            "Status da Nota Fiscal": ["ACEITA", "ACEITA", "NAO_TRANSMITIDA", "ACEITA"],
        })

    def test_revenue_by_city(self):
        result = SalesAnalytics.get_revenue_by_city(self.df)
        self.assertEqual(result.iloc[0]["Cidade"], "Campinas")
        self.assertEqual(result.iloc[0]["Valor_Total"], 1000.0)
        self.assertEqual(result.iloc[0]["Clientes"], 1)

    def test_clients_by_state(self):
        result = SalesAnalytics.get_clients_by_state(self.df)
        self.assertEqual(set(result["UF"]), {"SP", "RJ", "CE", "RS"})
        self.assertEqual(result.loc[result["UF"] == "SP", "Clientes"].iloc[0], 1)

    def test_state_revenue(self):
        result = SalesAnalytics.get_state_revenue(self.df)
        self.assertEqual(result.iloc[0]["UF"], "SP")
        self.assertEqual(result.iloc[0]["Valor_Total"], 1000.0)

    def test_ticket_average(self):
        result = SalesAnalytics.get_state_ticket_average(self.df)
        self.assertAlmostEqual(result.loc[result["UF"] == "SP", "Ticket Médio"].iloc[0], 1000.0)
        self.assertAlmostEqual(result.loc[result["UF"] == "SP", "Participação Clientes (%)"].iloc[0], 25.0)

    def test_top_cities(self):
        top_revenue = SalesAnalytics.get_top_cities_by_revenue(self.df, top_n=2)
        self.assertEqual(len(top_revenue), 2)
        self.assertEqual(top_revenue.iloc[0]["Cidade"], "Campinas")

    def test_state_geo_coordinates(self):
        result = SalesAnalytics.get_state_geo_coordinates(self.df)
        self.assertIn("Latitude", result.columns)
        self.assertIn("Longitude", result.columns)
        self.assertGreater(len(result), 0)


if __name__ == "__main__":
    unittest.main()
