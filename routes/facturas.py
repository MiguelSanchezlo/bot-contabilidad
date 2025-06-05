from flask import Blueprint, render_template, send_file, request, jsonify
from services.facturas_service import get_facturas_completas
from services.dataico_uploader import subir_facturas_a_dataico
from services.dataico_downloader import fetch_and_transform
from services.contapyme_exporter import export_contapyme_to_xlsx
from openpyxl.cell.cell import ILLEGAL_CHARACTERS_RE
import pandas as pd
import io
import json
from datetime import date, datetime

facturas_completo_bp = Blueprint("facturas", __name__, template_folder="../templates")

def split_name(full_name):
    parts = full_name.strip().split()
    if len(parts) == 0:
        return "", ""
    elif len(parts) == 1:
        return parts[0], ""
    elif len(parts) == 2:
        return parts[0], parts[1]
    else:
        return " ".join(parts[:-2]), " ".join(parts[-2:])
    

@facturas_completo_bp.route("/facturas/dataico", methods=["POST"])
def api_traer_dataico():
    nums = request.get_json(silent=True) or {}
    numeros = nums.get("numeros", [])
    print("🔍 /facturas/dataico recibió números:", numeros)

    if not numeros:
        return jsonify({"success": False, "message": "No se enviaron números."}), 400

    try:
        items = fetch_and_transform(numeros)
        return jsonify({"success": True, "items": items})
    except Exception as e:
        print("❌ Error al traer de Dataico:", e, type(e))
        return jsonify({"success": False, "message": str(e)}), 500


@facturas_completo_bp.route("/facturas")
def mostrar_facturas():
    fecha_inicio = request.args.get("inicio")
    fecha_fin    = request.args.get("fin")
    hoy = datetime.today().date()

    if not fecha_inicio:
        fecha_inicio = hoy.strftime("%Y-%m-%d")
    if not fecha_fin:
        fecha_fin    = hoy.strftime("%Y-%m-%d")

    productos = get_facturas_completas(desde=fecha_inicio, hasta=fecha_fin)
    for p in productos:
        p.pop("IVA_PORC", None)
    # Filtrado por rango de fechas
    productos = [
        p for p in productos
        if datetime.strptime(fecha_inicio, "%Y-%m-%d")
           <= datetime.strptime(p["FECHA_EXPEDICION"], "%d/%m/%Y")
           <= datetime.strptime(fecha_fin,    "%Y-%m-%d")
    ]

    # Split automático de nombre si faltan
    for p in productos:
        if not p["CLIENTE_PRIMER_NOMBRE"] or not p["CLIENTE_APELLIDO"]:
            fn, ln = split_name(p["CLIENTE_NOMBRE"])
            p["CLIENTE_PRIMER_NOMBRE"] = fn
            p["CLIENTE_APELLIDO"]       = ln

    # Clasificación por tipo de orden
    productos_fm = [p for p in productos if p["ORDEN_DE_COMPRA"].startswith("FM")]
    productos_fb = [p for p in productos if p["ORDEN_DE_COMPRA"].startswith("FB")]
    productos_eq = [p for p in productos if p["ORDEN_DE_COMPRA"].startswith("EQ")]

    return render_template(
        "facturas.html",
        productos_fm=productos_fm,
        productos_fb=productos_fb,
        productos_eq=productos_eq,
        fecha_inicio=fecha_inicio,
        fecha_fin=fecha_fin,
    )

@facturas_completo_bp.route("/facturas/subir", methods=["POST"])
def subir_facturas():
    try:
        data = request.get_json()
        if not data:
            return jsonify({"success": False, "message": "No se recibió data."}), 400
        
        print(json.dumps(data, indent=2))
        
        resultado = subir_facturas_a_dataico(data)
        return jsonify({"success": True, "message": f"Subidas: {resultado} facturas."})
    except Exception as e:
        return jsonify({"success": False, "message": f"Error: {str(e)}"}), 500


def _safe_str(x: str) -> str:
    return ILLEGAL_CHARACTERS_RE.sub("", x) if isinstance(x, str) else x

@facturas_completo_bp.route("/facturas/export")
def exportar_facturas():
    productos = get_facturas_completas()
    df = pd.DataFrame(productos).applymap(_safe_str)

    output = io.BytesIO()
    with pd.ExcelWriter(output, engine="openpyxl") as writer:
        df.to_excel(writer, index=False, sheet_name="Facturas")
    output.seek(0)

    return send_file(
        output,
        mimetype="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
        as_attachment=True,
        download_name="facturas_completas.xlsx",
    )

@facturas_completo_bp.route("/facturas/contapyme-export", methods=["POST"])
def api_export_contapyme():
    print("[DEBUG] Llamada a /facturas/contapyme-export recibida")

    data = request.get_json() or {}
    nums = data.get("numeros", [])
    print(f"[DEBUG] Números recibidos: {nums}")

    if not nums:
        return jsonify({"success": False, "message": "No se enviaron números."}), 400

    try:
        items = nums 
        print(f"[DEBUG] Items traídos de Dataico: {len(items)} líneas")

        buf = export_contapyme_to_xlsx(items)
            
        hoy = date.today().strftime("%Y%m%d")
        filename = f"contapyme_{hoy}.xlsx"
    
        return send_file(
            buf,
            mimetype="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
            as_attachment=True,
            download_name=filename
        )

    except Exception as e:
        print("[ERROR]", e)
        return jsonify({"success": False, "message": str(e)}), 500
