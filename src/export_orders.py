"""
Módulo Extrator e Consolidador de Vendas a partir de fontes de dados Excel.
Lê os arquivos de vendas da All Drive (Mainô e Histórico Gerensys), mapeia códigos
de produtos, normaliza dados fiscais e geográficos, e gera a planilha 'work/pedidos_confirmados.xlsx'.

Compatível com Python 3.11+.
"""

import ctypes
import io
import logging
import os
import re
import sys
import time
from pathlib import Path
from typing import Any, Dict, List, Optional

import pandas as pd
from openpyxl import Workbook
from dotenv import load_dotenv

# Ensure import paths work regardless of execution location
ROOT_DIR = Path(__file__).resolve().parent
if str(ROOT_DIR) not in sys.path:
    sys.path.insert(0, str(ROOT_DIR))

from utils.geo import extract_uf_from_string, map_cep_to_uf, normalize_cep, safe_float

# Logging configuration
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s - %(levelname)s - %(message)s",
    handlers=[logging.StreamHandler(sys.stdout)]
)
logger = logging.getLogger("export_orders")

load_dotenv()

WORK_DIR = Path(__file__).resolve().parent.parent / "work"
OUTPUT_FILE = WORK_DIR / "pedidos_confirmados.xlsx"
DEFAULT_REPRESENTATIVE = os.getenv("NOME_PADRAO_REPRESENTANTE", "Leonardo")


def read_excel_shared(fpath: Path | str) -> io.BytesIO:
    """
    Reads an Excel file using low-level Windows sharing flags (FILE_SHARE_READ | FILE_SHARE_WRITE | FILE_SHARE_DELETE)
    to prevent PermissionError crashes if the file is currently open in Microsoft Excel.
    """
    path_str = str(Path(fpath).resolve())
    if not os.path.exists(path_str):
        raise FileNotFoundError(f"Arquivo não encontrado: {path_str}")

    if os.name != "nt":
        # Non-Windows systems fall back to standard open
        with open(path_str, "rb") as f:
            return io.BytesIO(f.read())

    GENERIC_READ = 0x80000000
    FILE_SHARE_READ = 1
    FILE_SHARE_WRITE = 2
    FILE_SHARE_DELETE = 4
    OPEN_EXISTING = 3
    FILE_ATTRIBUTE_NORMAL = 0x80
    INVALID_HANDLE_VALUE = -1

    handle = ctypes.windll.kernel32.CreateFileW(
        path_str,
        GENERIC_READ,
        FILE_SHARE_READ | FILE_SHARE_WRITE | FILE_SHARE_DELETE,
        None,
        OPEN_EXISTING,
        FILE_ATTRIBUTE_NORMAL,
        None
    )
    if handle == INVALID_HANDLE_VALUE:
        err = ctypes.GetLastError()
        # Fallback to standard open if CreateFileW fails for any reason
        with open(path_str, "rb") as f:
            return io.BytesIO(f.read())

    buf = bytearray()
    chunk_size = 65536
    chunk = ctypes.create_string_buffer(chunk_size)
    bytes_read = ctypes.c_ulong(0)

    try:
        while True:
            res = ctypes.windll.kernel32.ReadFile(
                handle, chunk, chunk_size, ctypes.byref(bytes_read), None
            )
            if not res or bytes_read.value == 0:
                break
            buf.extend(chunk.raw[:bytes_read.value])
    finally:
        ctypes.windll.kernel32.CloseHandle(handle)

    return io.BytesIO(buf)


