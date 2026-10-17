"""Página web de la obra (salida/sitio/), con las mismas hojas del cuaderno de obra.

Pensada para el celular de cada trabajador: se navega con botones grandes OFICIO → PISO → TEMA, y desde cualquier
hoja se salta al mismo piso de otro oficio o al mismo tema de otro piso. Direcciones claras, por ejemplo
/albanil/primer-piso/muros/. La genera tools/cuaderno_obra.py (`make sitio`); se sube tal cual a Vercel.
"""
import html
import json
import re
import shutil
import unicodedata

OFICIOS = [  # (slug, nombre, emoji, color, sección del cuaderno)
    ("albanil", "Albañil", "🧱", "#b5472f", "A · Albañil"),
    ("plomero", "Plomero", "💧", "#1f6fb2", "B · Plomero"),
    ("gas", "Gas", "🔥", "#d9822b", "C · Gas"),
    ("electricista", "Electricista", "💡", "#c9a400", "D · Electricista"),
]
TODOS = ("todos", "Para todos", "📋", "#4a4a4a", "")
PISOS = [  # (slug, nombre, nombre en el título de la hoja)
    ("antes", "Antes de empezar", None),
    ("planta-baja", "Planta baja", "Planta baja"),
    ("primer-piso", "Primer piso", "Primer piso"),
    ("altillo", "Altillo", "Altillo"),
]
ICONOS = [  # palabra en el tema → emoji del botón (la primera que coincide)
    ("paso a paso", "✅"), ("ladrillo", "🧱"), ("bodega", "📦"), ("niveles", "📏"), ("plano del albañil", "📐"),
    ("vistas de frente", "🪟"), ("muros", "🧱"), ("puertas", "🚪"), ("techo", "🏠"), ("agua", "🚰"),
    ("desagüe", "🌧️"), ("gas", "🔥"), ("luces", "💡"), ("enchufes", "🔌"), ("tablas", "🔢"), ("medidas", "✏️"),
    ("cambió", "🆕"), ("leer", "👀"),
]


def slug(t):
    t = unicodedata.normalize("NFKD", t.lower()).encode("ascii", "ignore").decode()
    return re.sub(r"[^a-z0-9]+", "-", t).strip("-")[:60].rstrip("-")


def icono(tema):
    t = tema.lower()
    return next((e for k, e in ICONOS if k in t), "📄")


def corto(tema):
    """Nombre del botón: sin lo que va entre paréntesis y con mayúscula al empezar."""
    t = re.sub(r"\s*\((?!\d+ de \d+\)).*?\)", "", tema).strip(" —:")
    return t[:1].upper() + t[1:]


def clasificar(h):
    """(oficio, piso, tema) de una hoja del cuaderno."""
    tit = re.sub(r"<[^>]+>", "", h["titulo"])
    sec = h["seccion"]
    if sec == "✎" or not sec and "cambió" in tit:
        of = TODOS
    else:
        of = next((o for o in OFICIOS if o[4] == sec), TODOS)
    for ps, _, nom in PISOS[1:]:
        if tit.startswith(nom + " — "):
            return of, ps, tit[len(nom) + 3:]
    return of, "antes", tit


