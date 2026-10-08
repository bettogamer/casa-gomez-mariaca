"""Alzados (fachadas) generados desde el modelo: oeste (frente), norte, este (fondo) y sur.

Uso: python tools/render_alzados.py

Proyección ortogonal: cada pieza (muro, abertura, losa, baranda, celosía, techo, antepecho, tanque,
poste) se proyecta sobre el plano de la fachada y se dibuja de atrás hacia adelante. Las de más
atrás salen más claras. Los colores salen de `fachada.paleta` del modelo (si no, una paleta neutra);
cada opción de `fachada.opciones` genera su propio juego de alzados.
"""
import re

from casa import SALIDA, aberturas, ambientes, cargar, columnas, huella_casa, muros
from render_svg import ESC, Lienzo

PALETA = {
    "muro": "#f1eee8", "zocalo": "#cfc9bf", "losa": "#d8d3ca", "columna": "#e6e2da",
    "vidrio": "#b9d6e6", "marco": "#3a3a3a", "puerta": "#b07a4a", "baranda": "#333333",
    "celosia": "#c49a6c", "techo": "#7d878d", "antepecho": "#ece8e1", "tanque": "#e6e1d8", "poste": "#333333",
}

LISOS = {"muro", "antepecho", "columna", "losa", "zocalo", "tanque"}


def _aclarar(color, prof):
    """Mezcla con blanco según la profundidad (0 = adelante): hasta un 55 % a 8 m o más."""
    t = max(0.0, min(0.55, prof / 8 * 0.55))
    r, g, b = (int(color[i:i + 2], 16) for i in (1, 3, 5))
    r, g, b = (round(v + (255 - v) * t) for v in (r, g, b))
    return f"#{r:02x}{g:02x}{b:02x}"


# (nombre, cómo se ve: eje horizontal u y profundidad d desde el punto de (x, y) de la planta)
VISTAS = {
    "oeste": ("Fachada oeste (frente)", lambda x, y: y, lambda x, y: x),
    "norte": ("Fachada norte (retiro, Lote 105)", lambda x, y: -x, lambda x, y: y),
    "este": ("Fachada este (fondo, patio)", lambda x, y: -y, lambda x, y: -x),
    "sur": ("Fachada sur (vecino, Lote 103)", lambda x, y: x, lambda x, y: -y),
}


def _plano(de, a, vista):
    """¿El segmento de planta se ve de frente en esta vista? Devuelve (u0, u1, profundidad) o None."""
    _, U, D = VISTAS[vista]
    d0, d1 = D(*de), D(*a)
    if abs(d0 - d1) > 0.01:
        return None
    u0, u1 = sorted([U(*de), U(*a)])
    if u1 - u0 < 0.01:
        return None
    return u0, u1, d0


