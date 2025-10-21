from flask import Flask, request, Response

app = Flask(__name__)

@app.get("/embed")
def embed():
    code = request.args.get("code", "factor(2025)")
    auto = request.args.get("autoeval", "1")
    auto_js = "true" if str(auto).lower() in ("1","true","yes") else "false"

    html = f"""<!doctype html>
<html lang="es">
<head>
  <meta charset="utf-8" />
  <meta name="viewport" content="width=device-width,initial-scale=1" />
  <title>Sage embebido</title>
  <script src="https://sagecell.sagemath.org/static/embedded_sagecell.js"></script>
  <style>
    html,body {{ margin:0; height:100%; }}
    body {{ font-family: sans-serif; }}
    .bar {{ padding:8px; background:#f1f1f1; border-bottom:1px solid #ddd; }}
    #cell {{ min-height: calc(100vh - 40px); padding:8px; }}
  </style>
</head>
<body>
  <div class="bar">Sage embebido — autoeval={auto_js}</div>
  <div id="cell"></div>

  <script>
    (function () {{
      // Lee ?code=... si viene; si no, usa el valor del servidor
      function getParam(name) {{
        var m = location.search.match(new RegExp('[?&]'+name+'=([^&]+)'));
        return m ? decodeURIComponent(m[1].replace(/\\+/g, ' ')) : '';
      }}
      var initial = getParam('code') || {code!r};  // <- code inyectado por Flask
      var autoeval = {auto_js};

      // Crea la celda y (opcionalmente) la ejecuta
      sagecell.makeSagecell({{
        inputLocation: '#cell',
        template: sagecell.templates.minimal,
        evalButtonText: 'Ejecutar',
        autoeval: autoeval,
        code: initial,
        hide: ['permalink']
      }});
    }})();
  </script>
</body>
</html>"""
    return Response(html, mimetype="text/html")