def generar(hojas, portada, estilo, version, fecha, salida, extras):
    """hojas: [{titulo, seccion, cuerpo}] en el orden del cuaderno. extras: [(titulo, archivo en salida/)] de la casa."""
    dest = salida / "sitio"
    if dest.exists():   # se borra todo menos .vercel/ (el enlace con el proyecto de Vercel)
        for x in dest.iterdir():
            if x.name != ".vercel":
                shutil.rmtree(x) if x.is_dir() else x.unlink()
    (dest / "planos").mkdir(parents=True)

    def copiar(m):
        src = m.group(2)
        if src.startswith(("http", "data:", "/")):
            return m.group(0)
        if (salida / src).exists():
            shutil.copy(salida / src, dest / "planos" / src)
        return f'{m.group(1)}"/planos/{src}"'

    def vivo(m):
        """Plano del albañil metido en la página (no como imagen): se puede tocar cada código y ver sus datos."""
        src = m.group(1)
        svg = (salida / src).read_text(encoding="utf-8")
        shutil.copy(salida / src, dest / "planos" / src)
        svg = re.sub(r"<title>[^<]*</title>", "", svg, count=1)
        return (f'<div class="plano-vivo">{svg}</div><p class="toca">👆 Toca un código (V1, P2…) para ver todos sus datos · '
                f'<a href="/planos/{src}" target="_blank">🔍 ver el plano solo, para agrandarlo</a></p>')

    def ampliable(cuerpo):
        cuerpo = re.sub(r'<img class="plano alb" src="(obra-albanil-[^"]+\.svg)">', vivo, cuerpo)
        cuerpo = re.sub(r'(src=)"([^"]+)"', copiar, cuerpo)
        # los planos se abren solos al tocarlos (en el celular se agrandan con dos dedos)
        return re.sub(r'(<img class="plano[^"]*" src="([^"]+)">)',
                      r'<a class="zoom" href="\2" target="_blank">\1<span>🔍 Tocar para ver grande</span></a>', cuerpo)

    # árbol: oficio → piso → [páginas]
    arbol = {o[0]: {p[0]: [] for p in PISOS} for o in OFICIOS + [TODOS]}
    usados = set()
    for h in hojas:
        of, ps, tema = clasificar(h)
        s = "que-cambio" if "cambió" in tema else slug(corto(tema)) or "hoja"
        while (of[0], ps, s) in usados:
            s += "-2"
        usados.add((of[0], ps, s))
        arbol[of[0]][ps].append(dict(of=of, piso=ps, tema=tema, slug=s, cuerpo=ampliable(h["cuerpo"])))
    # "Cómo leer las medidas" (la portada del cuaderno) va para todos
    arbol["todos"]["antes"].insert(0, dict(of=TODOS, piso="antes", tema="Cómo leer las medidas y qué no hacer nunca",
                                           slug="como-leer", cuerpo=portada))
    OF = {o[0]: o for o in OFICIOS + [TODOS]}
    PS = {p[0]: p for p in PISOS}

    def url(of, ps=None, tema=None):
        return "/" + "/".join(x for x in (of, ps, tema) if x) + "/"

    def pagina(ruta, titulo, migas, cuerpo, color="#333"):
        nav = '<a class="inicio" href="/">🏠 Inicio</a>' + "".join(
            f'<span class="sep">›</span><a href="{u}">{html.escape(t)}</a>' for t, u in migas)
        doc = (f'<!doctype html><html lang="es"><head><meta charset="utf-8">'
               f'<meta name="viewport" content="width=device-width, initial-scale=1">'
               f'<title>{html.escape(titulo)} · Casa</title>{estilo}{ESTILO_WEB}</head>'
               f'<body style="--c:{color}"><header><nav>{nav}</nav><span class="ver">v{version} · {fecha}</span></header>'
               f'<main>{cuerpo}</main><div id="dato" hidden></div>{SCRIPT_WEB}<footer>Casa en construcción · Cochabamba · versión {version} del {fecha}. '
               f'Siempre es la última: si algo no coincide con la obra, avisar al dueño.</footer></body></html>')
        f = dest / ruta.strip("/") / "index.html" if ruta != "/" else dest / "index.html"
        f.parent.mkdir(parents=True, exist_ok=True)
        f.write_text(doc, encoding="utf-8")

    def boton(href, emoji, texto, sub="", clase="", color=None):
        st = f' style="--c:{color}"' if color else ""
        s = f"<small>{html.escape(sub)}</small>" if sub else ""
        return f'<a class="btn {clase}" href="{href}"{st}><span class="em">{emoji}</span><span>{html.escape(texto)}{s}</span></a>'

    def pisos_con(o):
        return [p for p in PISOS if arbol[o][p[0]]]

    # ── inicio ──
    oficios = "".join(boton(url(o[0]), o[2], o[1], color=o[3], clase="grande") for o in OFICIOS)
    todos = "".join(boton(url("todos", "antes", p["slug"]), icono(p["tema"]), corto(p["tema"]), color=TODOS[3])
                    for p in arbol["todos"]["antes"])
    casa = "".join(boton(f"/casa/{slug(t)}/", e, t, color="#2e7d32") for t, _, e in extras)
    pagina("/", "Obra", [], f'<h1>¿Quién eres?</h1><div class="grilla g2">{oficios}</div>'
           f'<h2>Para todos</h2><div class="grilla">{todos}</div>'
           f'<h2 id="casa">La casa entera</h2><div class="grilla">{casa}</div>')

    # ── la casa entera (fachadas, plantas, 3D) ──
    for t, arch, e in extras:
        if arch.endswith(".html"):
            d = dest / "casa" / slug(t)
            d.mkdir(parents=True, exist_ok=True)
            shutil.copy(salida / arch, d / "index.html")
            continue
        shutil.copy(salida / arch, dest / "planos" / arch)
        otros = "".join(boton(f"/casa/{slug(x)}/", ee, x, clase="chico" + (" activo" if x == t else ""), color="#2e7d32")
                        for x, _, ee in extras)
        pagina(f"/casa/{slug(t)}/", t, [("La casa", "/#casa"), (t, f"/casa/{slug(t)}/")],
               f'<div class="fila">{otros}</div><h1>{e} {html.escape(t)}</h1>'
               f'<a class="zoom" href="/planos/{arch}" target="_blank"><img class="plano" src="/planos/{arch}">'
               f'<span>🔍 Tocar para ver grande</span></a>', "#2e7d32")

    # ── oficio → pisos ──
    for o in OFICIOS + [TODOS]:
        ps = pisos_con(o[0])
        if o[0] == "todos":
            pagina(url(o[0]), o[1], [(o[1], url(o[0]))], f'<h1>{o[2]} {o[1]}</h1><div class="grilla g2">{todos}</div>', o[3])
        else:
            bot = "".join(boton(url(o[0], p[0]), "📋" if p[0] == "antes" else "🏢", p[1],
                                f"{len(arbol[o[0]][p[0]])} hojas", "grande", o[3]) for p in ps)
            pagina(url(o[0]), o[1], [(o[1], url(o[0]))], f'<h1>{o[2]} {o[1]}: ¿qué piso?</h1><div class="grilla g2">{bot}</div>',
                   o[3])
        for p in ps:
            pags = arbol[o[0]][p[0]]
            bot = "".join(boton(url(o[0], p[0], x["slug"]), icono(x["tema"]), corto(x["tema"]), clase="grande", color=o[3])
                          for x in pags)
            otros = "".join(boton(url(o[0], q[0]), "", q[1], clase="chico" + (" activo" if q == p else ""), color=o[3])
                            for q in ps)
            pagina(url(o[0], p[0]), f"{o[1]} · {p[1]}", [(o[1], url(o[0])), (p[1], url(o[0], p[0]))],
                   f'<div class="fila">{otros}</div><h1>{o[2]} {o[1]} · {p[1]}</h1><div class="grilla g2">{bot}</div>', o[3])

            # ── hojas ──
            for i, x in enumerate(pags):
                migas = [(o[1], url(o[0])), (p[1], url(o[0], p[0])), (corto(x["tema"]), url(o[0], p[0], x["slug"]))]
                temas = "".join(boton(url(o[0], p[0], y["slug"]), icono(y["tema"]), corto(y["tema"]),
                                      clase="chico" + (" activo" if y is x else ""), color=o[3]) for y in pags)
                # mismo tema en otro piso (si no existe, a la lista de ese piso)
                cambio_piso = ""
                if p[0] != "antes":
                    bs = []
                    for q in ps:
                        if q[0] == "antes":
                            continue
                        igual = next((y for y in arbol[o[0]][q[0]] if y["slug"] == x["slug"]), None)
                        bs.append(boton(url(o[0], q[0], igual["slug"]) if igual else url(o[0], q[0]), "🏢", q[1],
                                        clase="chico" + (" activo" if q == p else ""), color=o[3]))
                    cambio_piso = f'<div class="bloque"><b>Ver esto en otro piso:</b><div class="fila">{"".join(bs)}</div></div>'
                otro_of = "".join(boton(url(u[0], p[0]) if arbol[u[0]][p[0]] else url(u[0]), u[2], u[1], clase="chico",
                                        color=u[3]) for u in OFICIOS if u != o)
                ant = boton(url(o[0], p[0], pags[i - 1]["slug"]), "◀", "Anterior", corto(pags[i - 1]["tema"]),
                            "chico", o[3]) if i else ""
                sig = boton(url(o[0], p[0], pags[i + 1]["slug"]), "▶", "Siguiente", corto(pags[i + 1]["tema"]),
                            "chico", o[3]) if i + 1 < len(pags) else ""
                donde = "" if p[0] == "antes" else f" · {p[1]}"
                pagina(url(o[0], p[0], x["slug"]), f"{corto(x['tema'])} · {o[1]}{donde}", migas,
                       f'{cambio_piso}'
                       f'<h1>{icono(x["tema"])} {html.escape(x["tema"][:1].upper() + x["tema"][1:])}</h1>'
                       f'<div class="hoja-web">{x["cuerpo"]}</div>'
                       f'<div class="fila pie">{ant}{sig}</div>'
                       f'<div class="bloque"><b>Otras hojas de {o[1].lower()}{donde.lower()}:</b>'
                       f'<div class="fila">{temas}</div></div>'
                       f'<div class="bloque"><b>Ver {p[1].lower() if p[0] != "antes" else "lo"} de otro oficio:</b>'
                       f'<div class="fila">{otro_of}</div></div>', o[3])

    (dest / "vercel.json").write_text(json.dumps({"trailingSlash": True}, indent=2), encoding="utf-8")
    n = sum(1 for _ in dest.rglob("index.html"))
    print(f"ok salida/sitio ({n} páginas)")


