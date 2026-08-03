"""
Módulo Extrator e Consolidador de Vendas a partir de fontes de dados Excel.
Lê os arquivos de vendas da All Drive (Mainô e Histórico Gerensys), mapeia códigos
de produtos, normaliza dados fiscais e geográficos, e gera a planilha 'work/pedidos_confirmados.xlsx'.

Compatível com Python 3.11+.
"""

import ctypes
import io
import json
import logging
import os
import re
import sys
import time
import unicodedata
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

load_dotenv()

WORK_DIR = Path(__file__).resolve().parent.parent / "work"
OUTPUT_FILE = WORK_DIR / "pedidos_confirmados.xlsx"
QUALITY_REPORT_FILE = WORK_DIR / "pedidos_confirmados_qualidade.json"
DEFAULT_REPRESENTATIVE = os.getenv("NOME_PADRAO_REPRESENTANTE", "Leonardo")
LOG_LEVEL = os.getenv("LOG_LEVEL", "INFO").upper()
EXPECTED_COLUMNS = [
    "Pedido ID",
    "Número do Pedido",
    "Código do Produto",
    "Quantidade",
    "ID da Nota Fiscal",
    "Status da Nota Fiscal",
    "Status do Pedido",
    "Data do Pedido",
    "URL NFe",
    "CPF/CNPJ do Cliente",
    "Nome do Cliente",
    "CEP",
    "UF",
    "Cidade",
    "Valor Total",
    "Representante",
]

# Logging configuration
logging.basicConfig(
    level=getattr(logging, LOG_LEVEL, logging.INFO),
    format="%(asctime)s - %(levelname)s - %(message)s",
    handlers=[logging.StreamHandler(sys.stdout)]
)
logger = logging.getLogger("export_orders")


def _is_missing(value: Any) -> bool:
    """Returns True when value should be treated as missing in output rows."""
    if value is None:
        return True
    if isinstance(value, float) and pd.isna(value):
        return True
    text = str(value).strip()
    return text == "" or text.upper() in {"N/A", "NONE", "NAN", "<NA>"}


def _normalize_document(value: Any) -> str:
    """Normalizes CPF/CNPJ by keeping only digits."""
    if value is None:
        return ""
    return "".join(char for char in str(value) if char.isdigit())


def _normalize_name(value: Any) -> str:
    """Normalizes customer names for deterministic matching."""
    if value is None:
        return ""
    text = str(value).strip()
    text = unicodedata.normalize("NFKD", text)
    text = "".join(ch for ch in text if unicodedata.category(ch) != "Mn")
    text = re.sub(r"\s+", " ", text)
    return text.upper()


def _normalize_order_status(value: Any) -> str:
    """Normalizes order status text for consistent comparisons."""
    if value is None:
        return ""
    text = unicodedata.normalize("NFKD", str(value).strip())
    text = "".join(ch for ch in text if unicodedata.category(ch) != "Mn")
    text = re.sub(r"\s+", " ", text)
    return text.lower()


def _resolve_customer_master_path(work_dir: Path) -> Optional[Path]:
    """Resolves customer master workbook path supporting legacy typo fallback."""
    candidates = [work_dir / "clientes.xlsx", work_dir / "clientes.xmlx"]
    for candidate in candidates:
        if candidate.exists():
            return candidate
    return None


