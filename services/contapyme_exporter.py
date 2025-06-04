import io
import pandas as pd
from datetime import datetime

ACCOUNTS = {
    'venta_exenta': '413504',
    'venta_normal': '413502',
    'cloud': '41359515',
    'asistencia': '41359514',
    'adicionales': '413502',
    'retoma': '413598',
    'admin_iva': '24080119',
    'retenido': '13559003',
    'retenedor': '23659003',
    'total': '13050501',
    'retoma_ingreso': '28150501',
}

RETENTION_RATE = 0.0055

def generate_contapyme_entries(items):
    movimientos = []
    agrupado = {}

    # Agrupar items por número de factura
    for item in items:
        num = item.get("NUMERO", "").strip().upper()
        agrupado.setdefault(num, []).append(item)

    for numero, group in agrupado.items():
        # Derivar ciudad y MVTO según prefijo del número
        if numero.startswith("MCFE"):
            mvto = 1
        else:
            mvto = 2

        tercero = group[0].get("CLIENTE_IDENTIFICATION", "0")
        fecha = group[0].get("FECHA_EXPEDICION", datetime.today().strftime("%d/%m/%Y"))

        subtotal = 0
        iva_total = 0
        total_4135 = 0

        for item in group:
            desc = (item.get("ITEM_DESCRIPCION") or "").upper()
            precio = round(float(item.get("ITEM_PRECIO", 0)), 2)
            cantidad = int(item.get("ITEM_CANTIDAD", 1))
            iva = float(item.get("IVA%", 0))
            valor_total = precio * cantidad

            # Asignar cuenta contable
            if "ADMIN" in desc:
                cuenta = ACCOUNTS['admin_iva']
            elif "CLOUD" in desc:
                cuenta = ACCOUNTS['cloud']
            elif "ASISTENCIA" in desc:
                cuenta = ACCOUNTS['asistencia']
            elif "CABLE" in desc or "EMPAQUE" in desc:
                cuenta = ACCOUNTS['adicionales']
            elif iva == 0:
                cuenta = ACCOUNTS['venta_exenta'] if valor_total >= 1095000 else ACCOUNTS['retoma']
            else:
                cuenta = ACCOUNTS['venta_normal']

            # Venta e IVA
            if iva == 19:
                neto = precio
                iva_valor = round(neto * 0.19, 2)
                subtotal += neto
                iva_total += iva_valor
                total_4135 += valor_total

                # Venta neta
                movimientos.append({
                    "Cuenta": cuenta,
                    "MVTO": mvto,
                    "NUMERO": numero,
                    "Débito": 0,
                    "Crédito": neto,
                    "Base": "",
                    "Transacción": tercero,
                    "Tercero": "",
                    "Fecha pago": fecha,
                    "Referencia": numero
                })
                # IVA 19%
                movimientos.append({
                    "Cuenta": ACCOUNTS['admin_iva'],
                    "MVTO": mvto,
                    "NUMERO": numero,
                    "Débito": 0,
                    "Crédito": iva_valor,
                    "Base": neto,
                    "Transacción": tercero,
                    "Tercero": "",
                    "Fecha pago": fecha,
                    "Referencia": numero
                })
            else:
                subtotal += valor_total
                if cuenta.startswith('4135'):
                    total_4135 += valor_total

                movimientos.append({
                    "Cuenta": cuenta,
                    "MVTO": mvto,
                    "NUMERO": numero,
                    "Débito": 0,
                    "Crédito": round(valor_total, 2),
                    "Base": "",
                    "Transacción": tercero,
                    "Tercero": "",
                    "Fecha pago": fecha,
                    "Referencia": numero
                })

        # Retenciones sobre total_4135
        retencion = round(total_4135 * RETENTION_RATE, 2)
        base_retencion = round(retencion / RETENTION_RATE, 2)
        movimientos.append({
            "Cuenta": ACCOUNTS['retenido'],
            "MVTO": mvto,
            "NUMERO": numero,
            "Débito": retencion,
            "Crédito": 0,
            "Base": base_retencion,
            "Transacción": tercero,
            "Tercero": "",
            "Fecha pago": fecha,
            "Referencia": numero
        })
        movimientos.append({
            "Cuenta": ACCOUNTS['retenedor'],
            "MVTO": mvto,
            "NUMERO": numero,
            "Débito": 0,
            "Crédito": retencion,
            "Base": base_retencion,
            "Transacción": tercero,
            "Tercero": "",
            "Fecha pago": fecha,
            "Referencia": numero
        })

        # Total factura
        total_factura = round(subtotal + iva_total, 2)
        movimientos.append({
            "Cuenta": ACCOUNTS['total'],
            "MVTO": mvto,
            "NUMERO": numero,
            "Débito": total_factura,
            "Crédito": 0,
            "Base": "",
            "Transacción": tercero,
            "Tercero": "",
            "Fecha pago": fecha,
            "Referencia": numero
        })

    return pd.DataFrame(movimientos)


def export_contapyme_to_xlsx(items):
    df = generate_contapyme_entries(items)
    # separar por MVTO: 1 = Medellín, 2 = Bogotá
    df_med = df[df['MVTO'] == 1]
    df_bog = df[df['MVTO'] == 2]
    output = io.BytesIO()
    with pd.ExcelWriter(output, engine="openpyxl") as writer:
        df_med.to_excel(writer, index=False, sheet_name="Medellin")
        df_bog.to_excel(writer, index=False, sheet_name="Bogota")
    output.seek(0)
    return output
