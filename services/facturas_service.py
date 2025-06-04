import pandas as pd
from config import execute_query
from datetime import datetime
from collections import defaultdict

UVT = 49799
UVT_22 = 22 * UVT
UVT_36 = 36 * UVT
UVT_58 = 58 * UVT


def build_cliente_from_row(row):
    (
        descripcion, codigo, valor, codlinea, iva_porcentaje, origen,
        fecha, consecutivo, tipodcto, procli, nombre, n1, n2, a1, a2,
        ciudad, depto, dir_, mail, ident, nit, pais, personanj, tel1, codgrupo
    ) = row

    if isinstance(fecha, str):
        fecha = datetime.strptime(fecha[:10], "%Y-%m-%d")
    fecha_str = fecha.strftime("%d/%m/%Y")

    ciudad_default = "MEDELLIN" if consecutivo.startswith("FM") else "BOGOTA, D.C."
    departamento_default = "ANTIOQUIA" if consecutivo.startswith("FM") else "BOGOTA"

    tel = str(tel1).strip()

    return {
        "FECHA_EXPEDICION": fecha_str,
        "FECHA_VENCIMIENTO": fecha_str,
        "NUMERO": "",
        "MEDIO_DE_PAGO": "BANK_TRANSFER",
        "TIPO_MEDIO_DE_PAGO": "DEBITO",
        "ORDEN_DE_COMPRA": consecutivo,
        "MONEDA": "COP",
        "CLIENTE_PAIS": "CO",
        "CLIENTE_NOMBRE": nombre.strip() if nombre.strip() else f"{n1 or ''} {n2 or ''} {a1 or ''} {a2 or ''}".strip(),
        "OBSERVACIONES": "",
        "CLIENTE_PRIMER_NOMBRE": f"{n1 or ''} {n2 or ''}".strip() if personanj == 1 else "",
        "CLIENTE_APELLIDO": f"{a1 or ''} {a2 or ''}".strip() if personanj == 1 else "",
        "CLIENTE_NOMBRE_COMERCIAL": nombre.strip() if nombre else "",
        "CLIENTE_IDENTIFICATION": str(nit).split("-")[0].strip(),
        "CLIENTE_TIPO_IDENTIFICATION": "CC" if ident.strip().upper() == "C" else ident.strip().upper(),
        "CLIENTE_DIRECCION": dir_.strip() if dir_ else ciudad_default,
        "CLIENTE_TELEFONO": tel if tel and tel.lower() != "nan" else "0",
        "CLIENTE_CIUDAD": ciudad_default,
        "CLIENTE_DEPARTAMENTO": departamento_default,
        "CLIENTE_TIPO": "PERSONA_NATURAL" if personanj == 1 else "PERSONA_JURIDICA",
        "CLIENTE_CORREO": mail.strip() if mail and mail.strip() else "micelu.co7@gmail.com",
        "CLIENTE_TAX_LEVEL": "NO_RESPONSABLE_DE_IVA",
        "CLIENTE_REGIMEN": "ORDINARIO",
        "IVA_PORC": iva_porcentaje,
        "CODLINEA": codlinea.strip().upper(),
        "CODGRUPO": codgrupo.strip().upper()
    }


