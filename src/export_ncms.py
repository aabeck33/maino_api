import json
import logging
import os
import sys
from pathlib import Path
from typing import Any, Dict, List, Optional
from urllib.parse import parse_qs, urlparse

import requests
from requests.adapters import HTTPAdapter
from urllib3.util.retry import Retry
from openpyxl import Workbook

# Substitua este valor pelo token JWT do seu ERP Mainô.
YOUR_SECRET_TOKEN = "W_BvamRnXFPaaXaDsmxQSdE5Ak29etiQKjnozOrq3nw"

API_URL = "https://api.maino.com.br/api/v2/fiscal/ncms"
OUTPUT_FILE = Path(__file__).resolve().parent.parent / "work" / "ncms_export.xlsx"
IMPORT_TAX_FIELDS = [
    "ii_importacao",
    "ipi_importacao",
    "cofins_importacao",
    "gatt_importacao",
    "dumping_importacao",
]


# Set up logging configuration
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s - %(levelname)s - %(message)s",
    handlers=[logging.StreamHandler(sys.stdout)]
)
logger = logging.getLogger("export_orders")


def format_ncm_code(code: Any) -> str:
    code_str = str(code).strip()
    if not code_str:
        return ""
    digits = "".join(ch for ch in code_str if ch.isdigit())
    if len(digits) == 8:
        return f"{digits[:4]}.{digits[4:6]}.{digits[6:]}"
    return code_str


def flatten_item(item: Dict[str, Any]) -> Dict[str, Any]:
    flattened: Dict[str, Any] = {}
    for key, value in item.items():
        if key == "codigo":
            flattened[key] = format_ncm_code(value)
            continue
        if isinstance(value, (dict, list)):
            flattened[key] = json.dumps(value, ensure_ascii=False)
        else:
            flattened[key] = value
    return flattened


def build_headers(rows: List[Dict[str, Any]]) -> List[str]:
    if not rows:
        return ["codigo", "descricao", "categoria", *IMPORT_TAX_FIELDS]
    keys = set()
    for row in rows:
        keys.update(row.keys())
    ordered = ["codigo"] + sorted(k for k in keys if k != "codigo")
    return ordered


def create_session() -> requests.Session:
    session = requests.Session()
    retry = Retry(
        total=3,
        backoff_factor=1,
        status_forcelist=(429, 500, 502, 503, 504),
        allowed_methods=("GET",),
    )
    adapter = HTTPAdapter(max_retries=retry)
    session.mount("https://", adapter)
    session.mount("http://", adapter)
    return session


def extract_next_page_number(value: Any) -> Optional[int]:
    if value is None:
        return None

    if isinstance(value, int):
        return value

    if isinstance(value, str):
        stripped = value.strip()
        if stripped.isdigit():
            return int(stripped)

        parsed = urlparse(stripped)
        query = parse_qs(parsed.query)
        page_values = query.get("page") or query.get("page[]")
        if page_values:
            try:
                return int(page_values[0])
            except ValueError:
                return None

    return None


def fetch_page(session: requests.Session, page: int, token: str) -> Dict[str, Any]:
    headers = {
        "Authorization": f"Bearer {token}",
        "Accept": "application/json",
    }
    response = session.get(API_URL, headers=headers, params={"page": page}, timeout=(10, 60))
    response.raise_for_status()
    return response.json()


def fetch_all_ncms(token: str) -> List[Dict[str, Any]]:
    page = 1
    ncms: List[Dict[str, Any]] = []
    session = create_session()

    while True:
        logger.info(f"Buscando página {page}...")
        try:
            data = fetch_page(session, page, token)
        except Exception as e:
            logger.error(f"Falha na comunicação com a API ao obter página {page}: {e}")
            raise
        page_items = data.get("ncms") or []
        if not page_items:
            logger.info("Nenhum item retornado nesta página. Finalizando.")
            break

        logger.info(f"Página {page}: {len(page_items)} itens encontrados")
        for item in page_items:
            ncms.append(flatten_item(item))

        pagination = data.get("pagination") or {}
        next_page = extract_next_page_number(pagination.get("next_page"))
        if next_page is None:
            logger.info("Não há próxima página. Finalizando.")
            break

        page = next_page

    return ncms


def write_workbook(rows: List[Dict[str, Any]]) -> None:
    headers = build_headers(rows)
    workbook = Workbook()
    worksheet = workbook.active
    worksheet.title = "NCMs"
    worksheet.append(headers)

    for row in rows:
        worksheet.append([row.get(column) for column in headers])

    OUTPUT_FILE.parent.mkdir(parents=True, exist_ok=True)
    workbook.save(OUTPUT_FILE)


def main() -> None:
    token = os.getenv("MAINO_API_TOKEN")
    if not token:
        token = YOUR_SECRET_TOKEN
    if not token:
        logger.error(
            "Token de API não encontrado. Por favor, configure a variável de ambiente 'MAINO_API_TOKEN'."
        )
        sys.exit(1)

    logger.info("Buscando NCMs do ERP Mainô...")
    rows = fetch_all_ncms(token)
    logger.info(f"Encontrados {len(rows)} NCM(s). Gerando planilha...")
    write_workbook(rows)
    logger.info(f"Planilha salva em: {OUTPUT_FILE}")


if __name__ == "__main__":
    main()