def load_maino_sales_files(work_dir: Path) -> List[Dict[str, Any]]:
    """
    Extracts sales order items from Mainô Excel files matching 'vendas - All Drive - Maino*.xlsx'.
    """
    pattern = re.compile(r"^vendas\s*-\s*All Drive\s*-\s*Maino.*\.xlsx$", re.IGNORECASE)
    matching_files = [f for f in os.listdir(work_dir) if pattern.match(f)]
    
    extracted_rows: List[Dict[str, Any]] = []

    if not matching_files:
        logger.warning(f"Nenhum arquivo 'vendas - All Drive - Maino*.xlsx' encontrado em {work_dir}.")
        return extracted_rows

    for fname in sorted(matching_files):
        fpath = work_dir / fname
        logger.info(f"Processando arquivo Mainô: {fname}...")
        try:
            bio = read_excel_shared(fpath)
            xl = pd.ExcelFile(bio)

            if "Relatório de Pedidos" not in xl.sheet_names or "Relatório de Produtos" not in xl.sheet_names:
                logger.warning(f"Abas requeridas não encontradas em {fname}. Abas disponíveis: {xl.sheet_names}")
                continue

            df_pedidos = pd.read_excel(xl, sheet_name="Relatório de Pedidos")
            df_produtos = pd.read_excel(xl, sheet_name="Relatório de Produtos")

            if df_pedidos.empty or df_produtos.empty:
                logger.warning(f"Planilha {fname} possui abas vazias. Pulando.")
                continue

            # Ensure join column 'Número' is string
            df_pedidos["Número"] = df_pedidos["Número"].astype(str).str.strip()
            df_produtos["Número"] = df_produtos["Número"].astype(str).str.strip()

            # Index pedidos by 'Número' for fast lookup
            pedidos_dict = df_pedidos.set_index("Número").to_dict(orient="index")

            for _, prod_row in df_produtos.iterrows():
                num_ped = str(prod_row.get("Número", "")).strip()
                ped_info = pedidos_dict.get(num_ped, {})

                prod_code = str(prod_row.get("Codigo do Produto") or prod_row.get("Código do Produto") or "").strip().upper()
                if not prod_code or prod_code in {"NAN", "NONE", ""}:
                    continue

                qty = safe_float(prod_row.get("Quantidade do Pedido") or prod_row.get("Quantidade"))
                unit_price = safe_float(prod_row.get("Preço Unitário do Produto"))
                total_price = safe_float(prod_row.get("Preço Total do Produto"))

                if total_price == 0.0 and qty > 0 and unit_price > 0:
                    total_price = qty * unit_price

                status_fiscal = str(
                    ped_info.get("Status fiscal") or prod_row.get("Status fiscal") or ""
                ).strip()

                # Fiscal values handling: 'Confirmado (sem faturamento)' -> desconsiderar valores
                if "sem faturamento" in status_fiscal.lower():
                    total_price = 0.0

                nf_num = str(
                    ped_info.get("Nota Fiscal") or prod_row.get("Nota Fiscal") or ""
                ).strip()
                if nf_num in {"nan", "None", ""}:
                    nf_num = "N/A"

                # Standardize Fiscal Status
                if "aceita" in status_fiscal.lower():
                    nf_status = "NF-e Aceita"
                elif "rejeitada" in status_fiscal.lower():
                    nf_status = "NF-e Rejeitada"
                elif "gerada" in status_fiscal.lower():
                    nf_status = "NF-e Gerada"
                elif "digitação" in status_fiscal.lower() or "digitacao" in status_fiscal.lower():
                    nf_status = "NAO EMITIDA"
                elif nf_num != "N/A" and nf_num != "001/":
                    nf_status = "NF-e Aceita"
                elif "confirmado" in status_fiscal.lower():
                    nf_status = "NF-e Aceita" if nf_num != "N/A" else "NAO EMITIDA"
                else:
                    nf_status = "NAO EMITIDA" if nf_num == "N/A" else "NF-e Aceita"

                order_status = str(
                    ped_info.get("Status do pedido") or prod_row.get("Status do pedido") or "Pedido gerado"
                ).strip()

                # Dates extraction: Data de Emissão > Data de Aprovação > Data
                date_val = ped_info.get("Data de Emissão") or ped_info.get("Data de Aprovação") or ped_info.get("Data") or prod_row.get("Data")
                parsed_date = pd.to_datetime(date_val, dayfirst=True, errors="coerce")
                date_str = parsed_date.strftime("%Y-%m-%d") if pd.notna(parsed_date) else "N/A"

                client_name = str(ped_info.get("Cliente") or prod_row.get("Cliente") or "N/A").strip()
                uf = extract_uf_from_string(client_name)

                rep = str(ped_info.get("Representante") or prod_row.get("Representante") or DEFAULT_REPRESENTATIVE).strip()
                if not rep or rep in {"nan", "None", "N/A"}:
                    rep = DEFAULT_REPRESENTATIVE

                extracted_rows.append({
                    "Pedido ID": f"MAIN-{num_ped}",
                    "Número do Pedido": num_ped,
                    "Código do Produto": prod_code,
                    "Quantidade": qty,
                    "ID da Nota Fiscal": nf_num,
                    "Status da Nota Fiscal": nf_status,
                    "Status do Pedido": order_status,
                    "Data do Pedido": date_str,
                    "URL NFe": "N/A",
                    "CPF/CNPJ do Cliente": "N/A",
                    "Nome do Cliente": client_name,
                    "CEP": "N/A",
                    "UF": uf,
                    "Cidade": "N/A",
                    "Valor Total": total_price,
                    "Representante": rep,
                })

        except Exception as e:
            logger.error(f"Erro ao processar arquivo Mainô {fname}: {e}", exc_info=True)

    logger.info(f"Total de {len(extracted_rows)} itens extraídos dos arquivos Mainô.")
    return extracted_rows