def _piezas(casa, vista, pal):
    """Lista de (profundidad, orden, función que dibuja). Más profundidad = más atrás."""
    est = casa["estructura"]
    _, U, D = VISTAS[vista]
    out = []

    def rect(u0, u1, z0, z1, d, cat, extra="", orden=0, color=None):
        def f(L, prof, a=(u0, u1, z0, z1)):
            c = color or pal[cat]
            if cat in LISOS and c != "none":
                c = _aclarar(c, prof)      # lo de más atrás, más claro; sin borde: el muro se ve de una pieza
                estilo = f'fill="{c}" stroke="{c}" stroke-width="0.6"'
            else:
                at = {"fill": c, "stroke": "#555", "stroke-width": "0.6"}
                for k, v in re.findall(r'([\w-]+)="([^"]*)"', extra):
                    at[k] = v
                estilo = " ".join(f'{k}="{v}"' for k, v in at.items())
            L.poly([[a[0], -a[2]], [a[1], -a[2]], [a[1], -a[3]], [a[0], -a[3]]], estilo)
        out.append((d, orden, f))

    def lineas(u0, u1, z0, z1, d, paso, color, orden=1, ancho=2):
        def f(L, prof, u0=u0, u1=u1):
            n = max(1, int((u1 - u0) / paso))
            for k in range(n + 1):
                u = u0 + (u1 - u0) * k / n
                L.linea(u, -z0, u, -z1, f'stroke="{color}" stroke-width="{ancho}"')
        out.append((d, orden, f))

    cota = {n["id"]: n for n in casa["niveles"]}
    for n in casa["niveles"]:
        z0, z1 = n["cota"], n["cota"] + n["altura_libre"]
        if n["id"] == casa["niveles"][0]["id"]:
            z0 = 0.0
        # muros de ladrillo (sobre su cara exterior real) y aberturas con su dintel y antepecho
        for m in muros(casa, n["id"]):
            p = _plano(m["de"], m["a"], vista)
            if not p:
                continue
            u0, u1, d = p
            if m["tipo"] == "ladrillo":
                dd = d + D(m.get("dx", 0), m.get("dy", 0)) - D(0, 0) - m.get("grosor", 0.15) / 2
                rect(u0, u1, z0, z1, dd, "muro")
            elif m["tipo"] == "baranda":
                alto = m.get("alto") or 1.0
                if alto > 1.2:          # antepecho de ladrillo (muro ciego al vecino)
                    rect(u0, u1, n["cota"], n["cota"] + alto, d - 0.01, "antepecho")
                else:                   # baranda metálica: pasamanos + barrotes
                    zb, zt_ = n["cota"], n["cota"] + alto
                    lineas(u0, u1, zb, zt_, d - 0.01, 0.12, pal["baranda"], orden=3, ancho=1)
                    out.append((d - 0.01, 3, lambda L, prof, u0=u0, u1=u1, zt_=zt_, zb=zb: (
                        L.linea(u0, -zt_, u1, -zt_, f'stroke="{pal["baranda"]}" stroke-width="3"'),
                        L.linea(u0, -zb - 0.08, u1, -zb - 0.08, f'stroke="{pal["baranda"]}" stroke-width="1.5"'))))
            elif m["tipo"].startswith("celosia"):
                lineas(u0, u1, n["cota"], z1, d - 0.02, 0.10, pal["celosia"], orden=2)
        for ab in aberturas(casa, n["id"]):
            p = _plano(ab["de"], ab["a"], vista)
            if not p or ab["tipo"] in ("vano", "porton") or ab.get("en_cerco"):     # el portón y el cerco de la calle no van en las fachadas
                continue
            u0, u1, d = p
            alto = ab.get("alto", 2.10)
            ap = ab.get("antepecho") or 0.0
            dd = d - 0.13
            rect(u0, u1, z0, z1, d - 0.06, "muro", orden=0)     # dintel y antepecho: detrás de los acentos de la cara
            if ab["tipo"] == "ventana":
                rect(u0, u1, n["cota"] + ap, n["cota"] + alto, dd, "vidrio", orden=1)
                rect(u0, u1, n["cota"] + ap, n["cota"] + alto, dd, "vidrio", 'fill="none" stroke-width="2"', orden=2,
                     color="none")
            elif ab["tipo"] == "corrediza":
                rect(u0, u1, n["cota"], n["cota"] + alto, dd, "vidrio", orden=1)
                um = (u0 + u1) / 2
                out.append((dd, 2, lambda L, prof, um=um, a=n["cota"], b=n["cota"] + alto:
                            L.linea(um, -a, um, -b, f'stroke="{pal["marco"]}" stroke-width="2"')))
            else:
                rect(u0, u1, n["cota"], n["cota"] + alto, dd, "puerta", orden=1)
    # columnas a la vista (donde no las tapa un muro): de piso a la última losa
    s = est["seccion_columna"] / 2
    zc = max(n["cota"] for n in casa["niveles"])
    for c in columnas(casa):
        us = sorted([U(c["x"] - s, c["y"] - s), U(c["x"] + s, c["y"] + s)])
        d = min(D(c["x"] + sx, c["y"] + sy) for sx in (-s, s) for sy in (-s, s))
        rect(us[0], us[1], 0.0, zc, d + 0.002, "columna")
    # losas (P1 y altillo): banda de la losa en todo su borde, con el volado
    vg = est["viguetas"]
    xs = [p for pa in vg["panos"] for p in (pa["rect"][0], pa["rect"][2])]
    ys = [p for pa in vg["panos"] for p in (pa["rect"][1], pa["rect"][3])]
    caja = [(min(xs), min(ys)), (max(xs), min(ys)), (max(xs), max(ys)), (min(xs), max(ys))]
    us = [U(*p) for p in caja]
    dl = min(D(*p) for p in caja)
    for n in casa["niveles"][1:]:
        rect(min(us), max(us), n["cota"] - est["espesor_losa"], n["cota"], dl - 0.005, "losa", orden=3)
    # zócalo de PB
    hx0, hy0, hx1, hy1 = huella_casa(casa)
    hu = [U(hx0, hy0), U(hx1, hy1)]
    hd = min(D(hx0, hy0), D(hx1, hy1), D(hx0, hy1), D(hx1, hy0))
    rect(min(hu), max(hu), 0.0, casa["niveles"][0]["cota"], hd - 0.006, "zocalo", orden=3)
    # techos
    t = casa.get("techos") or {}
    for ag in t.get("aguas") or []:
        xs = [p[0] for p in ag["poly"]]
        ys = [p[1] for p in ag["poly"]]
        lo, hi = ag["cota_baja"], ag["cota_alta"]
        uu = [U(x, y) for x, y in ag["poly"]]
        d = min(D(x, y) for x, y in ag["poly"])
        rect(min(uu), max(uu), lo, hi, d - 0.03, "techo", orden=2)
    for a in t.get("antepechos") or []:
        p = _plano(a["de"], a["a"], vista)
        if p:
            rect(p[0], p[1], a["cota_base"], a["cota_tope"], p[2] - 0.08, "antepecho", orden=1)
    for po in t.get("postes") or []:
        x, y = po["pos"]
        zt = max(ag["cota_alta"] for ag in t.get("aguas") or [{"cota_alta": 9.9}])
        rect(U(x, y) - 0.05, U(x, y) + 0.05, casa["niveles"][-1]["cota"], po.get("tope", zt), D(x, y) - 0.12, "poste", orden=4)
    if t.get("tanque"):
        tq = t["tanque"]
        x0, y0, x1, y1 = tq["rect"]
        uu = [U(x0, y0), U(x1, y1)]
        d = min(D(x0, y0), D(x1, y1), D(x0, y1), D(x1, y0))
        rect(min(uu), max(uu), tq["cota_base"], tq["cota_base"] + tq["alto"], d, "tanque", orden=1)
        um = sum(uu) / 2      # base de hormigón del tanque, sobre el techo
        rect(um - 0.35, um + 0.35, 10.0, tq["cota_base"], d + 0.01, "losa", orden=0)
    return out