def load_customers_master(work_dir: Path) -> dict[str, dict[str, dict[str, str]]]:
    """Loads customer master and creates lookup indices by document and name."""
    customer_file = _resolve_customer_master_path(work_dir)
    if customer_file is None:
        logger.warning("Arquivo de clientes não encontrado (clientes.xlsx/clientes.xmlx).")
        return {"by_doc": {}, "by_name": {}}

    try:
        bio = read_excel_shared(customer_file)
        customers_df = pd.read_excel(bio)
    except Exception as exc:
        logger.warning("Falha ao carregar base de clientes em %s: %s", customer_file.name, exc)
        return {"by_doc": {}, "by_name": {}}

    if customers_df.empty:
        logger.warning("Base de clientes em %s está vazia.", customer_file.name)
        return {"by_doc": {}, "by_name": {}}

    by_doc: dict[str, dict[str, str]] = {}
    by_name: dict[str, dict[str, str]] = {}

    for _, row in customers_df.iterrows():
        status = str(row.get("Status") or "").strip().lower()
        if status and status not in {"ativo", "active"}:
            continue

        document_raw = row.get("CNPJ/CPF") or row.get("CPF/CNPJ") or row.get("CPF/CNPJ do Cliente")
        legal_name_raw = row.get("Razão Social") or row.get("Razao Social")
        trade_name_raw = row.get("Nome Fantasia")
        city_raw = row.get("Município") or row.get("Municipio") or row.get("Cidade")
        uf_raw = row.get("UF")
        cep_raw = row.get("CEP")
        representative_raw = row.get("Representante")

        normalized_doc = _normalize_document(document_raw)
        normalized_legal_name = _normalize_name(legal_name_raw)
        normalized_trade_name = _normalize_name(trade_name_raw)

        representative = str(representative_raw).strip() if not _is_missing(representative_raw) else DEFAULT_REPRESENTATIVE
        cep = normalize_cep(str(cep_raw)) if not _is_missing(cep_raw) else "N/A"
        uf = str(uf_raw).strip().upper() if not _is_missing(uf_raw) else "N/A"
        if uf == "N/A" and cep != "N/A":
            uf = map_cep_to_uf(cep)
        city = str(city_raw).strip() if not _is_missing(city_raw) else "N/A"
        preferred_name = str(legal_name_raw or trade_name_raw or "N/A").strip() or "N/A"

        payload = {
            "CPF/CNPJ do Cliente": str(document_raw).strip() if not _is_missing(document_raw) else "N/A",
            "Nome do Cliente": preferred_name,
            "CEP": cep,
            "UF": uf if uf else "N/A",
            "Cidade": city,
            "Representante": representative if representative else DEFAULT_REPRESENTATIVE,
        }

        if normalized_doc and normalized_doc not in by_doc:
            by_doc[normalized_doc] = payload

        if normalized_legal_name and normalized_legal_name not in by_name:
            by_name[normalized_legal_name] = payload
        if normalized_trade_name and normalized_trade_name not in by_name:
            by_name[normalized_trade_name] = payload

    logger.info(
        "Base de clientes carregada: %s documentos e %s nomes indexados.",
        len(by_doc),
        len(by_name),
    )
    return {"by_doc": by_doc, "by_name": by_name}


def enrich_rows_with_customers_master(
    rows: List[Dict[str, Any]],
    customers_index: dict[str, dict[str, dict[str, str]]],
) -> List[Dict[str, Any]]:
    """Enriches extracted rows with customer master values when fields are missing."""
    if not rows:
        return rows

    by_doc = customers_index.get("by_doc", {})
    by_name = customers_index.get("by_name", {})
    if not by_doc and not by_name:
        return rows

    enriched_count = 0
    for row in rows:
        doc_key = _normalize_document(row.get("CPF/CNPJ do Cliente"))
        name_key = _normalize_name(row.get("Nome do Cliente"))

        customer_info = None
        if doc_key:
            customer_info = by_doc.get(doc_key)
        if customer_info is None and name_key:
            customer_info = by_name.get(name_key)
        if customer_info is None:
            continue

        row_updated = False
        for field in ["CPF/CNPJ do Cliente", "Nome do Cliente", "CEP", "UF", "Cidade", "Representante"]:
            if _is_missing(row.get(field)) and not _is_missing(customer_info.get(field)):
                row[field] = customer_info[field]
                row_updated = True

        # Final fallback for UF based on CEP
        if _is_missing(row.get("UF")) and not _is_missing(row.get("CEP")):
            row["UF"] = map_cep_to_uf(str(row.get("CEP")))
            row_updated = True

        if _is_missing(row.get("Representante")):
            row["Representante"] = DEFAULT_REPRESENTATIVE
            row_updated = True

        if row_updated:
            enriched_count += 1

    logger.info("Linhas enriquecidas com base de clientes: %s", enriched_count)
    return rows


