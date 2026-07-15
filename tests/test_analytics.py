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


if __name__ == "__main__":
    unittest.main()