def generar_facturas(row):
    cliente = build_cliente_from_row(row)
    descripcion = row[0]
    codigo = row[1]
    valor = round(float(row[2]), 2)
    codlinea = cliente["CODLINEA"]
    codgrupo = cliente["CODGRUPO"]

    items = []

    if codlinea == "ACCE":
        base_sin_iva = round(valor / 1.19, 2)
        item = cliente.copy()
        item.update({
            "ITEM_DESCRIPCION": descripcion,
            "ITEM_REFERENCIA": codigo,
            "ITEM_CANTIDAD": 1,
            "ITEM_PRECIO": base_sin_iva,
            "IVA%": 19,
        })
        return [item]

    if codlinea == "CEL" and codgrupo == "SEMI":
        if valor < UVT_22:
            item = cliente.copy()
            item.update({
                "ITEM_DESCRIPCION": descripcion,
                "ITEM_REFERENCIA": codigo,
                "ITEM_CANTIDAD": 1,
                "ITEM_PRECIO": round(valor, 2),
                "IVA%": 0,
            })
            items.append(item)

        elif valor <= UVT_36:
            equipo = cliente.copy()
            equipo.update({
                "ITEM_DESCRIPCION": descripcion,
                "ITEM_REFERENCIA": codigo,
                "ITEM_CANTIDAD": 1,
                "ITEM_PRECIO": round(UVT_22, 2),
                "IVA%": 0,
            })
            cloud = cliente.copy()
            cloud.update({
                "ITEM_DESCRIPCION": f"CLOUD COMPUTING / {descripcion}",
                "ITEM_REFERENCIA": "CC24",
                "ITEM_CANTIDAD": 1,
                "ITEM_PRECIO": round(valor - UVT_22, 2),
                "IVA%": 0,
            })
            items.extend([equipo, cloud])

        elif valor <= UVT_58:
            dif = valor - UVT_22 - 200_000
            equipo = cliente.copy()
            equipo.update({
                "ITEM_DESCRIPCION": descripcion,
                "ITEM_REFERENCIA": codigo,
                "ITEM_CANTIDAD": 1,
                "ITEM_PRECIO": round(UVT_22, 2),
                "IVA%": 0,
            })
            pack = cliente.copy()
            pack.update({
                "ITEM_DESCRIPCION": "CABLE, EMPAQUE Y MANTENIMIENTO",
                "ITEM_REFERENCIA": "ADICIONALES",
                "ITEM_CANTIDAD": 1,
                "ITEM_PRECIO": round(200_000 / 1.19, 2),
                "IVA%": 19,
            })
            asistencia = cliente.copy()
            asistencia.update({
                "ITEM_DESCRIPCION": "ASISTENCIA",
                "ITEM_REFERENCIA": "ASIS24",
                "ITEM_CANTIDAD": 1,
                "ITEM_PRECIO": round((dif * 0.4) / 1.19, 2),
                "IVA%": 19,
            })
            cloud = cliente.copy()
            cloud.update({
                "ITEM_DESCRIPCION": f"CLOUD COMPUTING / {descripcion}",
                "ITEM_REFERENCIA": "CC24",
                "ITEM_CANTIDAD": 1,
                "ITEM_PRECIO": round(dif * 0.6, 2),
                "IVA%": 0,
            })
            items.extend([equipo, pack, asistencia, cloud])

    elif codlinea == "CEL" and codgrupo == "NUE":
        if valor < UVT_22:
            item = cliente.copy()
            item.update({
                "ITEM_DESCRIPCION": descripcion,
                "ITEM_REFERENCIA": codigo,
                "ITEM_CANTIDAD": 1,
                "ITEM_PRECIO": round(valor, 2),
                "IVA%": 0,
            })
            items.append(item)
        elif valor <= UVT_58:
            precio_sin_iva = round(valor / 1.19, 2)
            item = cliente.copy()
            item.update({
                "ITEM_DESCRIPCION": descripcion,
                "ITEM_REFERENCIA": codigo,
                "ITEM_CANTIDAD": 1,
                "ITEM_PRECIO": precio_sin_iva,
                "IVA%": 19,
            })
            items.append(item)
    else:
        if valor < UVT_22:
            item = cliente.copy()
            item.update({
                "ITEM_DESCRIPCION": descripcion,
                "ITEM_REFERENCIA": codigo,
                "ITEM_CANTIDAD": 1,
                "ITEM_PRECIO": round(valor, 2),
                "IVA%": 0,
            })
            items.append(item)

    return items


