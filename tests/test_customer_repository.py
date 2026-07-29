import unittest
from pathlib import Path
import sys

import pandas as pd

sys.path.insert(0, str(Path(__file__).resolve().parent.parent / "src"))

from repositories.customer_repository import CustomerRepository


class TestCustomerRepository(unittest.TestCase):
    def test_enrich_sales_handles_missing_optional_customer_columns(self):
        repository = CustomerRepository()
        repository.load_customers = lambda file_path=None: pd.DataFrame({"Cliente": ["ACME"]})

        sales_df = pd.DataFrame({
            "Pedido ID": ["1"],
            "Cliente": ["ACME"],
        })

        enriched_df = repository.enrich_sales_with_customer_master(sales_df)

        self.assertIn("customer_document_normalized", enriched_df.columns)
        self.assertIn("customer_name_normalized_master", enriched_df.columns)
        self.assertEqual(enriched_df.loc[0, "customer_name_normalized_master"], "ACME")

    def test_enrich_sales_matches_by_name_when_document_is_empty(self):
        repository = CustomerRepository()
        repository.load_customers = lambda file_path=None: pd.DataFrame({
            "CPF/CNPJ": [""],
            "Cliente": ["ACME"],
        })

        sales_df = pd.DataFrame({
            "Pedido ID": ["1"],
            "CPF/CNPJ do Cliente": [""],
            "Cliente": ["ACME"],
        })

        enriched_df = repository.enrich_sales_with_customer_master(sales_df)

        self.assertIn("customer_name_normalized_master", enriched_df.columns)
        self.assertEqual(enriched_df.loc[0, "customer_name_normalized_master"], "ACME")


if __name__ == "__main__":
    unittest.main()
