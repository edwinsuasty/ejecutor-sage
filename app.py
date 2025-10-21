from flask import Flask, request, jsonify
import requests

app = Flask(__name__)

@app.get("/")
def home():
    return "Proxy Sage ACTIVO"

@app.post("/sagemath")
def sagemath():
    """
    Acepta:
      - JSON: {"codigo": "factor(2025)"}
      - form-urlencoded: codigo=factor(2025)
    Devuelve:
      {
        "success": true/false,
        "stdout": "...",
        "stderr": "...",
        "files": [ { "url": "..."} ]   # si SageCell genera imágenes/archivos
      }
    """
    data = request.get_json(silent=True) or {}
    if not data:
        data = request.form.to_dict() if request.form else {}
    codigo = (data.get("codigo") or "").strip()
    if not codigo:
        return jsonify({"success": False, "stdout": "", "stderr": "Falta 'codigo'"}), 400

    try:
        # SageMathCell: mejor usar application/x-www-form-urlencoded
        upstream = requests.post(
            "https://sagecell.sagemath.org/service",
            data={"code": codigo, "language": "sage", "timeout": 20},
            timeout=25
        )

        # Intenta JSON; si no, devuelve error con crudo
        try:
            sj = upstream.json()
        except ValueError:
            return jsonify({
                "success": False,
                "stdout": "",
                "stderr": "Respuesta no-JSON de SageCell",
                "raw": upstream.text
            }), 502

        # Normalización de salida
        stdout = sj.get("stdout", "") or ""
        stderr = sj.get("stderr", "") or ""
        files  = sj.get("files", []) if isinstance(sj.get("files", []), list) else []

        # Algunos despliegues usan 'outputs' (lista). Intenta extraer texto.
        if (not stdout and not stderr) and isinstance(sj.get("outputs"), list):
            for item in sj["outputs"]:
                if isinstance(item, dict):
                    if "text" in item:
                        stdout += str(item["text"]) + "\n"
                    elif "data" in item and isinstance(item["data"], dict) and "text/plain" in item["data"]:
                        stdout += str(item["data"]["text/plain"]) + "\n"

        return jsonify({"success": True, "stdout": stdout, "stderr": stderr, "files": files})

    except Exception as e:
        return jsonify({"success": False, "stdout": "", "stderr": f"Error Sage: {e}"}), 502


# Arranque local (solo para pruebas en tu PC)
if __name__ == "__main__":
    # host=0.0.0.0 te permitirá probar desde el teléfono en la misma LAN si quieres
    app.run(host="0.0.0.0", port=8001, debug=True)