def get_retoma_items(desde=None, hasta=None):
    """
    Genera los ítems de retoma (TIPODCTO = 'EQ'). No aplica lógica de accesorios aquí,
    porque en retoma nunca modificas IVA según CODLINEA.
    """
    condiciones_fecha = ""
    if desde and hasta:
        condiciones_fecha = (
            f"AND a.FHCOMPRA BETWEEN '{desde} 00:00:00' AND '{hasta} 23:59:59'"
        )

    query = f"""
        SELECT
            c.SERIE                     AS imei,
            c.VALOR                     AS valor_retoma,
            v.VALOR                     AS valor_venta,
            b.DESCRIPCIO                AS descripcion,
            b.CODIGO                    AS referencia,
            a.FHCOMPRA                  AS fecha_compra,
            c.TIPODCTO + c.NRODCTO      AS consecutivo
        FROM MTSERIES c

        JOIN Mvtrade a
            ON a.TIPODCTO = c.TIPODCTO
            AND a.NRODCTO  = c.NRODCTO
            AND a.ORIGEN   = 'COMPRA'

        JOIN MTSERIES v
            ON v.SERIE   = c.SERIE
            AND v.ORIGEN = 'VENTA'
            AND v.TIPODCTO IN ('FM','FB')

        JOIN MtMercia b 
            ON b.CODIGO = c.CODIGO

        JOIN MtSeries s 
            ON s.TIPODCTO = c.TIPODCTO
            AND s.NRODCTO  = c.NRODCTO

        JOIN MtProcli p 
            ON p.NIT = s.PROCLI

        WHERE
            c.ORIGEN    = 'COMPRA'
            AND c.TIPODCTO = 'EQ'
            {condiciones_fecha}
        ORDER BY
            a.FHCOMPRA DESC,
            c.NRODCTO DESC;
    """

    results = execute_query(query)
    items = []

    for row in results:
        (
            imei,
            valor_retoma,
            valor_venta,
            descripcion,
            referencia,
            fecha_compra,
            consecutivo,
        ) = row

        # Formatear fecha
        if isinstance(fecha_compra, str):
            fecha_obj = datetime.strptime(fecha_compra[:10], "%Y-%m-%d")
        else:
            fecha_obj = fecha_compra
        fecha_str = fecha_obj.strftime("%d/%m/%Y")

        # Ciudad y depto según consecutivo
        if consecutivo.startswith("FM"):
            ciudad_default = "MEDELLIN"
            departamento_default = "ANTIOQUIA"
        else:
            ciudad_default = "BOGOTA, D.C."
            departamento_default = "BOGOTA"

        # Diccionario "cliente" para retoma (no usamos build_cliente_from_row aquí)
        cliente = {
            "FECHA_EXPEDICION": fecha_str,
            "FECHA_VENCIMIENTO": fecha_str,
            "NUMERO": "",
            "MEDIO_DE_PAGO": "BANK_TRANSFER",
            "TIPO_MEDIO_DE_PAGO": "DEBITO",
            "ORDEN_DE_COMPRA": consecutivo,
            "MONEDA": "COP",
            "CLIENTE_PAIS": "CO",
            "CLIENTE_NOMBRE": "",
            "OBSERVACIONES": imei,  # IMEI del equipo de retoma
            "CLIENTE_PRIMER_NOMBRE": "",
            "CLIENTE_APELLIDO": "",
            "CLIENTE_NOMBRE_COMERCIAL": "",
            "CLIENTE_IDENTIFICATION": "",
            "CLIENTE_TIPO_IDENTIFICATION": "",
            "CLIENTE_DIRECCION": ciudad_default,
            "CLIENTE_TELEFONO": "0",
            "CLIENTE_CIUDAD": ciudad_default,
            "CLIENTE_DEPARTAMENTO": departamento_default,
            "CLIENTE_TIPO": "PERSONA_NATURAL",
            "CLIENTE_CORREO": "micelu.co7@gmail.com",
            "CLIENTE_TAX_LEVEL": "NO_RESPONSABLE_DE_IVA",
            "CLIENTE_REGIMEN": "ORDINARIO",
        }

        total = float(valor_venta)
        admin_bruto = 200_000
        admin_sin_iva = round(admin_bruto / 1.19, 2)
        cloud = round(total - admin_bruto, 2)

        # Ítem “Equipo como pago”
        item_eq = cliente.copy()
        item_eq.update(
            {
                "ITEM_DESCRIPCION": "INGRESO RECIBIDO PARA TERCEROS",
                "ITEM_REFERENCIA": referencia,
                "ITEM_CANTIDAD": 1,
                "ITEM_PRECIO": round(total, 2),
                "IVA%": 0,
            }
        )

        # Ítem “Administración”
        item_admin = cliente.copy()
        item_admin.update(
            {
                "ITEM_DESCRIPCION": "ADMINISTRACIÓN",
                "ITEM_REFERENCIA": "ADMIN",
                "ITEM_CANTIDAD": 1,
                "ITEM_PRECIO": round(admin_sin_iva, 2),
                "IVA%": 19,
            }
        )

        # Ítem “Cloud computing”
        item_cloud = cliente.copy()
        item_cloud.update(
            {
                "ITEM_DESCRIPCION": f"CLOUD COMPUTING / {descripcion}",
                "ITEM_REFERENCIA": "CC24",
                "ITEM_CANTIDAD": 1,
                "ITEM_PRECIO": cloud,
                "IVA%": 0,
            }
        )

        items.extend([item_eq, item_admin, item_cloud])

    return items


