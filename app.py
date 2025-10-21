@app.post("/sagemath")
def sagemath():
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
            headers={"Accept": "application/json"},   # 👈 pedimos JSON explícitamente
            timeout=25
        )

        diag = {
            "upstream_status": upstream.status_code,
            "upstream_ok": upstream.ok,
            "upstream_ct": upstream.headers.get("Content-Type", ""),
        }

        # Si no es 200, devolvemos diagnóstico y el cuerpo crudo
        if upstream.status_code != 200:
            return jsonify({
                "success": False,
                "stdout": "",
                "stderr": f"Upstream status {upstream.status_code}",
                "raw": upstream.text,
                "diag": diag
            }), 200

        # Intentar JSON; si falla, devolvemos crudo con diag
        try:
            sj = upstream.json()
        except ValueError as e:
            return jsonify({
                "success": False,
                "stdout": "",
                "stderr": f"Respuesta no-JSON de SageCell ({diag['upstream_ct']})",
                "raw": upstream.text,
                "diag": diag
            }), 200

        stdout = sj.get("stdout", "") or ""
        stderr = sj.get("stderr", "") or ""
        files  = sj.get("files", []) if isinstance(sj.get("files", []), list) else []

        # Algunas variantes devuelven 'outputs'
        if (not stdout and not stderr) and isinstance(sj.get("outputs"), list):
            for item in sj["outputs"]:
                if isinstance(item, dict):
                    if "text" in item:
                        stdout += str(item["text"]) + "\n"
                    elif "data" in item and isinstance(item["data"], dict) and "text/plain" in item["data"]:
                        stdout += str(item["data"]["text/plain"]) + "\n"

        return jsonify({"success": True, "stdout": stdout, "stderr": stderr, "files": files, "diag": diag}), 200

    except Exception as e:
        # No 502: devolvemos 200 con success:false y el error legible
        return jsonify({
            "success": False,
            "stdout": "",
            "stderr": f"Excepción en proxy: {e.__class__.__name__}: {e}",
            "diag": {"exception": True}
        }), 200
