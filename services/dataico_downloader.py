import os
import requests
from config import load_dotenv

load_dotenv()

API_TOKEN  = os.getenv("DATAICO_AUTH_TOKEN")
ACCOUNT_ID = os.getenv("DATAICO_ACCOUNT_ID")
BASE_URL   = "https://api.dataico.com/direct/dataico_api/v2"
HEADERS    = {
    "Auth-token":         API_TOKEN,
    "Dataico-Account-Id":  ACCOUNT_ID,
    "Accept":             "application/json"
}


def fetch_invoices_by_number(numbers):
    invoices = []
    for num in numbers:
        try:
            resp = requests.get(
                f"{BASE_URL}/invoices",
                headers=HEADERS,
                params={"number": num}
            )
            resp.raise_for_status()
            data = resp.json()

            if "invoice" in data:
                invoices.append(data["invoice"])
            elif "invoices" in data and isinstance(data["invoices"], list):
                invoices.extend(data["invoices"])
            else:
                print(f"⚠️ No encontró invoice para {num}")

        except requests.exceptions.HTTPError as e:
            if resp.status_code == 404:
                print(f"⚠️ Factura {num} no existe en Dataico. Se omite.")
                continue
            print(f"❌ Error HTTP al consultar {num}: {e}")
        except Exception as e:
            print(f"❌ Error general con {num}: {e}")

    return invoices


def transform_invoice_to_items(inv):
    """
    Transforma un dict 'invoice' de Dataico a una lista de items planos.
    Se aseguran strings en dirección, ciudad y departamento para evitar [object Object].
    """
    customer = inv.get("customer", {})
    fecha    = inv.get("issue_date", "").split()[0]
    numero   = inv.get("number", "") or ""
    orden    = inv.get("order_reference") or numero

    # Derivar ubicación según prefijo de consecutivo
    if numero.upper().startswith("MCFE"):
        ciudad_def = "MEDELLIN"
        depto_def  = "ANTIOQUIA"
    else:
        ciudad_def = "BOGOTA, D.C."
        depto_def  = "BOGOTA"

    # Extract values and ensure they are strings
    raw_address = customer.get("address_line", "")
    address = raw_address if isinstance(raw_address, str) else ""
    raw_city = customer.get("city", "")
    city = raw_city if isinstance(raw_city, str) else ""
    raw_depto = customer.get("department", "")
    depto = raw_depto if isinstance(raw_depto, str) else ""
    correo = customer.get("email", "") if isinstance(customer.get("email"), str) else ""

    items = []
    for it in inv.get("items", []):
        iva = next(
            (t.get("tax_rate") for t in it.get("taxes", []) if t.get("tax_category") == "IVA"),
            0
        )
        items.append({
            "FECHA_EXPEDICION":     fecha,
            "FECHA_VENCIMIENTO":    fecha,
            "NUMERO":               numero,
            "ORDEN_DE_COMPRA":      orden,
            "CLIENTE_NOMBRE":       " ".join(
                filter(None, [customer.get("first_name"), customer.get("family_name")])
            ) or customer.get("company_name", ""),
            "OBSERVACIONES":        " ".join(inv.get('notes', [])),
            "CLIENTE_IDENTIFICATION": customer.get("party_identification", ""),
            "CLIENTE_TIPO_IDENTIFICATION": customer.get("party_identification_type", ""),
            "CLIENTE_DIRECCION":    address or ciudad_def,
            "CLIENTE_CIUDAD":       city or ciudad_def,
            "CLIENTE_DEPARTAMENTO": depto or depto_def,
            "CLIENTE_CORREO":       correo or "micelu.co7@gmail.com",
            "ITEM_DESCRIPCION":     it.get("description", ""),
            "ITEM_REFERENCIA":      it.get("sku", ""),
            "ITEM_CANTIDAD":        int(it.get("quantity", 1)),
            "ITEM_PRECIO":          float(it.get("price", 0)),
            "IVA%":                 iva,
        })
    return items


def fetch_and_transform(numbers):
    """
    Conveniencia: trae facturas por 'number' y devuelve todos los items listos para front o contapyme.
    """
    invs = fetch_invoices_by_number(numbers)
    all_items = []
    for inv in invs:
        all_items.extend(transform_invoice_to_items(inv))
    return all_items