def get_facturas_completas(desde=None, hasta=None):
    condiciones_fecha = ""
    if desde and hasta:
        condiciones_fecha = (
            f"AND a.FHCOMPRA BETWEEN '{desde} 00:00:00' AND '{hasta} 23:59:59'"
        )

    query = f"""
        SELECT
            b.DESCRIPCIO, 
            b.CODIGO, 
            a.VALUNID, 
            b.CODLINEA, 
            -- Nuevo campo que indica el porcentaje de IVA según CODLINEA
            CASE 
              WHEN b.CODLINEA = 'ACCE' THEN 19 
              ELSE 0 
            END AS IVA_PORC,
            a.ORIGEN,
            a.FHCOMPRA, 
            a.TIPODCTO + a.NRODCTO AS CONSECUTIVO, 
            a.TIPODCTO,
            s.PROCLI, 
            p.NOMBRE, 
            p.NOMBRE1, 
            p.NOMBRE2, 
            p.APELLIDO1, 
            p.APELLIDO2,
            p.CDCIIU, 
            p.CODDEPTO, 
            p.DIRECCION, 
            p.EMAILFEC, 
            p.IDENTIFICA, 
            p.NIT,
            p.PAIS, 
            p.PERSONANJ, 
            p.TEL1,
            b.CODGRUPO
        FROM Mvtrade a
        JOIN MtMercia b 
          ON a.PRODUCTO = b.CODIGO
        JOIN MtSeries s 
          ON s.TIPODCTO = a.TIPODCTO 
         AND s.NRODCTO  = a.NRODCTO
        JOIN MtProcli p 
          ON p.NIT = s.PROCLI
        WHERE
            b.CODLINEA NOT IN ('0','ST','SRV')
            AND a.TIPODCTO IN ('FM','FB')
            AND a.ORIGEN = 'FAC'
            AND a.VALUNID BETWEEN 1 AND {UVT_58}
            AND p.NIT NOT IN ('0','01')
            {condiciones_fecha}
        ORDER BY a.FHCOMPRA DESC, a.NRODCTO DESC
    """

    por_consec = defaultdict(list)
    rows_vistos = set()

    for row in execute_query(query):
        # Desempaquetamos tal cual vienen las columnas
        # row[0]=DESCRIPCIO, [1]=CODIGO, [2]=VALUNID, [3]=CODLINEA, [4]=IVA_PORC,
        # [5]=ORIGEN, [6]=FHCOMPRA, [7]=CONSECUTIVO, [8]=TIPODCTO,
        # [9]=PROCLI, [10]=NOMBRE, [11]=NOMBRE1, [12]=NOMBRE2, [13]=APELLIDO1,
        # [14]=APELLIDO2, [15]=CDCIIU, [16]=CODDEPTO, [17]=DIRECCION, [18]=EMAILFEC,
        # [19]=IDENTIFICA, [20]=NIT, [21]=PAIS, [22]=PERSONANJ, [23]=TEL1
        clave = (
            row[7],  # consecutivo
            row[0].strip().upper(),  # descripción
            row[1].strip().upper(),  # código
            round(float(row[2]), 2),  # valor
        )
        if clave in rows_vistos:
            continue
        rows_vistos.add(clave)

        for item in generar_facturas(row):
            por_consec[item["ORDEN_DE_COMPRA"]].append(item)

    def num(conc):
        digits = "".join(filter(str.isdigit, conc or ""))
        return int(digits) if digits else 0

    ordenados = sorted(por_consec.items(), key=lambda x: num(x[0]), reverse=True)

    resultado = []
    for _, items in ordenados:
        resultado.extend(items)

    resultado.extend(get_retoma_items(desde, hasta))
    return agrupar_items_factura(resultado)


def agrupar_items_factura(items):
    """
    Agrupa líneas de factura idénticas (misma factura, descripción, referencia, precio e IVA),
    sumando las cantidades.
    """
    agrupados = defaultdict(lambda: dict())

    for item in items:
        clave = (
            item["ORDEN_DE_COMPRA"],
            item["ITEM_DESCRIPCION"],
            item["ITEM_REFERENCIA"],
            round(float(item["ITEM_PRECIO"]), 2),
            item["IVA%"],
        )

        if clave in agrupados:
            agrupados[clave]["ITEM_CANTIDAD"] += 1
        else:
            nuevo = item.copy()
            nuevo["ITEM_CANTIDAD"] = 1
            agrupados[clave] = nuevo

    return list(agrupados.values())
