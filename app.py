from flask import Flask, request, jsonify
import os

app = Flask(__name__)

# ---------- Salud ----------
@app.get("/")
def home():
    return "Proxy Sage ACTIVO"

# ---------- Manejador global de errores ----------
@app.errorhandler(Exception)
def _handle_err(e):
    # Nunca 500 al cliente: devolvemos 200 con diagnóstico
    return jsonify({
        "success": False,
        "stderr": f"{e.__class__.__name__}: {e}",
        "diag": {"global_handler": True}
    }), 200

# ---------- FASE 0: eco (no usa Internet) ----------
def fase0_echo():
    data = request.get_json(silent=True) or request.form.to_dict() or {}
    return jsonify({"success": True, "echo": data, "note": "fase0_ok"}), 200

# ---------- FASE 1: salida a Internet (httpbin) ----------
def fase1_httpbin():
    import requests
    r = requests.post("https://httpbin.org/post", json={"pong": True}, timeout=10)
    return jsonify({"success": True, "httpbin_status": r.status_code, "json": r.json()}), 200

# ---------- FASE 2: llamada real a SageMathCell ----------
def fase2_sage():
    import requests
    data = request.get_json(silent=True) or request.form.to_dict() or {}
    codigo = (data.get("codigo") or "").strip()
    if not codigo:
        return jsonify({"success": False, "stdout": "", "stderr": "Falta 'codigo'"}), 200

    upstream = requests.post(
        "https://sagecell.sagemath.org/service",
        data={"code": codigo, "language": "sage", "timeout": 20},
        headers={"Accept": "application/json", "User-Agent": "ejecutor-sage-proxy"},
        timeout=25
    )

    diag = {
        "upstream_status": upstream.status_code,
        "upstream_ct": upstream.headers.get("Content-Type", "")
    }

    if upstream.status_code != 200:
        return jsonify({
            "success": False,
            "stdout": "",
            "stderr": f"Upstream {upstream.status_code}",
            "raw": upstream.text,
            "diag": diag
        }), 200

    # Intentar parsear JSON
    try:
        sj = upstream.json()
    except ValueError:
        return jsonify({
            "success": False,
            "stdout": "",
            "stderr": f"No-JSON ({diag['upstream_ct']})",
            "raw": upstream.text,
            "diag": diag
        }), 200

    stdout = sj.get("stdout") or ""
    stderr = sj.get("stderr") or ""
    files  = sj.get("files") if isinstance(sj.get("files"), list) else []

    # outputs (algunas variantes)
    if (not stdout and not stderr) and isinstance(sj.get("outputs"), list):
        for it in sj["outputs"]:
            if isinstance(it, dict):
                if "text" in it: stdout += str(it["text"]) + "\n"
                elif "data" in it and isinstance(it["data"], dict) and "text/plain" in it["data"]:
                    stdout += str(it["data"]["text/plain"]) + "\n"

    return jsonify({"success": True, "stdout": stdout, "stderr": stderr, "files": files, "diag": diag}), 200

# ===== Elige QUÉ FASE expones (cambia sólo el return) =====
@app.post("/sagemath")
def sagemath():
    return fase0_echo()     # 1) primero prueba eco
    # return fase1_httpbin()  # 2) luego prueba httpbin
    # return fase2_sage()       # 3) finalmente prueba Sage

# Arranque local opcional
if __name__ == "__main__":
    app.run(host="0.0.0.0", port=int(os.getenv("PORT", "8001")), debug=True)
