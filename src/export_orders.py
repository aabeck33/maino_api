import logging
import os
import sys
from pathlib import Path
from typing import Any, Dict, List, Optional
from urllib.parse import parse_qs, urlparse

import requests
from requests.adapters import HTTPAdapter
from urllib3.util import Retry
from openpyxl import Workbook
from dotenv import load_dotenv

from utils.geo import find_value_by_keys, map_cep_to_uf, normalize_cep, safe_float

# Set up logging configuration
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s - %(levelname)s - %(message)s",
    handlers=[logging.StreamHandler(sys.stdout)]
)
logger = logging.getLogger("export_orders")

# Substitua este valor pelo token JWT do seu ERP Mainô.
YOUR_SECRET_TOKEN = "W_BvamRnXFPaaXaDsmxQSdE5Ak29etiQKjnozOrq3nw"

# Carrega variáveis do arquivo .env antes do uso
load_dotenv()
ORDER_STATUS_FILTER = os.getenv("MAINO_ORDER_STATUS", "Pedido gerado")

API_BASE_URL = "https://api.maino.com.br/api/v2"
OUTPUT_FILE = Path(__file__).resolve().parent.parent / "work" / "pedidos_confirmados.xlsx"


def create_session() -> requests.Session:
    """Creates a requests session configured with retries for resilience."""
    session = requests.Session()
    retry = Retry(
        total=5,
        backoff_factor=1,
        status_forcelist=(429, 500, 502, 503, 504),
        allowed_methods=("GET",),
    )
    adapter = HTTPAdapter(max_retries=retry)
    session.mount("https://", adapter)
    session.mount("http://", adapter)
    return session


def extract_next_page_number(value: Any) -> Optional[int]:
    """Parses page number from pagination next_page string or returns integer value."""
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


def fetch_invoice(session: requests.Session, order_id: str, token: str) -> Dict[str, str]:
    """
    Fetches the invoice details corresponding to a sales order.
    Returns a dict with 'id' and 'status'.
    If the invoice does not exist or gets a 404, returns 'N/A' and 'Não emitida'.
    """
    url = f"{API_BASE_URL}/pedidos/{order_id}/nota_fiscal"
    headers = {
        "Authorization": f"Bearer {token}",
        "Accept": "application/json",
    }
    try:
        logger.debug(f"Buscando nota fiscal para o pedido {order_id}...")
        response = session.get(url, headers=headers, timeout=(10, 30))
        
        # 404 explicitly indicates the invoice does not exist/was not found for this order
        if response.status_code == 404:
            return {
                "id": "N/A",
                "status": "Não emitida",
                "danfe_url": "N/A",
            }
        response.raise_for_status()
        
        data = response.json()
        nf = data.get("nota_fiscal")
        if not nf or not isinstance(nf, dict):
            return {
                "id": "N/A",
                "status": "Não emitida",
                "danfe_url": "N/A",
            }

        return {
            "id": nf.get("id") or "N/A",
            "status": nf.get("status") or "Não emitida",
            "danfe_url": nf.get("danfe_url") or "N/A",
        }
    except requests.exceptions.HTTPError as e:
        if e.response is not None and e.response.status_code == 404:
            return {
                "id": "N/A",
                "status": "Não emitida",
                "danfe_url": "N/A",
            }
        logger.error(f"Erro HTTP ao buscar nota fiscal do pedido {order_id}: {e}")
        raise
    except Exception as e:
        logger.error(f"Erro inesperado ao buscar nota fiscal do pedido {order_id}: {e}")
        raise


def compute_order_total_from_parcels(order: Dict[str, Any]) -> float:
    """Sums the parcel values defined under order['cobranca']['parcelas']."""
    cobranca = order.get("cobranca") or {}
    parcelas = cobranca.get("parcelas") or []
    total = 0.0

    if isinstance(parcelas, list):
        for parcela in parcelas:
            total += safe_float(find_value_by_keys(parcela, ["valor", "valor_parcela", "amount"]))

    return total


def fetch_orders_page(session: requests.Session, page: int, token: str, status: str) -> Dict[str, Any]:
    """Fetches a page of sales orders with a given status."""
    url = f"{API_BASE_URL}/pedidos"
    headers = {
        "Authorization": f"Bearer {token}",
        "Accept": "application/json",
    }
    params = {
        #"status": status, # Esse filtro nãoestá funcionando nem mesmo no prórprio sistema.
        "page": page,
        "per_page": 100,  # Maximize entries per page to minimize API roundtrips
    }
    response = session.get(url, headers=headers, params=params, timeout=(10, 60))
    response.raise_for_status()
    return response.json()


