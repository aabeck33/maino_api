import unittest
from pathlib import Path
import tempfile
import openpyxl

import sys
sys.path.insert(0, str(Path(__file__).resolve().parent.parent / "src"))

from export_orders import (
    load_maino_sales_files,
    load_gerensys_history_files,
    save_to_excel,
)


class TestExportOrders(unittest.TestCase):

    def test_save_to_excel(self):
        rows = [
            {
                "Pedido ID": "MAIN-35",
                "Número do Pedido": "35",
                "Código do Produto": "ALL1107",
                "Quantidade": 1.0,
                "ID da Nota Fiscal": "001/",
                "Status da Nota Fiscal": "NF-e Aceita",
                "Status do Pedido": "Pedido gerado",
                "Data do Pedido": "2026-05-25",
                "Valor Total": 700.0,
                "Representante": "Sealtiel Cunha"
            },
            {
                "Pedido ID": "GER-523",
                "Número do Pedido": "523",
                "Código do Produto": "ALL1021",
                "Quantidade": 3.0,
                "ID da Nota Fiscal": "523",
                "Status da Nota Fiscal": "NF-e Aceita",
                "Status do Pedido": "Pedido gerado",
                "Data do Pedido": "2024-10-11",
                "Valor Total": 2227.8,
                "Representante": "FERNANDA"
            }
        ]
        
        with tempfile.TemporaryDirectory() as tmpdir:
            file_path = Path(tmpdir) / "pedidos_confirmados.xlsx"
            save_to_excel(rows, file_path)
            
            # Verify file creation and content
            self.assertTrue(file_path.exists())
            wb = openpyxl.load_workbook(file_path)
            sheet = wb.active
            self.assertEqual(sheet.title, "Itens Pedidos Confirmados")
            
            headers = [cell.value for cell in sheet[1]]
            # Check prompt required first 6 columns order
            self.assertEqual(headers[:6], [
                "Pedido ID",
                "Número do Pedido",
                "Código do Produto",
                "Quantidade",
                "ID da Nota Fiscal",
                "Status da Nota Fiscal"
            ])
            
            row1 = [cell.value for cell in sheet[2]]
            self.assertEqual(row1[:6], ["MAIN-35", "35", "ALL1107", 1.0, "001/", "NF-e Aceita"])

    def test_load_sales_from_work_dir(self):
        work_dir = Path(__file__).resolve().parent.parent / "work"
        if work_dir.exists():
            maino_rows = load_maino_sales_files(work_dir)
            self.assertIsInstance(maino_rows, list)

            gerensys_rows = load_gerensys_history_files(work_dir)
            self.assertIsInstance(gerensys_rows, list)


if __name__ == "__main__":
    unittest.main()