SCRIPT_WEB = """<script>
(function () {
  var caja = document.getElementById("dato");
  document.addEventListener("click", function (e) {
    var g = e.target.closest && e.target.closest("g.rot");
    if (!g) { caja.hidden = true; return; }
    var partes = g.getAttribute("data-info").split(" — ");
    caja.innerHTML = "<b>" + partes[0] + "</b>" + partes.slice(1).map(function (t) { return "<p>" + t + "</p>"; }).join("") +
      "<small>Toca afuera para cerrar</small>";
    caja.hidden = false;
  });
})();
</script>"""

ESTILO_WEB = """<style>
body { background: #f6f4f0; font-size: 17px; }
header { position: sticky; top: 0; z-index: 5; background: var(--c); color: #fff; padding: 10px 14px;
  display: flex; flex-wrap: wrap; align-items: center; gap: 6px 14px; box-shadow: 0 2px 6px rgba(0,0,0,.2); }
header nav { flex: 1; font-size: 18px; font-weight: bold; }
header a { color: #fff; text-decoration: none; }
header .inicio { background: rgba(255,255,255,.22); border-radius: 8px; padding: 6px 12px; display: inline-block; }
header .sep { margin: 0 8px; opacity: .7; }
header .ver { float: none; color: #fff; border-color: rgba(255,255,255,.6); margin: 0; }
main { max-width: 1400px; margin: 0 auto; padding: 14px 16px 30px; }
h1 { font-size: 26px; margin: 16px 0 12px; } h2 { font-size: 21px; margin: 26px 0 10px; }
.grilla { display: grid; grid-template-columns: repeat(auto-fill, minmax(230px, 1fr)); gap: 12px; }
.grilla.g2 { grid-template-columns: repeat(auto-fill, minmax(300px, 1fr)); }
.btn { display: flex; align-items: center; gap: 12px; background: #fff; color: #111; text-decoration: none;
  border: 3px solid var(--c); border-left-width: 12px; border-radius: 12px; padding: 14px 16px; font-size: 19px;
  font-weight: bold; line-height: 1.2; }
.btn:active { transform: scale(.98); }
.btn small { display: block; font-size: 13px; font-weight: normal; color: #555; margin-top: 3px; }
.btn .em { font-size: 30px; }
.btn.grande { min-height: 78px; font-size: 22px; } .btn.grande .em { font-size: 40px; }
.btn.chico { padding: 8px 12px; font-size: 15px; border-width: 2px; border-left-width: 6px; }
.btn.chico .em { font-size: 20px; } .btn.chico .em:empty { display: none; }
.btn.activo { background: var(--c); color: #fff; } .btn.activo small { color: #eee; }
.fila { display: flex; flex-wrap: wrap; gap: 8px; margin: 6px 0; }
.fila.pie { justify-content: space-between; margin: 24px 0 8px; }
.bloque { background: #fff; border-radius: 10px; padding: 8px 12px; margin: 10px 0; }
.bloque > b { font-size: 14px; color: #555; }
.hoja-web { background: #fff; border-radius: 10px; padding: 8px 14px 14px; overflow-x: auto; }
.hoja-web .hoja { page-break-after: auto; }
.hoja-web .tit { display: none; }
a.zoom { display: block; text-decoration: none; position: relative; }
a.zoom span { display: block; text-align: center; font-size: 14px; color: #1f6fb2; margin: 2px 0 8px; }
.plano, .plano.inst, .plano.alb { max-height: none; width: 100%; height: auto; background: #fff; }
table { display: block; overflow-x: auto; font-size: 14px; }
.plano-vivo svg { width: 100%; height: auto; display: block; }
.plano-vivo g.rot { cursor: pointer; } .plano-vivo g.rot:hover rect { stroke: #b71c1c; stroke-width: 2; }
p.toca { font-size: 14px; color: #1f6fb2; margin: 4px 0 10px; text-align: center; }
#dato { position: fixed; left: 12px; right: 12px; bottom: 12px; z-index: 20; max-width: 560px; margin: 0 auto; background: #fff;
  border: 3px solid #b71c1c; border-radius: 12px; padding: 10px 14px; box-shadow: 0 6px 24px rgba(0,0,0,.3); font-size: 16px; }
#dato b { font-size: 20px; color: #b71c1c; } #dato p { margin: 6px 0; } #dato small { color: #777; }
footer { text-align: center; color: #777; font-size: 13px; padding: 20px 16px 40px; }
@media (max-width: 800px) {
  .cols, .pasos, .bod { grid-template-columns: 1fr; gap: 10px; }
  .leyg { grid-template-columns: 1fr 1fr; } .tarjetas { grid-template-columns: 1fr 1fr; }
  h1 { font-size: 22px; } .btn.grande { font-size: 20px; }
}
</style>"""