MATERIALES = {   # acento -> (relleno, líneas: None | ("v"|"h", paso m, color))
    "negro": ("#2b2b2b", None), "gris_oscuro": ("#43464a", None), "blanco": ("#f7f7f5", None),
    "madera": ("#a8703f", ("v", 0.08, "#7a4f2a")), "piedra": ("#9a948b", ("h", 0.15, "#7c766d")),
    "beige": ("#d8c9b1", None), "gris_claro": ("#c9c6c0", None),
    # instalaciones a la vista (2026-10-08, fachada norte): chapa perforada (cajón del gas), caño de gas (amarillo, ANH),
    # rejillas pintadas del color del muro o del gris de las pilastras
    "chapa_perforada": ("#43464a", ("p", 0.06, "#6d7075")), "gas": ("#e0b000", None),
    "rejilla_blanca": ("#f3f1ec", ("h", 0.03, "#b9b4aa")), "rejilla_gris": ("#43464a", ("h", 0.03, "#7a7d82")),
}


def _punto(u, z, r=0.012):
    return [[u - r, z - r], [u + r, z - r], [u + r, z + r], [u - r, z + r]]


def _acentos(L, acentos, vista):
    for a in acentos or []:
        if a.get("vista") != vista:
            continue
        (u0, u1), (z0, z1) = a["u"], a["z"]
        relleno, lin = MATERIALES[a["material"]]
        L.poly([[u0, -z0], [u1, -z0], [u1, -z1], [u0, -z1]], f'fill="{relleno}" stroke="none"')
        if lin:
            sentido, paso, col = lin
            if sentido == "p":         # perforado: puntos cada `paso`
                nu, nz = max(1, int((u1 - u0) / paso)), max(1, int((z1 - z0) / paso))
                for i in range(nu):
                    for j in range(nz):
                        L.poly(_punto(u0 + (i + 0.5) * (u1 - u0) / nu, -(z0 + (j + 0.5) * (z1 - z0) / nz)),
                               f'fill="{col}" stroke="none"')
            elif sentido == "v":
                n = max(1, int((u1 - u0) / paso))
                for k in range(1, n):
                    u = u0 + (u1 - u0) * k / n
                    L.linea(u, -z0, u, -z1, f'stroke="{col}" stroke-width="1"')
            else:
                n = max(1, int((z1 - z0) / paso))
                for k in range(1, n):
                    z = z0 + (z1 - z0) * k / n
                    L.linea(u0, -z, u1, -z, f'stroke="{col}" stroke-width="1"')


