from collections import defaultdict
import json
import os
import requests
from dotenv import load_dotenv
from datetime import datetime

load_dotenv()

API_TOKEN = os.getenv("DATAICO_AUTH_TOKEN")
ACCOUNT_ID = os.getenv("DATAICO_ACCOUNT_ID")
RESOLUTION_FM = os.getenv("DATAICO_RESOLUTION_FM")
RESOLUTION_FB = os.getenv("DATAICO_RESOLUTION_FB")

BASE_URL = "https://api.dataico.com/direct/dataico_api/v2"
HEADERS = {
    "Auth-token": API_TOKEN,
    "Dataico-Account-Id": ACCOUNT_ID,
    "Accept": "application/json",
    "Content-Type": "application/json",
}

def to_float(val):
    try:
        return round(float(str(val).replace(",", ".")), 2)
    except:
        return 0.0

def safe_str(val, default=""):
    return str(val).strip() if val and str(val).strip() else default

def descomponer_nombre(nombre_completo):
    partes = nombre_completo.strip().split()
    if len(partes) == 1:
        return partes[0], ""
    elif len(partes) == 2:
        return partes[0], partes[1]
    else:
        # Tres o más tokens: últimos dos son apellidos, el resto nombres
        nombre = " ".join(partes[:-2])
        apellido = " ".join(partes[-2:])
        return nombre, apellido

def subir_facturas_a_dataico(facturas):
    total_exitosas = 0
    for numero, group in group_by_invoice_number(facturas).items():
        tipo_factura = "FM" if group[0]["ORDEN_DE_COMPRA"].startswith("FM") else "FB"
        numero_str = str(numero)

        numero_factura_final = f"{numero_str}" if tipo_factura == "FM" else numero_str
        resolucion = RESOLUTION_FM if tipo_factura == "FM" else RESOLUTION_FB

        issue_date = group[0]["FECHA_EXPEDICION"] + " 00:00:00"
        payment_date = issue_date

        actions = {
            "send_dian": False,
            "send_email": False,
            "email": group[0]["CLIENTE_CORREO"],
        }

        party_type = safe_str(group[0]["CLIENTE_TIPO"])
        customer_data = {
            "party_identification": safe_str(group[0]["CLIENTE_IDENTIFICATION"]),
            "party_identification_type": safe_str(group[0]["CLIENTE_TIPO_IDENTIFICATION"]),
            "email": safe_str(group[0]["CLIENTE_CORREO"]),
            "address_line": safe_str(group[0]["CLIENTE_DIRECCION"]),
            "phone": safe_str(group[0]["CLIENTE_TELEFONO"]),
            "city": safe_str(group[0]["CLIENTE_CIUDAD"]),
            "department": safe_str(group[0]["CLIENTE_DEPARTAMENTO"]),
            "country_code": safe_str(group[0]["CLIENTE_PAIS"]),
            "tax_level_code": safe_str(group[0]["CLIENTE_TAX_LEVEL"]),
            "regimen": safe_str(group[0]["CLIENTE_REGIMEN"]),
            "party_type": party_type
        }

        if party_type == "PERSONA_NATURAL":
            # siempre tomamos CLIENTE_NOMBRE, no nombre_comercial
            nombre_completo = safe_str(group[0].get("CLIENTE_NOMBRE", ""))
            primer_nombre = safe_str(group[0].get("CLIENTE_PRIMER_NOMBRE"))
            apellido      = safe_str(group[0].get("CLIENTE_APELLIDO"))

            # si faltan, descomponemos
            if not primer_nombre or not apellido:
                nom, ape = descomponer_nombre(nombre_completo)
                primer_nombre = primer_nombre or nom
                apellido      = apellido      or ape

            customer_data["first_name"]  = primer_nombre
            customer_data["family_name"] = apellido
        elif party_type == "PERSONA_JURIDICA":
            customer_data["company_name"] = safe_str(group[0].get("CLIENTE_NOMBRE_COMERCIAL"))
            
        invoice = {
            "dataico_account_id": ACCOUNT_ID,
            "env": "PRODUCCION",
            "number": "".join(filter(str.isdigit, group[0]["NUMERO"])),
            "issue_date": issue_date,
            "payment_date": payment_date,
            "currency": group[0]["MONEDA"],
            "invoice_type_code": "FACTURA_VENTA",
            "payment_means_type": group[0]["TIPO_MEDIO_DE_PAGO"],
            "payment_means": group[0]["MEDIO_DE_PAGO"],
            "order_reference": group[0]["ORDEN_DE_COMPRA"],
            "numbering": {
                "prefix": "MCFE" if tipo_factura == "FM" else "",
                "resolution_number": resolucion,
                "flexible": True,
            },
            "customer": customer_data,
            "items": [],
        }

        for item in group:
            invoice_item = {
                "sku": safe_str(item["ITEM_REFERENCIA"]),
                "description": safe_str(item["ITEM_DESCRIPCION"]),
                "quantity": to_float(item["ITEM_CANTIDAD"]),
                "price": to_float(item["ITEM_PRECIO"]),
            }

            taxes = []
            for tax_key, cat in [("IVA%", "IVA"), ("IMP_CONSUMO%", "IMP_CONSUMO")]:
                rate = to_float(item.get(tax_key, 0))
                if rate:
                    base_amount = int(invoice_item["quantity"] * invoice_item["price"])
                    taxes.append({
                        "tax-category": cat,
                        "tax-rate": rate,
                        "tax-base": 100,
                        "base-amount": base_amount,
                        "tax-amount": int(base_amount * rate / 100)
                    })
            if taxes:
                invoice_item["taxes"] = taxes
            invoice["items"].append(invoice_item)

        # Enviar a Dataico
        payload = {"actions": actions, "invoice": invoice}

        try:
            response = requests.post(f"{BASE_URL}/invoices", headers=HEADERS, json=payload)
            response.raise_for_status()

            print(f"Factura {numero_factura_final} creada: {response.json().get('invoice', {}).get('number')}")
            total_exitosas += 1

        except requests.exceptions.HTTPError as http_err:
            if response.status_code == 404:
                print(f"Factura {numero_factura_final} no encontrada en Dataico. Saltando.")
                continue
            else:
                print(f"Error {response.status_code} en {numero_factura_final}: {response.text}")
        except Exception as e:
            print(f"Excepción general para {numero_factura_final}: {str(e)}")


        print(f"\n🔍 Factura {numero} - Cliente:")
        print(json.dumps(group[0], indent=2, ensure_ascii=False))
        print(">>> DEbug cliente:", primer_nombre, apellido, "— completo:", nombre_completo)


    return total_exitosas

def group_by_invoice_number(facturas):
    grouped = defaultdict(list)
    vistos = set()

    for item in facturas:
        clave = (
            item["ORDEN_DE_COMPRA"],
            item["ITEM_DESCRIPCION"].strip().upper(),
            item["ITEM_REFERENCIA"].strip().upper(),
            round(float(item["ITEM_PRECIO"]), 2),
            float(item.get("IVA%", 0))
        )

        if clave not in vistos:
            grouped[item["ORDEN_DE_COMPRA"]].append(item)
            vistos.add(clave)

    return grouped

