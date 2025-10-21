from flask import Flask, request, jsonify
app = Flask(__name__)

@app.get("/")
def home():
    return "Proxy Sage ACTIVO"

@app.post("/sagemath")
def sagemath():
    data = request.get_json(silent=True) or request.form.to_dict() or {}
    return jsonify({"success": True, "echo": data, "note": "fase0_ok"}), 200

# ---------- FASE 1: prueba salida a internet (httpbin) ----------
def FASE_1_httpbin_impl():
    import requests
    try:
        r = requests.post("https://httpbin.org/post", json={"pong": True}, timeout=10)
        return jsonify({"success": True, "httpbin_status": r.status_code, "json": r.json()}), 200
    except Exception as e:
        return jsonify({"success": False, "stderr": f"httpbin error: {e}"}), 200

# ---------- FASE 2: llamada real a SageMathCell con diagnóstico ----------
def FASE_2_sagecell_impl():
    import requests
    data = request.get_json(silent=True) or {}
    if not data:
        data = request.form.to_dict() if request.form else {}
    codigo = (data.get("codigo") or "").strip()
    if not codigo:
        return jsonify({"success": False, "stdout": "", "stderr": "Falta 'codigo'"}), 200

    try:
        upstream = requests.post(
            "https://sagecell.sagemath.org/service",
            data={"code": codigo, "language": "sage", "timeout": 20},
            headers={"Accept": "application/json", "User-Agent": "ejecutor-sage-proxy"},
            timeout=25
        )
        diag = {
            "upstream_status": upstream.status_code,
            "upstream_ok": upstream.ok,
            "upstream_ct": upstream.headers.get("Content-Type", ""),
        }

        if upstream.status_code != 200:
            return jsonify({"success": False, "stdout": "", "stderr": f"Upstream status {upstream.status_code}",
                            "raw": upstream.text, "diag": diag}), 200

        # Intentar parsear JSON
        try:
            sj = upstream.json()
        except ValueError:
            return jsonify({"success": False, "stdout": "", "stderr": f"Respuesta no-JSON ({diag['upstream_ct']})",
                            "raw": upstream.text, "diag": diag}), 200

        stdout = sj.get("stdout", "") or ""
        stderr = sj.get("stderr", "") or ""
        files  = sj.get("files", []) if isinstance(sj.get("files", []), list) else []
        # outputs (algunas variantes)
        if (not stdout and not stderr) and isinstance(sj.get("outputs"), list):
            for item in sj["outputs"]:
                if isinstance(item, dict):
                    if "text" in item:
                        stdout += str(item["text"]) + "\n"
                    elif "data" in item and isinstance(item["data"], dict) and "text/plain" in item["data"]:
                        stdout += str(item["data"]["text/plain"]) + "\n"

        return jsonify({"success": True, "stdout": stdout, "stderr": stderr, "files": files, "diag": diag}), 200

    except Exception as e:
        return jsonify({"success": False, "stdout": "", "stderr": f"Excepción en proxy: {e.__class__.__name__}: {e}",
                        "diag": {"exception": True}}), 200


# ======= SELECCIÓN DE FASE: CAMBIA AQUÍ QUÉ FUNCIÓN SE EXPONE =======
@app.post("/sagemath")
def sagemath():
    # Cambia el 'return' a UNA de estas líneas y despliega:
    # return FASE_0_solo_echo_impl()
    # return FASE_1_httpbin_impl()
    return FASE_2_sagecell_impl()


# Arranque local (opcional)
if __name__ == "__main__":
    app.run(host="0.0.0.0", port=int(os.getenv("PORT", "8001")), debug=True)