def load_gerensys_history_files(work_dir: Path) -> List[Dict[str, Any]]:
    """
    Extracts sales history from Gerensys files matching '*Histórico Gerensys*.xlsx'.
    Maps old Gerensys product codes to Mainô codes using the 'Códigos' sheet mapping when available.
    Filters out 'Entrada de Mercadoria' records.
    """
    hist_files = [f for f in os.listdir(work_dir) if "Histórico Gerensys" in f and f.endswith(".xlsx")]
    extracted_rows: List[Dict[str, Any]] = []

    if not hist_files:
        logger.info(f"Nenhum arquivo histórico Gerensys encontrado em {work_dir}.")
        return extracted_rows

    for fname in sorted(hist_files):
        fpath = work_dir / fname
        logger.info(f"Processando arquivo histórico Gerensys: {fname}...")
        try:
            bio = read_excel_shared(fpath)
            xl = pd.ExcelFile(bio)

            # Build product code mapping dictionary if 'Códigos' sheet exists
            code_mapping: Dict[str, str] = {}
            if "Códigos" in xl.sheet_names:
                df_codes = pd.read_excel(xl, sheet_name="Códigos")
                if "Código Maino" in df_codes.columns and "Código Gerensys" in df_codes.columns:
                    for _, crow in df_codes.iterrows():
                        gcode = str(crow.get("Código Gerensys", "")).strip().upper()
                        mcode = str(crow.get("Código Maino", "")).strip().upper()
                        if gcode and mcode and gcode != "NAN":
                            code_mapping[gcode] = mcode

            # Primary sheet name (either 'Histórico' or first sheet)
            sheet_name = "Histórico" if "Histórico" in xl.sheet_names else xl.sheet_names[0]
            df_hist = pd.read_excel(xl, sheet_name=sheet_name)

            if df_hist.empty:
                logger.warning(f"Planilha de histórico {fname} [{sheet_name}] está vazia.")
                continue

            for _, row in df_hist.iterrows():
                tipo_mov = str(row.get("Tipo de Movimentação") or "").strip()

                # Requirement: Entrada de Mercadoria -> Desconsiderar
                if "entrada" in tipo_mov.lower():
                    continue

                g_prod_code = str(row.get("Código Produto") or "").strip().upper()
                if not g_prod_code or g_prod_code in {"NAN", "NONE", ""}:
                    continue

                # Map product code to Mainô code if available
                final_prod_code = code_mapping.get(g_prod_code, g_prod_code)

                qty = safe_float(row.get("Quantidade"))
                val_final = safe_float(row.get("Valor Final") or row.get("Valor Original"))
                nro_nota = str(row.get("Nro Nota") or row.get("Id Mov") or "").strip()
                if nro_nota in {"nan", "None", ""}:
                    nro_nota = "N/A"

                id_mov = str(row.get("Id Mov") or nro_nota).strip()

                # Fiscal status per specification:
                # Nota Fiscal 55 -> Venda com Nota Fiscal
                # Pedido de Venda -> Venda sem Nota Fiscal
                if "nota fiscal" in tipo_mov.lower():
                    nf_status = "NF-e Aceita"
                    nf_id = nro_nota
                else: # Pedido de Venda
                    nf_status = "NAO EMITIDA"
                    nf_id = "N/A"

                parsed_date = pd.to_datetime(row.get("DtEmissao"), dayfirst=True, errors="coerce")
                date_str = parsed_date.strftime("%Y-%m-%d") if pd.notna(parsed_date) else "N/A"

                doc = str(row.get("Documento") or "").strip()
                if doc in {"nan", "None", ""}:
                    doc = "N/A"

                client_name = str(row.get("Razão Social") or row.get("Cliente") or "N/A").strip()
                uf = extract_uf_from_string(client_name)

                rep = str(row.get("Vendedor") or DEFAULT_REPRESENTATIVE).strip()
                if not rep or rep in {"nan", "None", "N/A"}:
                    rep = DEFAULT_REPRESENTATIVE

                extracted_rows.append({
                    "Pedido ID": f"GER-{id_mov}",
                    "Número do Pedido": nro_nota,
                    "Código do Produto": final_prod_code,
                    "Quantidade": qty,
                    "ID da Nota Fiscal": nf_id,
                    "Status da Nota Fiscal": nf_status,
                    "Status do Pedido": "Pedido gerado",
                    "Data do Pedido": date_str,
                    "URL NFe": "N/A",
                    "CPF/CNPJ do Cliente": doc,
                    "Nome do Cliente": client_name,
                    "CEP": "N/A",
                    "UF": uf,
                    "Cidade": "N/A",
                    "Valor Total": val_final,
                    "Representante": rep,
                })

        except Exception as e:
            logger.error(f"Erro ao processar histórico Gerensys {fname}: {e}", exc_info=True)

    logger.info(f"Total de {len(extracted_rows)} itens extraídos dos históricos Gerensys.")
    return extracted_rows