def filter_generated_orders(rows: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
    """Keeps only rows whose order status is exactly 'Pedido gerado' (normalized)."""
    if not rows:
        return rows

    filtered_rows: List[Dict[str, Any]] = []
    for row in rows:
        status = _normalize_order_status(row.get("Status do Pedido") or row.get("Status do pedido") or "")
        if status == "pedido gerado":
            filtered_rows.append(row)

    logger.info(
        "Filtro por status aplicado: %s de %s linhas mantidas com 'Pedido gerado'.",
        len(filtered_rows),
        len(rows),
    )
    return filtered_rows


def normalize_consolidated_rows(rows: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
    """Normalizes critical fields and guarantees expected output columns."""
    normalized_rows: List[Dict[str, Any]] = []

    for row in rows:
        normalized_row: Dict[str, Any] = {column: row.get(column, "N/A") for column in EXPECTED_COLUMNS}

        normalized_row["Pedido ID"] = str(normalized_row.get("Pedido ID") or "N/A").strip() or "N/A"
        normalized_row["Número do Pedido"] = str(normalized_row.get("Número do Pedido") or "N/A").strip() or "N/A"
        normalized_row["Código do Produto"] = str(normalized_row.get("Código do Produto") or "N/A").strip().upper() or "N/A"
        normalized_row["ID da Nota Fiscal"] = str(normalized_row.get("ID da Nota Fiscal") or "N/A").strip() or "N/A"
        normalized_row["Status da Nota Fiscal"] = str(normalized_row.get("Status da Nota Fiscal") or "N/A").strip() or "N/A"

        status_order_norm = _normalize_order_status(normalized_row.get("Status do Pedido"))
        normalized_row["Status do Pedido"] = "Pedido gerado" if status_order_norm == "pedido gerado" else (
            str(normalized_row.get("Status do Pedido") or "N/A").strip() or "N/A"
        )

        normalized_row["Data do Pedido"] = str(normalized_row.get("Data do Pedido") or "N/A").strip() or "N/A"
        normalized_row["URL NFe"] = str(normalized_row.get("URL NFe") or "N/A").strip() or "N/A"
        normalized_row["CPF/CNPJ do Cliente"] = str(normalized_row.get("CPF/CNPJ do Cliente") or "N/A").strip() or "N/A"
        normalized_row["Nome do Cliente"] = str(normalized_row.get("Nome do Cliente") or "N/A").strip() or "N/A"
        normalized_row["Cidade"] = str(normalized_row.get("Cidade") or "N/A").strip() or "N/A"

        normalized_row["CEP"] = normalize_cep(str(normalized_row.get("CEP") or "N/A")) if not _is_missing(normalized_row.get("CEP")) else "N/A"
        normalized_row["UF"] = str(normalized_row.get("UF") or "N/A").strip().upper() or "N/A"
        if normalized_row["UF"] == "N/A" and normalized_row["CEP"] != "N/A":
            normalized_row["UF"] = map_cep_to_uf(normalized_row["CEP"])

        normalized_row["Representante"] = str(normalized_row.get("Representante") or "").strip() or DEFAULT_REPRESENTATIVE

        normalized_row["Quantidade"] = safe_float(normalized_row.get("Quantidade"))
        normalized_row["Valor Total"] = safe_float(normalized_row.get("Valor Total"))

        normalized_rows.append(normalized_row)

    return normalized_rows


def deduplicate_rows(rows: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
    """Removes exact duplicate rows after normalization."""
    if not rows:
        return rows

    unique_rows: List[Dict[str, Any]] = []
    seen: set[tuple[Any, ...]] = set()
    for row in rows:
        row_key = tuple(row.get(column) for column in EXPECTED_COLUMNS)
        if row_key in seen:
            logger.debug("Linha duplicada removida: %s", row)
            continue
        seen.add(row_key)
        unique_rows.append(row)

    removed = len(rows) - len(unique_rows)
    if removed > 0:
        logger.info("Deduplicacao aplicada: %s linhas duplicadas removidas.", removed)
    else:
        logger.info("Deduplicacao aplicada: nenhuma linha duplicada encontrada.")
    return unique_rows


def build_quality_report(
    rows: List[Dict[str, Any]],
    raw_total: int,
    filtered_total: int,
) -> dict[str, Any]:
    """Builds basic quality metrics for the consolidated output."""
    total = len(rows)
    if total == 0:
        return {
            "raw_total": raw_total,
            "after_status_filter": filtered_total,
            "final_total": 0,
            "missing_cpf_cnpj": 0,
            "missing_customer_name": 0,
            "missing_uf": 0,
            "missing_representative": 0,
            "status_do_pedido_distribution": {},
        }

    status_distribution: dict[str, int] = {}
    for row in rows:
        status = str(row.get("Status do Pedido") or "N/A").strip() or "N/A"
        status_distribution[status] = status_distribution.get(status, 0) + 1

    def missing_count(column: str) -> int:
        return sum(1 for row in rows if _is_missing(row.get(column)))

    return {
        "raw_total": raw_total,
        "after_status_filter": filtered_total,
        "final_total": total,
        "missing_cpf_cnpj": missing_count("CPF/CNPJ do Cliente"),
        "missing_customer_name": missing_count("Nome do Cliente"),
        "missing_uf": missing_count("UF"),
        "missing_representative": missing_count("Representante"),
        "status_do_pedido_distribution": status_distribution,
    }


def save_quality_report(report: dict[str, Any], filepath: Path) -> None:
    """Persists the consolidation quality report as JSON for traceability."""
    filepath.parent.mkdir(parents=True, exist_ok=True)
    with filepath.open("w", encoding="utf-8") as handle:
        json.dump(report, handle, ensure_ascii=False, indent=2)
    logger.info("Relatorio de qualidade salvo em: %s", filepath)


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


def load_product_code_mapping(work_dir: Path) -> Dict[str, str]:
    """
    Carrega a conversão dos códigos Gerensys para os códigos Mainô.
    """
    produtos_file = work_dir / "produtos.xlsx"
    if not produtos_file.exists():
        logger.warning("Arquivo produtos.xlsx não encontrado: %s", produtos_file)
        return {}

    try:
        df = pd.read_excel(
            produtos_file,
            sheet_name="Códigos",
            engine="openpyxl"
        )
        mapping = {}

        for _, row in df.iterrows():
            gerensys_code = str(row["Código Gerensys"]).strip()
            maino_code = str(row["Código Maino"]).strip()
            if (
                gerensys_code
                and gerensys_code.lower() != "nan"
                and maino_code
                and maino_code.lower() != "nan"
            ):
                mapping[gerensys_code] = maino_code

        logger.info("Mapeamentos Gerensys -> Mainô carregados: %s", len(mapping))
        return mapping

    except Exception as exc:
        logger.error("Erro carregando conversão de códigos: %s", exc)
        return {}

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

    code_mapping = load_product_code_mapping(work_dir)

    for fname in sorted(hist_files):
        fpath = work_dir / fname
        logger.info(f"Processando arquivo histórico Gerensys: {fname}...")
        try:
            bio = read_excel_shared(fpath)
            xl = pd.ExcelFile(bio)

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
                val_final = safe_float(row.get("Valor Final") - row.get("Valor Frete", 0.0))
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
        raw_total = len(all_rows)

        all_rows = filter_generated_orders(all_rows)
        filtered_total = len(all_rows)

        customers_index = load_customers_master(WORK_DIR)
        all_rows = enrich_rows_with_customers_master(all_rows, customers_index)
        all_rows = normalize_consolidated_rows(all_rows)
        #all_rows = deduplicate_rows(all_rows)

        if not all_rows:
            logger.error("Nenhum dado de vendas pôde ser extraído das planilhas indicadas.")
            sys.exit(1)

        '''maino_rows = load_maino_sales_files(WORK_DIR)
        gerensys_rows = load_gerensys_history_files(WORK_DIR)
        logger.debug("=" * 60)
        logger.debug("RESUMO DA CONSOLIDAÇÃO")
        logger.debug("=" * 60)
        logger.debug("Linhas Mainô.............: %s", len(maino_rows))
        logger.debug("Linhas Gerensys..........: %s", len(gerensys_rows))
        all_rows = maino_rows + gerensys_rows
        logger.debug("Linhas Consolidadas......: %s", len(all_rows))
        filtered_rows = filter_generated_orders(all_rows)
        logger.debug("Após Filtro Status.......: %s", len(filtered_rows))
        normalized_rows = normalize_consolidated_rows(filtered_rows)
        logger.debug("Após Normalização........: %s", len(normalized_rows))
        #dedup_rows = deduplicate_rows(normalized_rows)
        #logger.debug("Após Deduplicação........: %s", len(dedup_rows))
        #logger.debug(
        #    "Linhas removidas.........: %s",
        #    len(all_rows) - len(dedup_rows)
        #)
        logger.debug("=" * 60)'''

        logger.info(f"Total consolidado: {len(all_rows)} itens de pedido.")
        save_to_excel(all_rows, OUTPUT_FILE)
        quality_report = build_quality_report(all_rows, raw_total=raw_total, filtered_total=filtered_total)
        save_quality_report(quality_report, QUALITY_REPORT_FILE)
        logger.info("Processo de extração concluído com sucesso.")

    except Exception as e:
        logger.error(f"A execução do extrator falhou: {e}", exc_info=True)
        sys.exit(1)


if __name__ == "__main__":
    main()
