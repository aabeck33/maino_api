import unittest
from unittest.mock import MagicMock, patch
from pathlib import Path
import tempfile

import requests
from openpyxl import load_workbook

# Adjust path to import from src
import sys
sys.path.insert(0, str(Path(__file__).resolve().parent.parent / "src"))

from export_orders import (
    extract_next_page_number,
    fetch_invoice,
    process_orders_and_invoices,
    save_to_excel,
)


class TestExportOrders(unittest.TestCase):

    def test_extract_next_page_number(self):
        # Test case: next_page is None
        self.assertIsNone(extract_next_page_number(None))
        
        # Test case: next_page is int
        self.assertEqual(extract_next_page_number(5), 5)
        
        # Test case: next_page is clean digit string
        self.assertEqual(extract_next_page_number("3"), 3)
        
        # Test case: next_page is a URL path
        self.assertEqual(extract_next_page_number("/pedidos?page=2"), 2)
        self.assertEqual(extract_next_page_number("/pedidos?status=CONFIRMADO&page=45&per_page=100"), 45)
        self.assertEqual(extract_next_page_number("/pedidos?page[]=7"), 7)
        
        # Test case: next_page is invalid string
        self.assertIsNone(extract_next_page_number("not-a-number"))
        self.assertIsNone(extract_next_page_number("/pedidos?page=abc"))

    @patch("requests.Session")
    def test_fetch_invoice_success(self, mock_session):
        mock_response = MagicMock()
        mock_response.status_code = 200
        mock_response.json.return_value = {
            "nota_fiscal": {
                "id": "nf-123",
                "status": "ACEITA"
            }
        }
        mock_session.get.return_value = mock_response
        
        res = fetch_invoice(mock_session, "order-abc", "dummy-token")
        self.assertEqual(res["id"], "nf-123")
        self.assertEqual(res["status"], "ACEITA")

    @patch("requests.Session")
    def test_fetch_invoice_not_found_404(self, mock_session):
        # Simulating 404 response
        mock_response = MagicMock()
        mock_response.status_code = 404
        # We want raise_for_status to raise HTTPError
        http_error = requests.exceptions.HTTPError(response=mock_response)
        mock_response.raise_for_status.side_effect = http_error
        
        # We also mock Session.get to return this response
        mock_session.get.return_value = mock_response
        
        res = fetch_invoice(mock_session, "order-abc", "dummy-token")
        self.assertEqual(res["id"], "N/A")
        self.assertEqual(res["status"], "Não emitida")

    @patch("requests.Session")
    def test_fetch_invoice_missing_invoice_data(self, mock_session):
        mock_response = MagicMock()
        mock_response.status_code = 200
        mock_response.json.return_value = {"nota_fiscal": None}
        mock_session.get.return_value = mock_response
        
        res = fetch_invoice(mock_session, "order-abc", "dummy-token")
        self.assertEqual(res["id"], "N/A")
        self.assertEqual(res["status"], "Não emitida")

    @patch("requests.Session")
    @patch("export_orders.fetch_invoice")
    def test_process_orders_and_invoices(self, mock_fetch_invoice, mock_session):
        # Setup mocks for orders pages
        # Page 1
        page1_response = {
            "pedidos": [
                {
                    "id": "order-1",
                    "numero": "PED-001",
                    "status": "CONFIRMADO",
                    "itens": [
                        {"codigo": "P01", "quantidade": 10},
                        {"codigo": "P02", "quantidade": 5}
                    ]
                },
                {
                    "id": "order-2",
                    "numero": "PED-002",
                    "status": "RASCUNHO",  # Should be skipped because it is not CONFIRMADO
                    "itens": [{"codigo": "P03", "quantidade": 1}]
                }
            ],
            "pagination": {
                "next_page": "/pedidos?page=2"
            }
        }
        
        # Page 2
        page2_response = {
            "pedidos": [
                {
                    "id": "order-3",
                    "numero": "PED-003",
                    "status": "CONFIRMADO",
                    "itens": [{"codigo": "P04", "quantidade": 2}]
                }
            ],
            "pagination": {
                "next_page": None
            }
        }
        
        # Mock Session to return page1 and page2
        mock_session.get.side_effect = [
            MagicMock(status_code=200, json=lambda: page1_response),
            MagicMock(status_code=200, json=lambda: page2_response)
        ]
        
        # Mock fetch_invoice response: order-1 has invoice, order-3 has none (N/A)
        mock_fetch_invoice.side_effect = [
            {"id": "nf-1", "status": "ACEITA"},
            {"id": "N/A", "status": "Não emitida"}
        ]
        
        rows = process_orders_and_invoices(mock_session, "dummy-token", "CONFIRMADO")
        
        # Total rows expected: 2 from order-1, 0 from order-2 (skipped), 1 from order-3 = 3 rows
        self.assertEqual(len(rows), 3)
        
        # Assert rows content
        self.assertEqual(rows[0]["Pedido ID"], "order-1")
        self.assertEqual(rows[0]["Código do Produto"], "P01")
        self.assertEqual(rows[0]["Quantidade"], 10)
        self.assertEqual(rows[0]["ID da Nota Fiscal"], "nf-1")
        self.assertEqual(rows[0]["Status da Nota Fiscal"], "ACEITA")
        
        self.assertEqual(rows[1]["Pedido ID"], "order-1")
        self.assertEqual(rows[1]["Código do Produto"], "P02")
        
        self.assertEqual(rows[2]["Pedido ID"], "order-3")
        self.assertEqual(rows[2]["Código do Produto"], "P04")
        self.assertEqual(rows[2]["ID da Nota Fiscal"], "N/A")
        self.assertEqual(rows[2]["Status da Nota Fiscal"], "Não emitida")

    def test_save_to_excel(self):
        rows = [
            {
                "Pedido ID": "order-1",
                "Número do Pedido": "PED-001",
                "Código do Produto": "PROD-A",
                "Quantidade": 5,
                "ID da Nota Fiscal": "nf-1",
                "Status da Nota Fiscal": "ACEITA"
            },
            {
                "Pedido ID": "order-2",
                "Número do Pedido": "PED-002",
                "Código do Produto": "PROD-B",
                "Quantidade": 2,
                "ID da Nota Fiscal": "N/A",
                "Status da Nota Fiscal": "Não emitida"
            }
        ]
        
        with tempfile.TemporaryDirectory() as tmpdir:
            file_path = Path(tmpdir) / "test_out.xlsx"
            save_to_excel(rows, file_path)
            
            # Read file back to verify content
            self.assertTrue(file_path.exists())
            wb = load_workbook(file_path)
            sheet = wb.active
            self.assertEqual(sheet.title, "Itens Pedidos Confirmados")
            
            # Check headers
            headers = [cell.value for cell in sheet[1]]
            self.assertEqual(headers, [
                "Pedido ID",
                "Número do Pedido",
                "Código do Produto",
                "Quantidade",
                "ID da Nota Fiscal",
                "Status da Nota Fiscal"
            ])
            
            # Check row 1
            row1 = [cell.value for cell in sheet[2]]
            self.assertEqual(row1, ["order-1", "PED-001", "PROD-A", 5, "nf-1", "ACEITA"])
            
            # Check row 2
            row2 = [cell.value for cell in sheet[3]]
            self.assertEqual(row2, ["order-2", "PED-002", "PROD-B", 2, "N/A", "Não emitida"])


if __name__ == "__main__":
    unittest.main()