def save_to_excel(rows: List[Dict[str, Any]], filepath: Path) -> None:
    """
    Saves the extracted sales order item details to an Excel file with required column ordering.
    Handles PermissionError if target Excel file is currently open.
    """
    if not rows:
        logger.warning("Nenhum dado extraído para salvar no Excel.")
        return

    # Prompt required columns first
    required_headers = [
        "Pedido ID",
        "Número do Pedido",
        "Código do Produto",
        "Quantidade",
        "ID da Nota Fiscal",
        "Status da Nota Fiscal",
    ]

    discovered_headers: List[str] = []
    for row in rows:
        for key in row.keys():
            if key not in discovered_headers:
                discovered_headers.append(key)

    headers = [h for h in required_headers if h in discovered_headers]
    headers.extend([h for h in discovered_headers if h not in headers])

    workbook = Workbook()
    sheet = workbook.active
    sheet.title = "Itens Pedidos Confirmados"

    sheet.append(headers)
    for row in rows:
        sheet.append([row.get(col) for col in headers])

    filepath.parent.mkdir(parents=True, exist_ok=True)
    
    # Save to Excel with retry and exception handling for file locks
    try:
        workbook.save(filepath)
        logger.info(f"Planilha Excel gerada com sucesso em: {filepath} ({len(rows)} linhas)")
    except PermissionError:
        logger.warning(
            f"O arquivo '{filepath.name}' está aberto em outro programa (ex: Excel). "
            f"Tentando salvar como temporário..."
        )
        temp_path = filepath.parent / f"{filepath.stem}_novo{filepath.suffix}"
        workbook.save(temp_path)
        logger.warning(
            f"Salvo em '{temp_path.name}'. Por favor, feche '{filepath.name}' para permitir a substituição automática."
        )
        try:
            os.replace(temp_path, filepath)
            logger.info(f"Substituição concluída com sucesso em: {filepath}")
        except Exception:
            logger.error(
                f"Não foi possível sobrescrever '{filepath.name}'. O resultado foi mantido em '{temp_path.name}'."
            )


def main() -> None:
    load_dotenv()
    logger.info("Iniciando extração e consolidação de dados de vendas a partir das planilhas...")

    try:
        maino_rows = load_maino_sales_files(WORK_DIR)
        gerensys_rows = load_gerensys_history_files(WORK_DIR)
        all_rows = maino_rows + gerensys_rows

        if not all_rows:
            logger.error("Nenhum dado de vendas pôde ser extraído das planilhas indicadas.")
            sys.exit(1)

        logger.info(f"Total consolidado: {len(all_rows)} itens de pedido.")
        save_to_excel(all_rows, OUTPUT_FILE)
        logger.info("Processo de extração concluído com sucesso.")
    except Exception as e:
        logger.error(f"A execução do extrator falhou: {e}", exc_info=True)
        sys.exit(1)


if __name__ == "__main__":
    main()