def process_orders_and_invoices(session: requests.Session, token: str, status: str) -> List[Dict[str, Any]]:
    """Pages through the Maino API to fetch all orders with status matching `status` and their invoices."""
    page = 1
    extracted_rows: List[Dict[str, Any]] = []

    while True:
        logger.info(f"Buscando página {page} de pedidos com status '{status}'...")
        try:
            data = fetch_orders_page(session, page, token, status)
        except Exception as e:
            logger.error(f"Falha na comunicação com a API ao obter pedidos da página {page}: {e}")
            raise

        orders = data.get("pedidos") or []
        if not orders:
            logger.info("Nenhum pedido retornado nesta página. Finalizando busca.")
            break

        logger.info(f"Processando {len(orders)} pedidos na página {page}...")
        for order in orders:
            # We also check status client-side (case-insensitively) to guarantee we only extract the target status
            order_status = order.get("status") or ""
            if order_status.lower() != status.lower():
                logger.warning(
                    f"Ignorando pedido {order.get('id')} com status {order_status} (esperado: {status})."
                )
                continue

            order_id = order.get("id")
            order_number = order.get("numero")
            order_status = order.get("status")
            order_cep = normalize_cep(
                order.get("cep")
                or find_value_by_keys(order.get("cliente") or {}, ["cep"])
                or ""
            )
            order_city = str(
                find_value_by_keys(order.get("cliente") or {}, ["municipio", "municipio_ibge"])
                or ""
            ).strip() or "N/A"
            order_representative = find_value_by_keys(order.get("representante") or {}, ["nome", "name"]) or "N/A"
            order_date = order.get("data") or "N/A"
            items = order.get("itens") or []

            # If order has no items, we skip or add a row with empty items?
            # The prompt says: "Cada linha da planilha deve representar um item do pedido"
            if not items:
                logger.info(f"Pedido {order_number} (ID: {order_id}) não possui itens. Pulando.")
                continue

            # Fetch invoice details
            try:
                invoice_info = fetch_invoice(session, order_id, token)
            except Exception as e:
                logger.error(f"Erro crítico ao recuperar nota fiscal para o pedido {order_id}: {e}")
                # We raise or fallback? Since requirement says "Caso não exista... preencher N/A", but a communication error
                # represents a failure to communicate, we raise to allow retry/recovery instead of silently outputting invalid data.
                raise

            invoice_id = invoice_info["id"]
            invoice_status = invoice_info["status"]
            url_nfe = invoice_info["danfe_url"]
            order_total = compute_order_total_from_parcels(order)

            effective_cep = order_cep or "N/A"
            effective_uf = map_cep_to_uf(effective_cep)

            for item in items:
                extracted_rows.append({
                    "Pedido ID": order_id,
                    "Número do Pedido": order_number,
                    "Status do Pedido": order_status,
                    "Data do Pedido": order_date,
                    "Código do Produto": item.get("codigo"),
                    "Quantidade": item.get("quantidade"),
                    "ID da Nota Fiscal": invoice_id,
                    "Status da Nota Fiscal": invoice_status,
                    "URL NFe": url_nfe,
                    "CEP": effective_cep,
                    "UF": effective_uf,
                    "Cidade": order_city,
                    "Valor Total": order_total,
                    "Representante": order_representative,
                })

        pagination = data.get("pagination") or {}
        next_page = extract_next_page_number(pagination.get("next_page"))
        if next_page is None:
            logger.info("Não há próxima página. Finalizando busca de pedidos.")
            break

        page = next_page

    return extracted_rows


def save_to_excel(rows: List[Dict[str, Any]], filepath: Path) -> None:
    """Saves the extracted sales order item details to an Excel file."""
    headers = [
        "Pedido ID",
        "Número do Pedido",
        "Status do Pedido",
        "Data do Pedido",
        "Código do Produto",
        "Quantidade",
        "ID da Nota Fiscal",
        "Status da Nota Fiscal",
        "URL NFe",
        "CEP",
        "UF",
        "Cidade",
        "Valor Total",
        "Representante",
    ]
    
    workbook = Workbook()
    sheet = workbook.active
    sheet.title = "Itens Pedidos Confirmados"
    
    # Append header row
    sheet.append(headers)
    
    # Append data rows
    for row in rows:
        sheet.append([row.get(col) for col in headers])
        
    filepath.parent.mkdir(parents=True, exist_ok=True)
    workbook.save(filepath)
    logger.info(f"Planilha Excel gerada com sucesso em: {filepath}")


def main() -> None:
    # Load env variables from .env file if it exists
    load_dotenv()
    
    token = os.getenv("MAINO_API_TOKEN")
    if not token:
        token = YOUR_SECRET_TOKEN
    if not token:
        logger.error(
            "Token de API não encontrado. Por favor, configure a variável de ambiente 'MAINO_API_TOKEN'."
        )
        sys.exit(1)
        
    logger.info(f"Iniciando exportação de pedidos com status '{ORDER_STATUS_FILTER}'...")
    session = create_session()
    
    try:
        rows = process_orders_and_invoices(session, token, ORDER_STATUS_FILTER)
        logger.info(f"Total de {len(rows)} itens de pedido extraídos.")
        save_to_excel(rows, OUTPUT_FILE)
        logger.info("Exportação concluída com sucesso.")
    except Exception as e:
        logger.error(f"A execução falhou: {e}")
        sys.exit(1)


if __name__ == "__main__":
    main()