def alzado(casa, vista, pal, sufijo="", acentos=None):
    titulo, U, D = VISTAS[vista]
    piezas = _piezas(casa, vista, pal)
    hx0, hy0, hx1, hy1 = huella_casa(casa)
    puntos = [(-1.2, hy0), (hx1, hy1), (-1.2, hy1), (hx1, hy0)]
    us = [U(x, y) for x, y in puntos]
    u0, u1 = min(us) - 1.0, max(us) + 1.0
    zt = 12.8
    L = Lienzo(u0 - 1.5, -zt, u1, 0.6)
    # de atrás hacia adelante; `prof` = cuánto más atrás está que lo más cercano (para aclarar)
    dmin = min(p[0] for p in piezas)
    # cada acento va pegado a la cara que decora: `d` = su profundidad en esta vista (oeste: x; norte: y; este: -x; sur: -y)
    for a in acentos or []:
        if a.get("vista") == vista:
            piezas.append((a["d"] - 0.004, 1, lambda L, prof, a=a: _acentos(L, [a], vista)))
    for d, orden, f in sorted(piezas, key=lambda p: (-p[0], p[1])):
        f(L, d - dmin)
    L.linea(u0, 0, u1, 0, 'stroke="#222" stroke-width="2.5"')
    for n in casa["niveles"]:
        L.linea(u0 - 1.2, -n["cota"], u0 - 0.2, -n["cota"], 'stroke="#555" stroke-width="1"')
        L.texto(u0 - 1.25, -n["cota"] - 0.08, f"+{n['cota']:.2f} {n['nombre'].lower()}", 8,
                'fill="#555" text-anchor="start"')
    L.texto((u0 + u1) / 2, 0.45, f"{titulo}{sufijo}", 13, 'font-weight="bold"')
    return L.svg(f"{titulo}{sufijo}")


def main():
    casa = cargar()
    SALIDA.mkdir(exist_ok=True)
    fz = casa.get("fachada") or {}
    juegos = [("", {**PALETA, **(fz.get("paleta") or {})}, "", None)]
    for op in fz.get("opciones") or []:
        juegos.append((f"-{op['id']}", {**PALETA, **(op.get("paleta") or {})}, f" — opción {op['id'].upper()}: {op['nombre']}",
                       op.get("acentos")))
    for suf, pal, txt, ac in juegos:
        for v in VISTAS:
            f = SALIDA / f"fachada-{v}{suf}.svg"
            f.write_text(alzado(casa, v, pal, txt, ac), encoding="utf-8")
            print("→", f.relative_to(SALIDA.parent))
    _pagina(casa, juegos)


def _pagina(casa, juegos):
    """salida/fachadas.html: las opciones lado a lado, con sus notas."""
    from html import escape
    fz = casa.get("fachada") or {}
    notas = {f"-{op['id']}": op for op in fz.get("opciones") or []}
    cuerpo = ""
    for suf, _, txt, _ in juegos:
        op = notas.get(suf)
        titulo = f"Opción {op['id'].upper()}: {op['nombre']}" if op else "Base (sin materiales)"
        cuerpo += f"<section><h2>{escape(titulo)}</h2>"
        if op and op.get("descripcion"):
            cuerpo += f"<p>{escape(op['descripcion'])}</p>"
        cuerpo += '<div class="fila">' + "".join(
            f'<figure>{(SALIDA / f"fachada-{v}{suf}.svg").read_text(encoding="utf-8")}</figure>' for v in ("oeste", "norte")) + "</div>"
        cuerpo += '<div class="fila">' + "".join(
            f'<figure>{(SALIDA / f"fachada-{v}{suf}.svg").read_text(encoding="utf-8")}</figure>' for v in ("este", "sur")) + "</div></section>"
    html = ("<!doctype html><meta charset=utf-8><title>Fachadas</title><style>body{font-family:Helvetica,Arial,sans-serif;"
            "margin:16px;color:#222}.fila{display:flex;gap:12px;flex-wrap:wrap}figure{margin:0;flex:1 1 420px}"
            "svg{width:100%;height:auto}section{margin-bottom:40px;border-bottom:1px solid #ddd}</style>"
            "<h1>Fachadas — opciones</h1>" + cuerpo)
    f = SALIDA / "fachadas.html"
    f.write_text(html, encoding="utf-8")
    print("→", f.relative_to(SALIDA.parent))


if __name__ == "__main__":
    main()
