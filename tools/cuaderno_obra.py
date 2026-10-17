"""Cuaderno de obra (A3 apaisado) para el albañil, el plomero, el gasista y el electricista.

Cada sección: paso a paso, lista "para el dueño: cómo revisar", planos con una sola instalación por hoja y su leyenda
completa, y tablas para contar los puntos en obra. Genera salida/cuaderno-obra.html y, si hay Google Chrome,
salida/cuaderno-obra.pdf. Se corre con `make cuaderno` (después de `make build`, porque usa las plantas de salida/).
"""
import datetime
import html
import pathlib
import re
import shutil
import subprocess
import sys

import casa as C
import instalaciones as I
import plano_obra as O
import sitio_obra
from render_svg import ESC, Lienzo

RAIZ = pathlib.Path(__file__).resolve().parent.parent
SALIDA = RAIZ / "salida"
CHROME = "/Applications/Google Chrome.app/Contents/MacOS/Google Chrome"

c = C.cargar()
est = c["estructura"]
EX = sorted((v, k) for k, v in est["ejes_x"].items())
EY = sorted((v, k) for k, v in est["ejes_y"].items())
NIVELES = [("pb", "Planta baja"), ("p1", "Primer piso"), ("altillo", "Altillo")]
COTA = {n["id"]: n.get("cota", 0) for n in c["niveles"]}
CUAD = (c.get("proyecto") or {}).get("cuaderno") or {}
VERSION = str(CUAD.get("version", "1"))
NUEVAS = []     # hojas que cambian en esta versión: van también al PDF corto de "hojas nuevas"
HOJAS = []      # todas las hojas con su sección: para la página web de la obra (tools/sitio_obra.py)

# Muros sobre losa sin muro debajo (docs/preguntas-ingeniero.md, pregunta 4) y sobre el volado (pregunta 1):
# (eje, valor, rango opcional sobre la otra coordenada, texto)
CONSULTAR = {
    "p1": [
        ("x", 5.85, None, "muro del vestidor sobre la losa"),
        ("x", 9.40, (3.88, 6.67), "muro del Baño 2 sobre la losa"),
        ("y", 3.88, None, "muro del Baño 2 sobre la losa"),
        ("x", 12.50, None, "muro del vestíbulo sobre la losa"),
        ("y", 3.335, None, "muro entre los dos cuartos, sobre la losa"),
    ],
    "altillo": [
        ("x", 13.60, None, "muro del dormitorio sobre la losa"),
        ("y", 4.67, None, "muro sur del departamento sobre la losa (12.5 m)"),
    ],
}


def ref(v, ejes):
    """'eje 3 + 1.65' (o 'eje 3' si cae justo)."""
    base = max((e for e in ejes if e[0] <= v + 0.005), default=ejes[0])
    d = v - base[0]
    if abs(d) < 0.005:
        return f"eje {base[1]}"
    return f"eje {base[1]} {'+' if d > 0 else '−'} {abs(d):.2f}"


def corto(t, n=150):
    t = re.sub(r"\s+", " ", t or "").strip()
    return t if len(t) <= n else t[: n - 1].rsplit(" ", 1)[0] + "…"


def donde_id(nivel, x, y):
    """Id del ambiente que contiene el punto; si cae en un muro de la casa, el de al lado; afuera, qué lado."""
    ambs = C.ambientes(c, nivel)
    x1, y1 = EX[-1][0], EY[-1][0]
    afuera = ("afuera: retiro norte" if 0 <= x <= x1 and y < 0 else "afuera: patio" if x > x1
              else "afuera: lado sur" if y > y1 else "")
    for dx, dy in [(0, 0)] + ([] if afuera else [(0.2, 0), (-0.2, 0), (0, 0.2), (0, -0.2)]):
        for a in ambs:
            if C.dentro(a["poly"], x + dx, y + dy):
                return a["id"]
    return afuera or "afuera"


def donde(nivel, x, y):
    i = donde_id(nivel, x, y)
    return nombres_amb(nivel).get(i, i)


def lados(nivel, ab):
    """Los dos ambientes que une una puerta o ventana (o el ambiente y 'afuera')."""
    (x0, y0), (x1, y1) = ab["de"], ab["a"]
    mx, my = (x0 + x1) / 2, (y0 + y1) / 2
    hor = abs(y0 - y1) < 0.01
    ns = []
    for s in (-0.25, 0.25):
        px, py = (mx, my + s) if hor else (mx + s, my)
        adentro = 0 < px < EX[-1][0] and 0 < py < EY[-1][0]
        n = next((a.get("nombre", a["id"]) for a in C.ambientes(c, nivel) if C.dentro(a["poly"], px, py)),
                 "Escalera" if adentro else "afuera")
        if n not in ns:
            ns.append(n)
    return " ↔ ".join(ns)


MIN_VANO = 0.20   # huecos más angostos son restos de dibujo entre muros, no se marcan


def esperar(nivel, eje, val, de, a):
    """Texto de aviso si el muro espera al ingeniero."""
    if nivel == "p1" and (eje == "y" and a < 0.01 or eje == "x" and val < -0.01):
        return "sobre el volado del frente (peso en la punta)"
    for e, v, rango, txt in CONSULTAR.get(nivel, []):
        if e == eje and abs(v - val) < 0.01 and (rango is None or de >= rango[0] - 0.01 and a <= rango[1] + 0.01):
            return txt
    return ""


def lineas(nivel):
    """Agrupa muros de ladrillo y aberturas por línea recta; devuelve muros continuos con sus vanos."""
    nombres = {a["id"]: a.get("nombre", a["id"]) for a in C.ambientes(c, nivel)}
    segs = []
    for m in C.muros(c, nivel):
        if m["tipo"] != "ladrillo":
            continue
        (x0, y0), (x1, y1) = m["de"], m["a"]
        if abs(y0 - y1) < 0.01:
            a, b = min(x0, x1), max(x0, x1)
            # en el P1 se corta en el eje 1: lo que cae sobre el volado espera al ingeniero
            cortes = [a, 0.0, b] if nivel == "p1" and a < -0.01 < 0.01 < b else [a, b]
            for p, q in zip(cortes, cortes[1:]):
                segs.append(("y", round(y0, 3), p, q, m))
        elif abs(x0 - x1) < 0.01:
            segs.append(("x", round(x0, 3), min(y0, y1), max(y0, y1), m))
    vanos = []
    for ab in C.aberturas(c, nivel):
        if ab.get("en_cerco") or ab["tipo"] == "porton":
            continue
        (x0, y0), (x1, y1) = ab["de"], ab["a"]
        if abs(x1 - x0) + abs(y1 - y0) < MIN_VANO:
            continue
        if abs(y0 - y1) < 0.01:
            vanos.append(("y", round(y0, 3), min(x0, x1), max(x0, x1), ab))
        elif abs(x0 - x1) < 0.01:
            vanos.append(("x", round(x0, 3), min(y0, y1), max(y0, y1), ab))
    grupos = {}
    for s in segs:
        grupos.setdefault((s[0], s[1], s[4].get("grosor", 0.15), s[0] == "y" and s[3] < 0.01), []).append(s)
    salida = []
    for (eje, val, g, _), tramos in grupos.items():
        vs = [v for v in vanos if v[0] == eje and abs(v[1] - val) < 0.01]
        lo, hi = min(t[2] for t in tramos), max(t[3] for t in tramos)
        todos = sorted([[t[2], t[3]] for t in tramos] + [[v[2], v[3]] for v in vs if v[2] >= lo - 0.01 and v[3] <= hi + 0.01])
        unidos = []
        for a, b in todos:
            if unidos and a <= unidos[-1][1] + 0.02:
                unidos[-1][1] = max(unidos[-1][1], b)
            else:
                unidos.append([a, b])
        m0 = tramos[0][4]
        for a, b in unidos:
            mios = [t for t in tramos if t[2] >= a - 0.01 and t[3] <= b + 0.01]
            if not mios:
                continue
            ambs = []
            for t in mios:
                n = nombres.get(t[4].get("amb"), "")
                if n and n not in ambs:
                    ambs.append(n)
            salida.append({"eje": eje, "val": val, "de": a, "a": b, "grosor": g, "dx": m0.get("dx", 0),
                           "dy": m0.get("dy", 0), "ambs": ambs,
                           "vanos": [v for v in vs if v[2] >= a - 0.01 and v[3] <= b + 0.01]})
    salida.sort(key=lambda m: (m["eje"], m["val"], m["de"]))
    return salida


def nombre_vano(ab):
    return {"puerta": "Puerta", "ventana": "Ventana", "vano": "Paso abierto (sin puerta)", "corrediza": "Corrediza",
            "celosia_madera": "Celosía"}.get(ab["tipo"], ab["tipo"].replace("_", " ").capitalize())


def fila_muro(nivel, m):
    if m["eje"] == "y":
        donde = f"Línea {ref(m['val'], EY)} (horizontal en el plano)"
        tramo = f"de {ref(m['de'], EX)} a {ref(m['a'], EX)}"
    else:
        donde = f"Línea {ref(m['val'], EX)} (vertical en el plano)"
        tramo = f"de {ref(m['de'], EY)} a {ref(m['a'], EY)}"
    tipo = "CABEZA (25)" if m["grosor"] >= 0.2 else "soga (15)"
    if m["dx"] or m["dy"]:
        cara = {(-1, 0): "OESTE", (1, 0): "ESTE", (0, -1): "NORTE", (0, 1): "SUR"}[
            ((m["dx"] > 0) - (m["dx"] < 0), (m["dy"] > 0) - (m["dy"] < 0))]
        tipo += f" · al ras de la cara {cara} de las columnas"
    elif m["grosor"] < 0.2:
        tipo += " · centrado en la línea"
    aviso = esperar(nivel, m["eje"], m["val"], m["de"], m["a"])
    clase = ' class="espera"' if aviso else ""
    aviso = f'<div class="aviso">✗ NO LEVANTAR TODAVÍA: {html.escape(aviso)} → ingeniero</div>' if aviso else ""
    otro = EX if m["eje"] == "y" else EY
    vanos = "<br>".join(f"{nombre_vano(v[4])} {v[3] - v[2]:.2f} ({ref(v[2], otro)} a {ref(v[3], otro)})"
                        for v in m["vanos"]) or "—"
    return (f"<tr{clase}><td>{html.escape(donde)}<div class=amb>{html.escape(' · '.join(m['ambs']))}</div>{aviso}</td>"
            f"<td>{html.escape(tramo)}</td><td class=n>{m['a'] - m['de']:.2f}</td><td>{tipo}</td><td>{vanos}</td></tr>")


def tabla_vanos(nivel):
    cod = O.codigos(c, nivel)
    filas = []
    for ab in C.aberturas(c, nivel):
        if ab.get("en_cerco") or ab["tipo"] == "porton":
            continue
        (x0, y0), (x1, y1) = ab["de"], ab["a"]
        ancho = abs(x1 - x0) + abs(y1 - y0)
        if ancho < MIN_VANO:
            continue
        if abs(y0 - y1) < 0.01:
            donde = f"{ref(y0, EY)}, de {ref(min(x0, x1), EX)} a {ref(max(x0, x1), EX)}"
        else:
            donde = f"{ref(x0, EX)}, de {ref(min(y0, y1), EY)} a {ref(max(y0, y1), EY)}"
        t = ab["tipo"]
        if t == "vano":
            ap, dint = "—", "hasta losa / abierto"
        elif t == "ventana":
            ap, dint = f"{ab.get('antepecho', 1.0):.2f}", f"{ab.get('alto', 2.10):.2f}"
        else:
            ap, dint = "piso", f"{ab.get('alto', 2.10):.2f}"
        filas.append((t != "ventana", donde,
                      f"<tr><td><b>{cod.get(ab['id'], '')}</b> {nombre_vano(ab)}</td><td>{html.escape(lados(nivel, ab))}</td><td>{html.escape(donde)}</td>"
                      f"<td class=n><b>{ancho:.2f}</b></td><td class=n>{ap}</td><td class=n>{dint}</td>"
                      f"<td class=nota>{html.escape(ab.get('obra', ''))}</td></tr>"))
    filas.sort(key=lambda f: (f[0], f[1]))
    return "".join(f[2] for f in filas)


def hoja(titulo, cuerpo, clase="", seccion="", nueva=False):
    s = f'<span class="secc">{seccion}</span>' if seccion else ""
    marca = f'<span class="ver{" nueva" if nueva else ""}">v{VERSION}{" · HOJA NUEVA" if nueva else ""}</span>'
    h = f'<section class="hoja {clase}"><h2 class="tit">{s}{titulo}{marca}</h2>{cuerpo}</section>'
    HOJAS.append(dict(titulo=titulo, seccion=seccion or globals().get("S", ""), cuerpo=f'<section class="hoja {clase}">{cuerpo}</section>'))
    if nueva is True:      # nueva="luego": cambia, pero no va al PDF corto (se imprime cuando se llegue a ese piso)
        NUEVAS.append(h)
    return h


def paso(n, titulo, items, quien=""):
    q = f'<span class="quien">{quien}</span>' if quien else ""
    return (f'<div class="paso"><div class="num">{n}</div><div><h3>{titulo}{q}</h3>'
            + "".join(f'<p class="chk">☐ {i}</p>' for i in items) + "</div></div>")


def pasos(*ps):
    return '<div class="pasos">' + "".join(ps) + "</div>"


def revisar(items):
    """Lista para el dueño: qué mirar para saber si el trabajo está bien hecho."""
    return ('<div class="revisar"><h3>Para el dueño: cómo revisar que esté bien hecho</h3>'
            + "".join(f'<p class="chk">☐ {i}</p>' for i in items) + "</div>")


def alternativa(titulo, items):
    """Recuadro amarillo: qué cambiaría si se decide otra cosa (todavía NO se hace)."""
    return (f'<div class="alt"><h3>{titulo}</h3>' + "".join(f'<p class="chk">• {i}</p>' for i in items) + "</div>")


# ── símbolos para las leyendas (mismo dibujo que en los planos) ─────────────────

def mini(dibujar, w=0.9, h=0.5):
    """SVG chico con un símbolo dibujado alrededor de (0, 0) por `dibujar(L)`."""
    L = Lienzo(0, 0, 0, 0)
    dibujar(L)
    cx, cy = L.p(0, 0)
    return (f'<svg class="sim" viewBox="{cx - w * ESC / 2:.0f} {cy - h * ESC / 2:.0f} {w * ESC:.0f} {h * ESC:.0f}" '
            f'width="{w * 64:.0f}" height="{h * 64:.0f}">' + "".join(L.partes) + "</svg>")


def punto(tipo, **kw):
    return lambda L: I._dibujar_punto(L, dict(tipo=tipo, pos=(0, 0), **kw))


def raya(color, ancho=2.5, dash="", extra=""):
    return lambda L: L.linea(-0.38, 0, 0.38, 0, f'stroke="{color}" stroke-width="{ancho}" '
                                                 + (f'stroke-dasharray="{dash}" ' if dash else "") + extra)


def cuadro(fill, stroke, letra="", r=0.25, col_letra=None, dash=""):
    def f(L):
        L.poly([[-r, -r], [r, -r], [r, r], [-r, r]], f'fill="{fill}" stroke="{stroke}" stroke-width="1.5"'
               + (f' stroke-dasharray="{dash}"' if dash else ""))
        if letra:
            L.texto(0, 0.05, letra, 7, f'fill="{col_letra or stroke}" font-weight="bold"')
    return f


def circulo(fill, stroke, letra="", r=0.16, col_letra=None, ancho=1.5, dash=""):
    def f(L):
        I._circulo(L, 0, 0, r, f'fill="{fill}" stroke="{stroke}" stroke-width="{ancho}"'
                   + (f' stroke-dasharray="{dash}"' if dash else ""))
        if letra:
            L.texto(0, 0.05, letra, 6, f'fill="{col_letra or stroke}" font-weight="bold"')
    return f


def texto(t, col="#555", tam=7):
    return lambda L: L.texto(0, 0.05, t, tam, f'fill="{col}"')


def tablero(L):
    L.poly([[-0.30, -0.10], [0.30, -0.10], [0.30, 0.08], [-0.30, 0.08]], 'fill="#212121"')
    L.texto(0, 0.03, "TD", 7, 'fill="#fff" font-weight="bold"')


def montante(L):
    I._circulo(L, 0, 0, 0.12, 'fill="#fff" stroke="#212121" stroke-width="1.5"')
    L.linea(-0.08, 0.08, 0.08, -0.08, 'stroke="#212121" stroke-width="1.2"')


def llave(col):
    return lambda L: L.poly([[-0.10, -0.10], [0.10, 0.10], [0.10, -0.10], [-0.10, 0.10]], f'fill="{col}" stroke="{col}"')


def ducto_aire(L):
    L.linea(-0.38, 0, 0.2, 0, 'stroke="#2e7d32" stroke-width="3.5" stroke-opacity="0.75"')
    L.poly([[0.42, 0], [0.2, 0.15], [0.2, -0.15]], 'fill="#2e7d32"')


def seg(**cfg):
    return lambda L: I._dibujar_seguridad(L, cfg)


def leyenda(items, titulo="Qué quiere decir cada símbolo"):
    filas = "".join(f'<div class="ley"><div>{mini(d, *tam)}</div><div>{t}</div></div>' for d, t, *tam in items)
    return f'<div class="leyenda"><h3>{titulo}</h3><div class="leyg">{filas}</div></div>'


NAR, AZ, ROJO, CAFE, GAS, PLUV, VIO, VERDE = "#e65100", "#1565c0", "#c62828", "#6d4c41", "#f9a825", "#0097a7", "#6a1b9a", "#2e7d32"
ALTURA = (texto("h1.10"), "<b>h1.10</b> junto a un punto = altura de la caja desde el piso terminado (1.10 m). Si no dice, "
          "la define el electricista.")
LEY_LUCES = [
    (punto("luz"), "<b>Foco de TECHO</b> (círculo con cruz): la caja va en el techo."),
    (punto("luz", clase="aplique"), "<b>Aplique de PARED (A)</b>: la caja va en el muro, a la altura que dice h (sobre un espejo, "
                                     "junto a una cama, en la escalera, afuera)."),
    (punto("luz", clase="aplique", alto=3.5), "<b>Aplique de la ESCALERA (A↑, punteado)</b>: va más arriba que el techo de "
                                               "ese piso (sobre un descanso). En la planta cae encima de otro ambiente, pero "
                                               "<b>no es de ese ambiente</b>."),
    (punto("luz", clase="led"), "<b>Tira LED</b> bajo una alacena o sobre un espejo: solo una caja chica en el muro, "
                                 "detrás del mueble. <b>No es un foco.</b>"),
    (punto("luz", clase="baliza"), "<b>Luz baja de afuera</b> (baliza empotrada en un muro o en el borde del deck)."),
    (punto("interruptor"), "<b>Tecla (S)</b>: prende y apaga desde un solo lugar."),
    (punto("conmutador"), "<b>Tecla de dos lugares (Sc)</b>: la misma luz se prende y apaga desde dos teclas "
                          "(entrada y salida, abajo y arriba de la escalera)."),
    (raya(NAR, 0.8, "4 3"), "<b>Línea naranja punteada</b>: qué tecla prende qué luces. No es el camino real del cable: "
                            "une la tecla con sus luces."),
    (punto("extractor"), "<b>Extractor (E)</b> de baño, lavado o cocina (se prende con la luz o con su tecla)."),
    (punto("detector", etiqueta="HUMO"), "<b>Detector de humo (H)</b>, en el techo."),
    (punto("detector", etiqueta="GAS"), "<b>Detector de gas (G)</b>, en la cocina."),
    ALTURA,
]
LEY_TOMAS = [
    (punto("toma", circuito="C3"), "<b>Enchufe</b> (tomacorriente doble). El código de arriba (<b>C3</b>) es el "
                                    "<b>circuito</b>: la llave del tablero que lo corta."),
    (punto("toma_ext", circuito="C21"), "<b>Enchufe de afuera (IP)</b>, con tapa contra la lluvia."),
    (punto("toma_piso", circuito="C4"), "<b>Enchufe de piso</b> (en la isla de la cocina)."),
    (punto("especial", etiqueta="R", circuito="C5"), "<b>Enchufe especial</b> para un aparato. La letra dice cuál es: "
                                                      "ver la tabla <b>Enchufes especiales</b>."),
    (punto("datos"), "<b>Internet / TV</b>: caja con tubo propio (no comparte tubo con los cables de 220 V)."),
    (tablero, "<b>TD = tablero</b> de llaves (térmicos y diferenciales).", 0.9, 0.4),
    (montante, "<b>Montante</b>: tubos que suben al piso de arriba (junto a la columna B2)."),
    (raya("#212121", 1.2, "6 3"), "<b>Línea negra punteada</b>: cables gruesos del medidor al tablero, o del tablero al piso de arriba."),
    (raya(VIO, 1.2, "2 3"), "<b>Línea violeta punteada</b>: tubo de corrientes débiles (internet, cámaras, portero, alarma)."),
    (lambda L: I._dibujar_tierra(L, 0, 0.05), "<b>Puesta a tierra</b> (jabalina enterrada, cable verde al tablero)."),
    (seg(camaras=[{"pos": [0, 0]}]), "<b>Cámara</b> de seguridad."),
    (seg(alarma={"central": {"pos": [0, 0]}}), "<b>AL</b> central de alarma · <b>TK</b> teclado · <b>SI</b> sirena."),
    (seg(alarma={"sensores": [{"pos": [0, 0.08], "tipo": "movimiento"}]}),
     "<b>PIR</b> sensor de movimiento · <b>MG</b> sensor magnético de puerta o ventana."),
    (seg(portero={"pos": [0, 0]}), "<b>P</b> pantalla del portero (videoportero)."),
    ALTURA,
]
LEY_AGUA = [
    (raya(AZ, 2.5), "<b>Azul grueso</b>: caño principal de <b>agua fría</b>."),
    (raya(AZ, 1.2), "<b>Azul fino</b>: ramal de agua fría hasta cada artefacto."),
    (raya(ROJO, 2.5), "<b>Rojo</b>: <b>agua caliente</b> (viene del calefón de la terraza del altillo)."),
    (raya("#00838f", 2, "3 3"), "<b>Verde azulado punteado</b>: caño de la <b>bomba</b>, de la cisterna al tanque de arriba."),
    (circulo("#fff", CAFE, r=0.09), "<b>Punto de un artefacto</b> (inodoro, lavamanos, ducha, lavaplatos, lavadora): "
                                    "ver la tabla <b>Puntos de agua</b>."),
    (llave(AZ), "<b>Llave de paso</b> de agua (corta el agua de un baño, de la cocina o de toda la casa)."),
    (circulo(AZ, AZ, r=0.13), "<b>Bajada del tanque</b> (agua fría que viene de arriba)."),
    (circulo(ROJO, ROJO, r=0.13), "<b>Subida/bajada del agua caliente</b> del calefón."),
    (cuadro("#e0f7fa", "#00838f", dash="4 2"), "<b>Cisterna</b> enterrada (llega el agua de SEMAPA)."),
    (circulo("#fff", "#00838f", "B", r=0.18), "<b>Bomba</b> que sube el agua al tanque."),
    (lambda L: L.poly([[-0.18, -0.3], [0.18, -0.3], [0.18, 0.3], [-0.18, 0.3]], f'fill="#fff" stroke="{ROJO}" stroke-width="1.5"'),
     "<b>Calefón</b> a gas (agua caliente de toda la casa).", 0.9, 0.75),
]
LEY_DESAGUE = [
    (raya(CAFE, 4), "<b>Café grueso</b>: caño principal de desagüe (Ø110) que va a la red de la calle."),
    (raya(CAFE, 2, "7 3"), "<b>Café punteado</b>: ramal de cada artefacto, con su diámetro (Ø50 o Ø110). "
                           "Siempre con pendiente hacia la cámara."),
    (cuadro("#efebe9", CAFE, "CI"), "<b>CI = cámara de inspección</b>, con tapa, para destapar."),
    (cuadro("#fff8e1", CAFE, "DG"), "<b>DG = desgrasadora</b> de la cocina (atrapa la grasa antes del desagüe)."),
    (circulo("#efebe9", CAFE, "BV", ancho=1.8), "<b>BV = bajante</b>: caño vertical que baja de los pisos de arriba y "
                                                "sube como ventilación sobre el techo."),
    (circulo(CAFE, CAFE, "BV", col_letra="#fff"), "<b>BV lleno</b>: aquí llega una bajante de arriba (dejar el caño "
                                                  "de espera antes del contrapiso)."),
    (circulo("#fff", CAFE, r=0.10, ancho=1.2, dash="2 1"), "<b>Ventilación</b> del desagüe que sube sobre el techo."),
    (cuadro("#efebe9", CAFE, r=0.10), "<b>Sumidero</b> (rejilla de piso: ducha, lavandería, terraza)."),
    (raya(PLUV, 2.2, "2 3"), "<b>Celeste punteado</b>: agua de <b>lluvia</b>. Va aparte: <b>nunca</b> al desagüe de los baños."),
    (cuadro("#e0f7fa", PLUV), "<b>Pozo de absorción</b> o registro de lluvia."),
    (circulo("#fff", CAFE, r=0.09), "<b>Punto de un artefacto</b> (ver la tabla <b>Puntos de agua</b>)."),
]
LEY_GAS = [
    (raya(GAS, 2.5, "10 4"), "<b>Amarillo punteado</b>: caño de <b>gas natural</b>."),
    (circulo(GAS, GAS, r=0.10), "<b>Fin del caño de gas</b>: cocina o calefón."),
    (llave(GAS), "<b>Llave de paso de gas</b> (una junto a cada artefacto y la general en el medidor)."),
    (cuadro("#fff", "#9a6700", r=0.15), "<b>Rejilla de ventilación</b> (alta y baja) donde hay gas. <b>No se tapa nunca.</b>"),
    (lambda L: L.poly([[-0.18, -0.3], [0.18, -0.3], [0.18, 0.3], [-0.18, 0.3]], f'fill="#fff" stroke="{ROJO}" stroke-width="1.5"'),
     "<b>Calefón</b> (afuera, en la terraza del altillo).", 0.9, 0.75),
    (ducto_aire, "<b>Verde con flecha</b>: ducto de aire (extractor o campana) y hacia dónde sale."),
    (punto("extractor"), "<b>Extractor (E)</b>."),
    (cuadro("#e8f5e9", VERDE, r=0.22, dash="2 2"), "<b>Verde punteado</b>: cielo falso o cajón por donde pasa el ducto."),
    (cuadro("#bdbdbd", "#424242", r=0.18), "<b>Gris</b>: ducto de ladrillo por donde suben los caños (junto a las columnas A2, A3 y A4)."),
]

LETRAS = {"R": "refrigerador", "F": "freezer", "H": "horno eléctrico", "M": "microondas", "C": "campana",
          "LV": "lavavajillas", "L": "lavadora", "LM": "lavadora semiautomática", "S": "secadora", "A": "anafe eléctrico",
          "B": "bomba de agua de la cisterna", "PT": "videoportero (frente de la calle)",
          "CE": "cerradura eléctrica de la puerta peatonal", "FT": "fotocélula del portón",
          "VE": "tubo vacío para un cargador de auto eléctrico (a futuro)", "CAM": "cámara", "T": "termotanque"}


def nombres_amb(nivel):
    return {a["id"]: a.get("nombre", a["id"]) for a in C.ambientes(c, nivel)}


def tabla_puntos_elec(nivel, puntos):
    """Cuántos puntos tiene que haber en cada ambiente (para contarlos en obra)."""
    nom = nombres_amb(nivel)
    puntos = [dict(p, amb=p.get("amb") or donde_id(nivel, *p["pos"])) for p in puntos]
    nom.update({p["amb"]: p["amb"] for p in puntos if p["amb"] not in nom})
    cols = [("Focos de techo", {"luz:techo"}), ("Apliques de pared", {"luz:aplique"}), ("Tiras LED", {"luz:led"}),
            ("Balizas (afuera)", {"luz:baliza"}), ("Teclas", {"interruptor", "conmutador"}), ("Enchufes", {"toma", "toma_ext", "toma_piso"}),
            ("Especiales", {"especial"}), ("Internet/TV", {"datos"}), ("Extractor", {"extractor"}), ("Detector", {"detector"})]
    filas, tot = [], [0] * len(cols)
    orden = [a["id"] for a in C.ambientes(c, nivel)]
    for amb in orden + sorted({p["amb"] for p in puntos} - set(orden)):
        ps = [p for p in puntos if p.get("amb") == amb]
        clave = lambda p: f"luz:{p.get('clase') or 'techo'}" if p["tipo"] == "luz" else p["tipo"]
        n = [sum(clave(p) in ts for p in ps) for _, ts in cols]
        if not any(n):
            continue
        tot = [a + b for a, b in zip(tot, n)]
        celdas = "".join(f"<td class=n>{v or ''}</td>" for v in n)
        filas.append(f"<tr><td>{html.escape(nom.get(amb, 'otros (sin ambiente)'))}</td>{celdas}<td class=blanco></td></tr>")
    filas.append("<tr class=tot><td>TOTAL</td>" + "".join(f"<td class=n>{v}</td>" for v in tot) + "<td></td></tr>")
    cab = "".join(f"<th>{t}</th>" for t, _ in cols)
    return (f"<table class=cuenta><thead><tr><th>Ambiente</th>{cab}<th>¿Está todo? (marcar)</th></tr></thead>"
            f"<tbody>{''.join(filas)}</tbody></table>")


def tabla_especiales(nivel, puntos):
    nom = nombres_amb(nivel)
    filas = ""
    for p in sorted((p for p in puntos if p["tipo"] == "especial"), key=lambda p: (p.get("amb") or "", p.get("etiqueta", ""))):
        et = p.get("etiqueta", "")
        que = p.get("desc") or LETRAS.get(et, "")
        alto = f"{p['alto']:.2f}" if p.get("alto") else "—"
        filas += (f"<tr><td class=letra>{html.escape(et)}</td><td>{html.escape(que)}</td>"
                  f"<td>{html.escape(nom.get(p.get('amb')) or donde(nivel, *p['pos']))}</td><td>{p.get('circuito', '')}</td><td class=n>{alto}</td></tr>")
    if not filas:
        return ""
    return ("<h3>Enchufes especiales (la letra del cuadrado azul)</h3><table><thead><tr><th>Letra</th><th>Para qué</th>"
            f"<th>Ambiente</th><th>Circuito</th><th>Altura</th></tr></thead><tbody>{filas}</tbody></table>")


def tabla_circuitos(nivel, puntos):
    filas = "".join(f"<tr><td class=letra>{r['id']}</td><td>{html.escape(r['nombre'])}</td><td class=n>{r['puntos']}</td>"
                    f"<td class=n>{r['prot']}</td><td class=n>{r['cable']}</td><td class=blanco></td></tr>"
                    for r in I.cuadro_cargas(puntos, nivel))
    return ("<h3>Circuitos (una llave del tablero por cada uno)</h3><table><thead><tr><th>Circuito</th><th>Qué alimenta</th>"
            "<th>Puntos</th><th>Llave (prelim.)</th><th>Cable (prelim.)</th><th>¿Tiene su etiqueta en el tablero?</th></tr>"
            f"</thead><tbody>{filas}</tbody></table>")


def tabla_agua(nivel):
    _, puntos, _ = I.sanitario(c, nivel)
    amb_de = lambda p: donde(nivel, *p["pos"])
    filas = "".join(f"<tr><td>{html.escape(amb_de(p))}</td><td>{html.escape(LETRAS.get(p['nombre'], p['nombre']))}</td>"
                    f"<td class=c>{'✔' if p['af'] else ''}</td><td class=c>{'✔' if p['ac'] else ''}</td>"
                    f"<td class=n>{'Ø' + str(p['desague']) if p.get('desague') else '—'}</td><td class=blanco></td></tr>"
                    for p in sorted(puntos, key=lambda p: amb_de(p)))
    return ("<h3>Puntos de agua (cada artefacto)</h3><table class=cuenta><thead><tr><th>Ambiente</th><th>Artefacto</th>"
            "<th>Agua fría</th><th>Agua caliente</th><th>Desagüe</th><th>¿Está? (marcar)</th></tr></thead>"
            f"<tbody>{filas}</tbody></table>")


def tabla_llaves(nivel):
    cfg = (c.get("instalaciones", {}).get(nivel, {}) or {}).get("sanitario", {}) or {}
    ll = cfg.get("llaves") or []
    if not ll:
        return ""
    filas = "".join(f"<tr><td>{'gas' if l.get('gas') else 'agua'}</td><td>{html.escape(l.get('etiqueta', ''))}</td>"
                    f"<td class=blanco></td></tr>" for l in ll)
    return ("<h3>Llaves de paso</h3><table class=cuenta><thead><tr><th>Tipo</th><th>Cuál</th><th>¿Está y cierra bien?</th></tr>"
            f"</thead><tbody>{filas}</tbody></table>")


# ── planos de instalaciones ────────────────────────────────────────────────────

ALTO_Y = (-2.7, 7.35)                # del retiro norte (luces del muro del lote) al muro sur
CASA_X = (-3.6, 22.4) + ALTO_Y       # la casa con la terraza, el acceso y el patio (pozo de lluvia del fondo)
FRENTE_X = (-16.2, 0.6) + ALTO_Y     # el frente: estacionamiento, jardín, camino, cisterna, portón


def plano(nombre, svg):
    (SALIDA / nombre).write_text(svg, encoding="utf-8")
    return f'<img class="plano inst" src="{nombre}">'


def hojas_plano(seccion, titulo, archivo, generar, ley, extra="", frente=True, nueva=False):
    """Hoja del plano de un nivel (PB: la casa y otra hoja para el frente) con su leyenda debajo."""
    out = []
    nid = archivo.split("-")[1]
    if nid == "pb":
        out.append(hoja(f"{titulo} — la casa", plano(archivo + ".svg", generar(CASA_X)) + leyenda(ley), seccion=seccion, nueva=nueva))
        if frente:
            out.append(hoja(f"{titulo} — el frente (estacionamiento, jardín, camino)",
                            plano(archivo + "-frente.svg", generar(FRENTE_X)) + leyenda(ley), seccion=seccion, nueva=nueva))
    else:
        out.append(hoja(titulo, plano(archivo + ".svg", generar((-1.6, 18.3) + ALTO_Y)) + leyenda(ley), seccion=seccion, nueva=nueva))
    if extra:
        out.append(hoja(f"{titulo} — tablas para revisar", extra, seccion=seccion))
    return out


def nivel_dict(nid):
    return next(n for n in c["niveles"] if n["id"] == nid)


def tiene_gas(nid):
    i = c.get("instalaciones", {}).get(nid, {}) or {}
    s, v = i.get("sanitario") or {}, i.get("ventilacion") or {}
    return bool(s.get("gas") or s.get("gas_ramales") or s.get("rejillas") or v.get("ductos"))


alb = c.get("albanileria", {})
uc = alb.get("union_columnas", {})
hoy = datetime.date.today().isoformat()
ejes_x = " · ".join(f"{k}" for _, k in EX) + " = " + " · ".join(f"{v:.2f}".replace("0.00", "0") for v, _ in EX)
ejes_y = " · ".join(f"{k}" for _, k in EY) + " = " + " · ".join(f"{v:.2f}".replace("0.00", "0") for v, _ in EY)
SEC = {"A": "A · Albañil", "P": "B · Plomero", "G": "C · Gas", "E": "D · Electricista"}
partes = []

# ── portada general ────────────────────────────────────────────────────────────
partes.append(f"""
<section class="hoja portada">
<h1>Casa — cuaderno de obra <span class="vgr">v{VERSION}</span></h1>
<p class="sub">Para el albañil, el plomero, el gasista y el electricista · generado del modelo el {hoy} ·
<b>PRELIMINAR</b>: lo que dice "ingeniero", "YPFB" o "lo define el electricista" se espera a su respuesta</p>
<div class="cols">
<div>
<h2>Qué hay en este cuaderno</h2>
<table class="indice">
<tr><td class="ca">A</td><td><b>Albañil</b>: paso a paso, niveles de piso, plantas, muros y puertas y ventanas de cada piso.</td></tr>
<tr><td class="cp">B</td><td><b>Plomero</b>: agua fría y caliente, desagüe y lluvia de cada piso; puntos de agua y llaves de paso.</td></tr>
<tr><td class="cg">C</td><td><b>Gas</b>: caño de gas, calefón, rejillas y ductos de aire.</td></tr>
<tr><td class="ce">D</td><td><b>Electricista</b>: luces y teclas, enchufes y tablero de cada piso; circuitos y enchufes especiales.</td></tr>
<tr><td>✎</td><td><b>Medidas a tomar</b>: una hoja para anotar lo que se mide en obra.</td></tr>
</table>
<h2>Cada sección tiene</h2>
<ul>
<li>Un <b>paso a paso</b> con casillas ☐ para ir marcando.</li>
<li>Planos con <b>una sola cosa por hoja</b> (por ejemplo: solo luces y teclas) y la <b>leyenda completa abajo</b>.</li>
<li>Una lista <b>"Para el dueño: cómo revisar"</b> y tablas para <b>contar</b> que esté todo, ambiente por ambiente.</li>
</ul>
</div>
<div>
<h2>Cómo leer las medidas (para todos)</h2>
<ul>
<li>Todo se mide desde los <b>EJES DE LAS COLUMNAS</b> (el centro de la columna), no desde la cara.</li>
<li>Ejes a lo largo (de la calle al fondo): <b>{ejes_x}</b> m.</li>
<li>Ejes a lo ancho (del retiro norte al vecino sur): <b>{ejes_y}</b> m.</li>
<li>"eje 3 + 1.65" = a 1.65 m del eje 3 hacia el fondo (o hacia el sur, si es A · B · C).</li>
<li>Las alturas (h1.10, antepecho, dintel) se miden desde el <b>piso terminado</b>.</li>
<li>En los planos el <b>norte</b> está arriba y la calle a la izquierda. Las columnas son los <b>cuadrados rojos</b>.</li>
</ul>
<h2>Nunca (ningún oficio)</h2>
<ul class="no">
<li>Picar columnas o vigas para pasar caños o cables (las losas sí se pueden perforar entre viguetas: lo dijo el ingeniero).</li>
<li>Cavar una zanja más honda que la base de una zapata o de un cimiento.</li>
<li>Tapar caños o cables sin probarlos antes (y sin que el dueño les saque foto).</li>
</ul>
</div>
</div>
</section>""")

if CUAD.get("cambios"):
    items = "".join(f"<li>{html.escape(t)}</li>" for t in CUAD["cambios"])
    partes.append(hoja(f"Qué cambió en la v{VERSION} ({CUAD.get('fecha', '')}) — leer primero", nueva=True, cuerpo=
        f'<ol class="cambios">{items}</ol><div class="alt"><h3>Qué hojas cambiar en el cuaderno impreso</h3>'
        f'<p>{html.escape(CUAD.get("reemplazar", ""))}</p><p>Las hojas nuevas dicen <b>«v{VERSION} · HOJA NUEVA»</b> arriba a la '
        f'derecha. Las viejas del mismo tema se <b>tachan o se sacan</b>, para que nadie trabaje con la medida vieja.</p></div>'))

# ── A · albañil ────────────────────────────────────────────────────────────────
S = SEC["A"]
partes.append(hoja("Ladrillo y forma de asentar", nueva=True, cuerpo=f"""<div class="cols"><div><ul>
<li><b>Ladrillo:</b> {html.escape(alb.get('ladrillo', ''))}, en toda la casa (también los tabiques; no hay drywall).</li>
<li><b>TODOS los muros van de SOGA</b> (~0.15 terminado), también el del frente de planta baja. No hay muros de cabeza.</li>
<li><b>Muros de afuera de soga: AL RAS DE LA CARA EXTERIOR de las columnas</b> (fachada lisa; la columna sobresale ~0.10 hacia adentro).</li>
<li><b>Muros sobre la línea de las columnas: AL RAS DE UNA CARA de la columna</b> (el plano y la tabla de muros dicen
cuál); del otro lado la columna asoma ~10 cm. Los tabiques que no van sobre una línea de columnas, centrados.</li></ul></div><div><ul>
<li>Puertas y ventanas: <b>ancho del hueco terminado</b> (la hoja de la puerta mide ~10 cm menos, por el marco). Ventanas con
<b>antepecho</b> (del piso a la parte de abajo de la ventana) y <b>dintel</b> (del piso a la parte de arriba). Todo está
<b>dibujado en el plano</b> y en la hoja <b>de frente</b>.</li>
<li><b>Junto a una COLUMNA: la puerta o ventana va AL RAS de la columna</b>, sin pedacito de ladrillo (no agarra el marco).
Junto a otro muro: pegada a él, o con al menos 12.5 cm.</li>
<li>Antes de marcar: <b>comprobar con cinta</b> las distancias entre columnas. Si algo no coincide en más de 2 cm,
<b>parar y avisar</b>.</li>
<li>Los muros en <b style="color:#b00">rojo</b> en las tablas: <b>NO LEVANTAR TODAVÍA</b> (esperan al ingeniero).</li>
</ul></div></div>""" + revisar([
    "Con cinta, la distancia de cada muro al eje de la columna más cercana (tabla <b>muros</b>): no más de 2 cm de diferencia.",
    "El ancho de cada hueco de puerta y ventana (tabla <b>puertas y ventanas</b>) y la altura del antepecho.",
    "Que las fachadas queden lisas: el muro al ras de la cara de afuera de las columnas.",
    "Chicotes de fierro cada 3 hiladas al lado de cada columna (verlos antes de que revoque).",
    "Que la última hilada quede apretada contra la viga o la losa, sin hueco.",
    "Con un nivel de burbuja largo: muros a plomo y pisos con la pendiente de la hoja de niveles.",
]), seccion=S))
partes.append(hoja("Paso a paso (1 de 2)", pasos(
    paso(1, "Antes de empezar: medir y avisar", [
        "Medir con cinta las distancias entre ejes de columnas en cada piso y compararlas con los ejes de la portada.",
        "Con manguera de nivel: cuánto más alto que la <b>vereda</b> está el piso de PB (losa o contrapiso), la tierra del "
        "<b>patio</b> y la del <b>retiro norte</b>.",
        "Cuánto <b>cuelga cada viga</b> bajo la losa (ver la hoja de medidas). De eso dependen los dinteles altos y el cielo falso.",
        "Anotar todo en la hoja <b>Medidas a tomar</b> y pasársela al dueño.",
    ], "maestro"),
    paso(2, "Bajo el piso de planta baja (antes del contrapiso)", [
        "Zanjas de desagüe y cámaras según el plano <b>B · Plomero — desagüe y lluvia</b>, <b>junto con el plomero</b>.",
        "La cámara de la entrada (junto al acceso) se hace <b>antes</b> del piso del acceso, con tapa hermética de 0.60 × 0.60.",
        "Por dónde cruzan los caños el cimiento del eje A (junto a A3 y A4): <b>esperar al ingeniero</b>.",
        "Cerca de las zapatas de B1, C1 y del muro sur: antes, <b>pozo de prueba</b> para ver su profundidad.",
    ], "albañil + plomero"),
    paso(3, "Marcar los muros de planta baja", [
        "Tirar hilos por los ejes de columnas. Marcar cada muro con tiza según la tabla <b>Planta baja — muros</b>.",
        "Marcar los huecos de puertas y ventanas según la tabla de <b>puertas y ventanas</b> (el ancho es del hueco terminado).",
        "Las puertas y ventanas que están junto a una columna, AL RAS de la columna (sin pedacito de ladrillo).",
    ], "maestro"),
    paso(4, "Levantar los muros de planta baja", [
        "Soga en todo, también el muro oeste (el frente, eje 1). Los de afuera, al ras de la cara exterior de las columnas.",
        f"<b>Unión con las columnas:</b> {html.escape(uc.get('chicotes', ''))}.",
        "Dintel de hormigón sobre cada puerta y ventana.",
        "<b>Ductos de caños</b> de ladrillo en los rincones de las columnas A2 (escalera/depósito), A3 (baño) y A4 (estudio), "
        "como están dibujados (gris) en los planos del plomero, con tapa de registro donde lo indica el plano.",
        "Puerta de entrada (1.05, pivotante) y su vidrio: altos hasta 2.60; "
        "ventana del living de 3.00: <b>antes medir cuánto cuelgan las vigas</b> del eje 1 y del eje A.",
        f"<b>Última hilada:</b> {html.escape(uc.get('remate_losa', ''))}.",
    ], "albañil"),
), seccion=S))
partes.append(hoja("Paso a paso (2 de 2)", pasos(
    paso(5, "Antes de revocar: electricista y plomero", [
        "Canaletas para caños y cables <b>solo en el ladrillo</b>, nunca en columnas ni vigas.",
        "Las losas SÍ se pueden perforar para los pases de caños (respuesta del ingeniero), entre viguetas y con camisa.",
        "Prueba de los caños de agua y de desagüe <b>antes</b> de tapar.",
    ], "electricista + plomero"),
    paso(6, "Revoque", [
        f"{html.escape(uc.get('malla_revoque', '')).capitalize()}.",
        "Fachadas: blanco, piedra en el muro del living, madera y gris según los alzados (lo confirma el dueño antes de "
        "comprar material).",
    ], "albañil"),
    paso(7, "Contrapiso y pisos de planta baja", [
        "Piso terminado de <b>toda la planta baja a +0.20</b>, sin desniveles; ducha 1.5 cm más baja, con rejilla lineal.",
        "Afuera: retiro y patio a +0.05 (caen 1.5 % alejándose de la casa), umbral de piedra de la entrada a +0.20, "
        "escalón de 0.15 en la puerta del depósito. Ver la hoja <b>Niveles de piso</b>.",
        "Si al medir (paso 1) los niveles no dan, <b>se corren todos juntos</b>: avisar al dueño.",
    ], "albañil"),
    paso(8, "Primer piso", [
        "Igual que la planta baja: marcar, levantar, chicotes, dinteles, ductos de A3 (blancos) y A4 (Baño 1).",
        "<b>Esperan al ingeniero</b> (en rojo en la tabla): muros del vestidor, del Baño 2, del vestíbulo, el muro entre los dos "
        "cuartos y todo lo que va sobre el volado del frente (inodoro y ducha de la suite).",
        "Baños: membrana impermeable en todo el piso (sube 0.20 en los muros y 1.80 en la ducha), prueba de 48 h con agua.",
    ], "albañil"),
    paso(9, "Altillo", [
        "<b>Esperar al ingeniero</b> antes de empezar: si se prolongan las columnas (hay fierros de espera en A2 y A3), "
        "el muro sur del departamento, el muro del dormitorio y la base del tanque.",
        "Después, igual que los otros pisos.",
    ], "albañil + ingeniero"),
    paso("✗", "Todavía NO hacer", [
        "Muro de la calle, portón, pilares y muros del frente (esperan al ingeniero: cimiento, columnetas, viga del riel).",
        "Cisterna nueva: primero el pozo de prueba junto al vecino del sur y la respuesta del ingeniero.",
        "Cajón de bajantes de la esquina suroeste: esperar al ingeniero (dónde se ancla).",
    ]),
), seccion=S))
niv = sorted((c.get("niveles_piso") or {}).get("pb", []), key=lambda n: n["cota"])
filas = "".join(f"<tr><td><b>{html.escape(n['etiqueta'])}</b></td><td class=n>{n['cota']:+.2f}</td>"
                f"<td class=nota>{html.escape(corto(n.get('nota', ''), 260))}</td></tr>" for n in niv)
(SALIDA / "obra-bodega-planta.svg").write_text(O.bodega_planta_svg(c), encoding="utf-8")
(SALIDA / "obra-bodega-corte1.svg").write_text(O.bodega_corte_svg(c, 5.125, "CORTE 1 — lado del living (bajo el tramo de 10, que sube)"), encoding="utf-8")
(SALIDA / "obra-bodega-corte2.svg").write_text(O.bodega_corte_svg(c, 6.325, "CORTE 2 — lado del baño (bajo el tramo de 6, que llega arriba)"), encoding="utf-8")
partes.append(hoja("Planta baja — BODEGA debajo de la escalera: cómo es", nueva=True, seccion=S, cuerpo=
    '<div class="bod"><div><img src="obra-bodega-planta.svg"><p class=lee>En cada escalón: <b>número · altura libre '
    'debajo</b> (desde el piso). Verde: se entra de pie. Naranja: agachado. Líneas azules: dónde están los cortes.</p></div>'
    '<div><img src="obra-bodega-corte1.svg"><img src="obra-bodega-corte2.svg"></div></div>' + pasos(
    paso(1, "Qué es", [
        "Una <b>bodega cerrada</b> debajo de la escalera, entre las columnas A2, A3, B2 y B3 (2.40 × 2.53 por dentro).",
        "Se entra <b>solo desde el retiro norte</b>, por una puerta de <b>0.80 × 1.85</b> al ras de la columna A3, que abre "
        "hacia afuera, con un escalón de 0.15. <b>No se comunica con la casa.</b>",
    ]),
    paso(2, "Qué alto queda adentro", [
        "<b>Bajo el descanso</b> (la parte de la puerta): <b>1.92</b> libres, se entra de pie.",
        "<b>Lado del baño</b> (bajo el tramo de 6 que llega al primer piso): el techo <b>sube</b> de 1.92 a 2.48.",
        "<b>Lado del living</b> (bajo el tramo de 10 que sube desde el hall): el techo <b>baja</b> de 1.54 a 0.98 junto al "
        "muro del hall: ahí va el estante bajo de herramientas.",
    ]),
    paso(3, "Muros (todos de soga)", [
        "<b>Norte</b> (al retiro): con la puerta, al ras de afuera de las columnas.",
        "<b>Del lado del hall</b> (eje B): al ras de la cara NORTE de B2 y B3; <b>sube hasta tocar la escalera por debajo</b>, "
        "siguiendo la pendiente (corte 1: llega a ~0.98; corte 2: ~2.48). Arriba se cierra apretado contra la losa de la escalera.",
        "<b>Del lado del living</b> (eje 2) y <b>del lado del baño</b> (eje 3): al ras de la escalera, hasta tocarla.",
    ], "albañil"),
    paso(4, "Adentro y los cajones del hall", [
        "Piso de cemento. Un <b>aplique</b> en el muro (a 1.80) y un enchufe junto a la puerta. En el rincón de A2 sube el "
        "<b>ducto del agua caliente</b>: no taparlo.",
        "<b>Cajones hacia el hall</b> (opcional): debajo de los escalones 4 a 6, del lado del hall, un hueco de ~0.55 de ancho, "
        "0.40 de alto y 1.10 de fondo. Más al sur la escalera baja a menos de 0.40. Antes, ver si debajo de los primeros "
        "escalones hay relleno.",
    ], "albañil + carpintero"),
)))
partes.append(hoja("Niveles de piso — planta baja y exteriores (PROPUESTOS, falta medir)",
                   "<p>±0.00 = vereda pública frente al portón. Todo se mide con manguera de nivel desde ahí.</p>"
                   f"<table><thead><tr><th>Lugar</th><th>Cota</th><th>Cómo</th></tr></thead><tbody>{filas}</tbody></table>",
                   seccion=S))
# Recorte de cada plano del albañil (m): PB sin el frente; altillo sin la terraza.
RECORTE = {"pb": (-3.0, 19.8, -3.6, 9.2), "p1": (-4.3, 19.8, -3.6, 9.2), "altillo": (0.9, 19.8, -3.6, 7.1)}
LEE_PLANO = (f"<p class=lee><b>Cómo leer:</b> <b style='color:{O.ROJO}'>V</b> ventana, <b style='color:{O.ROJO}'>P</b> puerta, "
             f"<b style='color:{O.ROJO}'>C</b> corrediza, con <b style='color:{O.AZUL}'>ancho × alto</b> y <b style='color:{O.AZUL}'>ant.</b> "
             "= antepecho (del piso terminado a la parte de abajo de la ventana). Las puertas: <b>hueco</b> (ancho que deja el albañil) y "
             "<b>alto</b>. Las <b>cadenas de medidas</b> van de cara a cara (de columnas y de muros), no de eje a eje; en azul, los huecos. "
             "Columnas: cuadrados rojos (naranja punteado = las que se prolongan en el altillo).</p>")
for nid, nombre in NIVELES:
    nv = nivel_dict(nid)
    entre = {ab["id"]: lados(nid, ab) for ab in O.de_obra(c, nid)}
    (SALIDA / f"obra-albanil-{nid}.svg").write_text(O.planta_obra(c, nv, *RECORTE[nid], donde=entre), encoding="utf-8")
    partes.append(hoja(f"{nombre} — plano del albañil (piso terminado +{COTA[nid]:.2f})",
                       f'<img class="plano alb" src="obra-albanil-{nid}.svg">' + LEE_PLANO, seccion=S,
                       nueva=True if nid == "altillo" else "luego"))
    partes.append(hoja(f"{nombre} — puertas y ventanas VISTAS DE FRENTE (alturas desde el piso terminado)",
                       O.frentes_html(c, nid, lambda ab, n=nid: lados(n, ab)), seccion=S,
                       nueva=True if nid == "altillo" else "luego"))
    ms = lineas(nid)
    partes.append(hoja(f"{nombre} — muros de ladrillo (medidos desde los ejes)",
                       "<table><thead><tr><th>Dónde va el muro</th><th>Desde / hasta</th><th>Largo</th><th>Ladrillo</th>"
                       f"<th>Huecos en ese muro</th></tr></thead><tbody>{''.join(fila_muro(nid, m) for m in ms)}</tbody></table>",
                       seccion=S, nueva=True if nid == "altillo" else "luego"))
    partes.append(hoja(f"{nombre} — puertas, ventanas y pasos",
                       "<table class=vanos><thead><tr><th>Tipo</th><th>Entre</th><th>Dónde</th><th>Ancho</th><th>Antepecho</th>"
                       f"<th>Dintel</th><th>Cómo</th></tr></thead><tbody>{tabla_vanos(nid)}</tbody></table>", seccion=S,
                       nueva=True if nid == "altillo" else "luego"))

# Techo del altillo (2026-10-16): planta y corte para el albañil, con lo que falta decidir antes de techar.
tq = (c.get("techos") or {}).get("tanque") or {}
TOPE = max(m["cota_tope"] for m in (c.get("techos") or {}).get("antepechos", []))
(SALIDA / "obra-techo-altillo.svg").write_text(O.planta_techo_obra(c), encoding="utf-8")
(SALIDA / "obra-techo-corte.svg").write_text(O.corte_techo_svg(c), encoding="utf-8")
partes.append(hoja("Altillo — TECHO: planta (cotas aproximadas, desde el nivel ±0.00 de la vereda)",
                   '<img class="plano alb" src="obra-techo-altillo.svg">' + "<p class=lee>Departamento: calamina a un agua que "
                   "cae al NORTE (el agua sale al retiro norte, no a la franja), escondida detrás del antepecho; canaleta por dentro "
                   "del antepecho norte hasta la bajante BP3 (esquina A5, por la cara del patio); una gárgola de rebalse por si se "
                   "tapa. La franja tiene su propio sumidero a la bajante BP2 (esquina C5). Terraza: techo propio de calamina sobre fierro a la vista que cae al "
                   "frente, sobre postes en A1 y B1. Las cotas son desde la vereda (el piso del altillo está a +6.60).</p>",
                   seccion=S, nueva=True))
partes.append(hoja("Altillo — TECHO: corte norte–sur y paso a paso",
                   '<img class="plano corte" src="obra-techo-corte.svg">' + pasos(
    paso(1, "Muros de afuera del departamento", [
        f"Suben <b>de una sola vez hasta +{TOPE:.2f}</b> ({TOPE - 6.60:.2f} sobre el piso del altillo): la parte de arriba es el "
        "<b>antepecho</b> que tapa el techo. No cortar el muro a la altura del techo.",
        "Columnas y viga de encadenado (dónde y de qué tamaño): <b>lo dice el ingeniero</b>.",
        "Arriba del antepecho, remate con pendiente hacia adentro, para que el agua no manche la fachada.",
    ], "albañil + ingeniero"),
    paso(2, "Lo que se deja en los muros mientras se levantan", [
        "<b>Muro NORTE:</b> UNA gárgola de rebalse a ~+9.20, cerca de la esquina A5 (x ~16.20), al ras y con goterón, con "
        "caída hacia afuera (diámetro: el plomero). En el muro sur ya NO van gárgolas.",
        "<b>Muro oeste (el de la terraza, eje 2):</b> anclajes para las vigas de fierro del techo de la terraza a ~+9.80 "
        "(los define el herrero).",
        "<b>Esquina A5 (norte, lado del patio):</b> la canaleta sale por el antepecho a la bajante <b>BP3</b>, que baja por la "
        "cara del patio en un cajón pegado a la columna. <b>Esquina C5:</b> el sumidero de la franja sale por el antepecho a la "
        "bajante <b>BP2</b>. Las dos van enterradas a un pozo de absorción en el patio.",
    ], "albañil"),
    paso(3, "Lo que atraviesa el techo", [
        "Caños del tanque (ducto de A3) y <b>ventilación Ø110</b> del desagüe (ducto de A4): con babeta y sombrerete.",
        "La <b>canaleta pasa junto a la base del tanque</b> (en el borde bajo): que el agua no se estanque contra la base "
        "(tubo por debajo o canaleta en dos tramos: el ingeniero).",
        "2 <b>tubos vacíos de 1\"</b> desde el techo (junto al tanque) hasta el tablero, por el montante de B2: para paneles "
        "solares a futuro.",
        f"El <b>tanque</b> va sobre su propia base a +{tq.get('cota_base', 10.5):.2f}, junto a A3: la dimensiona el ingeniero.",
    ], "albañil + plomero"),
    paso("?", "Falta decidir ANTES de techar", [
        "<b>Ingeniero:</b> columnas y viga de encadenado del altillo; cómo se apoya la calamina (propuesta: vigas de norte a "
        "sur sobre el eje A y el eje B, con un volado corto hasta el muro sur, para que ese muro no cargue; nada sobre los "
        "muros del baño y del dormitorio); base del tanque y paso de la canaleta.",
        "<b>Dueño:</b> calefón solar o a gas (el solar lleno pesa ~300–400 kg y va sobre el techo o la terraza).",
        "<b>Dueño:</b> altura del cielo raso (en el dibujo, ~2.55 libres: tiene que quedar debajo de la canaleta).",
    ], "dueño + ingeniero"),
), seccion=S, nueva=True))

# ── B · plomero ────────────────────────────────────────────────────────────────
S = SEC["P"]
partes.append(hoja("Paso a paso del plomero", pasos(
    paso(1, "Bajo el piso de planta baja (antes del contrapiso)", [
        "Caño principal de desagüe (café grueso) y cámaras de inspección (CI) por el retiro norte, con pendiente hacia la calle.",
        "Dejar los caños de espera donde llegan las bajantes de arriba (BV lleno) y bajo cada artefacto de planta baja.",
        "Lluvia (celeste) por su lado: <b>nunca</b> conectada al desagüe de los baños ni de la cocina.",
        "Desgrasadora (DG) de la cocina antes de que su desagüe llegue al caño principal.",
    ], "plomero + albañil"),
    paso(2, "Ductos y pases", [
        "Caños verticales <b>dentro de los ductos de ladrillo</b> junto a las columnas A2 (agua caliente), A3 (agua fría, bomba, "
        "ventilación) y A4 (bajante): antes de que el albañil los cierre.",
        "Pases por las losas entre viguetas, con camisa (el ingeniero dijo que sí). Nunca por columnas ni vigas.",
    ], "plomero"),
    paso(3, "Agua fría y caliente", [
        "Agua fría: SEMAPA → cisterna → bomba → tanque de arriba → baja por el ducto de A3 a cada piso.",
        "Agua caliente: del calefón de la terraza del altillo, baja por el ducto de A2.",
        "Una <b>llave de paso</b> por baño, cocina y lavado, más la general de cada piso (tabla <b>Llaves de paso</b>).",
    ], "plomero"),
    paso(4, "Probar antes de tapar", [
        "<b>Prueba de presión</b> del agua fría y caliente con manómetro, con el dueño presente: la aguja no tiene que bajar.",
        "<b>Prueba del desagüe con agua</b>: llenar y ver que no gotee ninguna unión, y que el agua corra a la cámara.",
        "Baños de arriba: membrana en todo el piso y <b>prueba de 48 h con agua</b> antes del piso.",
    ], "plomero + dueño"),
) + revisar([
    "En cada artefacto, contar las salidas con la tabla <b>Puntos de agua</b>: fría (azul), caliente (rojo) y desagüe.",
    "Lo normal: <b>caliente a la izquierda</b> y fría a la derecha, mirando el artefacto.",
    "Abrir y cerrar cada <b>llave de paso</b>: que corte el agua de lo que dice su nombre.",
    "Ver la prueba de presión con sus propios ojos y sacar <b>foto de los caños antes de que los tapen</b> (para saber dónde no clavar).",
    "Echar un balde de agua en cada desagüe y sumidero: que corra rápido y llegue a la cámara (destapar la tapa y mirar).",
    "Las tapas de las cámaras (CI) quedan a la vista y se pueden abrir.",
    "Que ningún caño cruce una columna o una viga.",
]) + alternativa("Alternativa (todavía NO): bajante de A4 por AFUERA, solo si el arquitecto de la obra o la municipalidad lo aceptan", [
    "<b>Hoy se hace ADENTRO</b>: ducto de ladrillo en el rincón de A4 (baño del altillo, Baño 1 y estudio), pases por las dos "
    "losas entre viguetas y cruce del cimiento del eje A hasta la cámara nueva del retiro.",
    "<b>Por qué no va afuera:</b> el retiro norte quedó en 2.00 justo (la norma dice \"incluido voladizo\"); un cajón de ~0.25 "
    "lo deja en 1.75 y puede traer observaciones. Además la fachada norte deja de ser lisa.",
    "<b>Si lo aceptan, para el plomero cambia:</b> no perfora losas (cada ramal sale por el muro norte, que es ladrillo); no "
    "cruza el cimiento del eje A (baja pegada a A4 directo a la cámara del retiro); tapa de registro y ventilación quedan "
    "afuera, sin entrar a los cuartos; el caño va dentro de un cajón que lo proteja del sol.",
    "<b>Para el albañil:</b> no se hace el ducto en los tres ambientes; el estudio recupera ese rincón.",
    "<b>Antes de hacerlo, avisar al dueño:</b> se actualizan los planos del plomero de los tres pisos.",
]), seccion=S))
for nid, nombre in NIVELES:
    n = nivel_dict(nid)
    partes += hojas_plano(S, f"{nombre} — agua fría y caliente", f"obra-{nid}-agua",
                          lambda r, n=n: I.plano_sanitario(c, n, "agua", r, leyenda_svg=False)[0], LEY_AGUA,
                          tabla_agua(nid) + tabla_llaves(nid))
    partes += hojas_plano(S, f"{nombre} — desagüe y lluvia", f"obra-{nid}-desague",
                          lambda r, n=n: I.plano_sanitario(c, n, "desague", r, leyenda_svg=False)[0], LEY_DESAGUE)

# ── C · gas ────────────────────────────────────────────────────────────────────
S = SEC["G"]
partes.append(hoja("Paso a paso del gas", pasos(
    paso(1, "Quién lo hace", [
        "Solo un <b>gasista matriculado</b>. La instalación la aprueba <b>YPFB</b> antes de habilitar el gas.",
        "El recorrido de estos planos es una <b>propuesta</b>: se lo muestra a YPFB y él dice si lo acepta.",
        "Calcular el <b>consumo total</b> (calefón de toda la casa + cocina de planta baja + anafe del altillo) para el "
        "medidor y el diámetro de cada tramo.",
    ], "gasista + YPFB"),
    paso(2, "Recorrido propuesto", [
        "Del medidor (pilar sur del frente) <b>enterrado</b> por el retiro norte y el patio hasta la cocina: sale a ~0.60 junto a la columna C5.",
        "Al <b>calefón</b>: sube por un compartimiento propio junto al cajón gris del frente y sigue por dentro de los "
        "antepechos de la terraza del altillo. <b>No entra a la casa</b> (solo el ramal de la cocina del altillo, abajo).",
        "Si YPFB no acepta esa subida: plan B, enterrado hasta A2 y subida en vaina ventilada dentro del ducto de la escalera.",
        "<b>Cocina del altillo</b> (anafe a gas): ramal con su <b>llave en la terraza</b>, junto a la del calefón. Sube a ~2.20, "
        "cruza el muro por encima del ducto de A2, va <b>empotrado</b> en el muro norte de la escalera (sin uniones adentro), "
        "rodea la columna A3 sin picarla y baja por el muro de la cocina hasta el anafe, a 0.20 del piso bajo la mesada. "
        "Rejilla baja bajo el anafe (muro norte) y alta en el muro sur del comedor; detector de gas.",
    ], "gasista"),
    paso(3, "Ventilación", [
        "Rejillas alta y baja en la cocina (no se tapan nunca).",
        "Campana: ducto propio hacia el patio, lo más alto posible. El caño de gas nunca dentro del cajón de la campana.",
        "Detector de gas en la cocina (está en los planos del electricista).",
    ], "gasista + albañil"),
) + revisar([
    "Que haya una <b>llave de paso de gas</b> junto a la cocina y otra junto al calefón, y la general en el medidor.",
    "Ver la <b>prueba de hermeticidad</b> del gasista y pedir el papel de aprobación de YPFB.",
    "Las rejillas de la cocina quedan abiertas y sin muebles delante.",
    "El caño de gas no pasa por adentro de la casa (salvo el último tramo a la cocina).",
    "Con agua y jabón en cada unión, con el gas abierto: no tiene que hacer burbujas.",
]) + alternativa("Cocina del altillo — otra ruta posible: POR EL TECHO (la eligen el gasista y YPFB)", [
    "Desde la llave de la terraza <b>sube</b> por el muro hasta arriba del antepecho, <b>cruza a la vista</b> sobre el techo "
    "del departamento y <b>baja empotrado</b> dentro del muro norte hasta el anafe.",
    "<b>A favor:</b> casi todo al aire libre y fácil de revisar; no pasa por la escalera ni rodea las columnas A2 y A3.",
    "<b>En contra:</b> ~10–11 m (la de los planos ~6 m); tiene que rodear la <b>base del tanque</b> (x 6.40–7.80, sobre el muro "
    "norte) y no mezclarse con la <b>canaleta</b>; al sol: pintura y grapas firmes, que no se pise al limpiar el techo.",
    "<b>Nunca</b> por el espacio entre la calamina y el cielo raso (hueco cerrado: ahí el gas se acumula).",
]), seccion=S))
for nid, nombre in NIVELES:
    if tiene_gas(nid):
        n = nivel_dict(nid)
        partes += hojas_plano(S, f"{nombre} — gas y ventilación", f"obra-{nid}-gas",
                              lambda r, n=n: I.plano_sanitario(c, n, "gas", r, leyenda_svg=False)[0], LEY_GAS)

# ── D · electricista ───────────────────────────────────────────────────────────
S = SEC["E"]
partes.append(hoja("Paso a paso del electricista", pasos(
    paso(1, "Marcar antes de picar", [
        "Marcar con tiza en la pared cada caja de luz, tecla, enchufe e internet según los planos, a la altura indicada (h).",
        "Recorrer las marcas con el dueño <b>antes de picar</b> (con los muebles en mente: cama, TV, mesón).",
    ], "electricista + dueño"),
    paso(2, "Tubos", [
        "Canaletas <b>solo en el ladrillo</b>, nunca en columnas ni vigas. Por las losas, entre viguetas.",
        "Los tubos que suben a los pisos de arriba van por el <b>montante</b> junto a la columna B2 (ya dejaron tubos en su cara sur).",
        "Internet, TV, cámaras, portero y alarma en <b>tubos propios</b> (línea violeta), separados de los de 220 V.",
        "Tubo vacío con guía donde el plano lo pide (cargador de auto eléctrico a futuro).",
    ], "electricista"),
    paso(3, "Tablero y cables", [
        "Tablero de planta baja (TD) y subtablero del primer piso en el hall junto a B2.",
        "Una llave por circuito, cada una con su <b>etiqueta</b> (tabla de circuitos). Diferencial donde dice \"con diferencial\".",
        "Puesta a tierra con jabalina y cable verde a todos los enchufes.",
        "Las llaves y los cables de las tablas son <b>preliminares</b>: los define el electricista (NB 777).",
    ], "electricista"),
    paso(4, "Probar", [
        "Cada tecla prende sus luces (línea naranja). Las Sc desde los dos lugares.",
        "Cada enchufe con un probador. Apagar cada llave del tablero y ver que se corta su circuito.",
        "El botón de prueba de cada diferencial tiene que cortar la luz.",
    ], "electricista + dueño"),
) + revisar([
    "En cada ambiente, <b>contar</b> luces, teclas y enchufes con la tabla <b>Cuántos puntos hay</b> de cada piso.",
    "Con cinta, la <b>altura</b> de las cajas que dicen h (por ejemplo h1.10 = 1.10 m del piso terminado).",
    "Que cada tecla prenda las luces que le une la línea naranja.",
    "Que los <b>enchufes especiales</b> (cuadrado azul con letra) estén donde va su aparato: refrigerador, horno, lavadora...",
    "Que cada llave del tablero tenga su etiqueta con el número de circuito (C1, C2...).",
    "Sacar <b>foto de las paredes con los tubos antes de revocar</b> (para saber después dónde no perforar).",
    "Que no haya picado ninguna columna ni viga.",
]), seccion=S))
for nid, nombre in NIVELES:
    n = nivel_dict(nid)
    _, puntos = I.plano_electrico(c, n, leyenda_svg=False)
    partes += hojas_plano(S, f"{nombre} — luces y teclas", f"obra-{nid}-luces",
                          lambda r, n=n: I.plano_electrico(c, n, "luces", r, leyenda_svg=False)[0], LEY_LUCES, nueva=True)
    partes += hojas_plano(S, f"{nombre} — enchufes, tablero y especiales", f"obra-{nid}-tomas",
                          lambda r, n=n: I.plano_electrico(c, n, "tomas", r, leyenda_svg=False)[0], LEY_TOMAS,
                          "<h3>Cuántos puntos hay en cada ambiente</h3>" + tabla_puntos_elec(nid, puntos)
                          + tabla_especiales(nid, puntos) + tabla_circuitos(nid, puntos))

# ── medidas a tomar ────────────────────────────────────────────────────────────
medir = [
    ("Distancias entre ejes de columnas, a lo largo (1–2, 2–3, 3–4, 4–5)", "4.40 · 2.65 · 4.15 · 5.70"),
    ("Distancias entre ejes de columnas, a lo ancho (A–B, B–C)", "2.68 · 3.99"),
    ("Tamaño real de las columnas", "0.25 × 0.25"),
    ("Espesor de las losas", "?"),
    ("Piso de PB (losa o contrapiso) sobre la vereda", "piso terminado +0.20"),
    ("Tierra del patio sobre la vereda", "+0.05 terminado"),
    ("Tierra del retiro norte sobre la vereda", "+0.05 terminado"),
    ("Cuánto cuelga la viga del eje 1 (A1–B1 y B1–C1)", "puerta de entrada y su vidrio a 2.60"),
    ("Cuánto cuelga la viga del eje A entre A1 y A2", "ventana del living a 2.10"),
    ("Cuánto cuelga la viga del eje A entre A2 y A3 (escalera)", "ventana de la escalera a 2.90"),
    ("Cuánto cuelgan las vigas sobre el lavado, el baño y el pasillo de PB", "cielo falso a 2.70 (si > 0.18 → 2.50)"),
    ("Cuánto sale el volado del primer piso al frente y su espesor en la punta", "1.00"),
    ("Distancia de la casa al lindero norte (Lote 105) y al del fondo", "2.00 · 5.00"),
    ("Fondo del descanso de la escalera y distancia de B2 al primer escalón", "?"),
    ("Fierros de espera arriba de las columnas (¿cuáles tienen?)", "vistos en A2 y A3"),
]
filas = "".join(f"<tr><td>{html.escape(q)}</td><td class=sup>{html.escape(s)}</td><td class=blanco></td></tr>" for q, s in medir)
partes.append(hoja("Medidas a tomar en obra (anotar y devolver al dueño)",
                   f"<table class=medir><thead><tr><th>Qué medir</th><th>Lo que supone el plano</th><th>Medido en obra</th></tr>"
                   f"</thead><tbody>{filas}</tbody></table>", seccion="✎"))

ESTILO = f"""<style>
@page {{ size: A3 landscape; margin: 12mm; }}
body {{ font-family: Helvetica, Arial, sans-serif; color: #111; margin: 0; }}
.hoja {{ page-break-after: always; }}
.hoja:last-child {{ page-break-after: auto; }}
h1 {{ font-size: 30px; margin: 0 0 4px; }} .sub {{ color: #444; margin: 0 0 18px; font-size: 15px; }}
h2 {{ font-size: 19px; margin: 14px 0 6px; }} .tit {{ border-bottom: 3px solid #111; padding-bottom: 4px; }}
h3 {{ font-size: 16px; margin: 12px 0 6px; }}
.secc {{ display: inline-block; background: #111; color: #fff; font-size: 14px; padding: 2px 10px; border-radius: 4px;
  margin-right: 12px; vertical-align: 2px; }}
.cols {{ display: grid; grid-template-columns: 1fr 1fr; gap: 36px; }}
li, p {{ font-size: 15px; margin: 5px 0; line-height: 1.35; }}
ul.no li::marker {{ content: "✗  "; color: #c00; }}
table.indice td {{ font-size: 15px; border: none; padding: 6px 8px; }}
table.indice td:first-child {{ font-weight: bold; font-size: 20px; text-align: center; width: 36px; color: #fff; background: #111; }}
.pasos {{ display: grid; grid-template-columns: 1fr 1fr; gap: 14px 30px; }}
.paso {{ display: flex; gap: 12px; break-inside: avoid; }}
.paso .num {{ flex: 0 0 38px; height: 38px; border-radius: 50%; background: #111; color: #fff; font-size: 20px;
  font-weight: bold; display: flex; align-items: center; justify-content: center; }}
.paso h3 {{ font-size: 18px; margin: 6px 0 4px; }} .quien {{ font-size: 12px; font-weight: normal; color: #555;
  border: 1px solid #999; border-radius: 10px; padding: 1px 8px; margin-left: 10px; }}
.chk {{ margin: 4px 0 4px 1.3em; text-indent: -1.3em; }}
.revisar {{ border: 3px solid #2e7d32; background: #f1f8e9; border-radius: 8px; padding: 6px 16px 10px; margin-top: 16px;
  break-inside: avoid; }}
.revisar h3 {{ color: #1b5e20; }}
.alt {{ border: 3px dashed #b28704; background: #fffde7; border-radius: 8px; padding: 6px 16px 10px; margin-top: 14px;
  break-inside: avoid; }}
.alt h3 {{ color: #7a5c00; }}
.plano {{ width: 100%; max-height: 245mm; object-fit: contain; }}
.plano.inst {{ max-height: 200mm; }}
.leyenda {{ border-top: 2px solid #111; margin-top: 4px; break-inside: avoid; }}
.leyenda h3 {{ margin: 6px 0; }}
.leyg {{ display: grid; grid-template-columns: repeat(4, 1fr); gap: 3px 18px; }}
.ley {{ display: flex; align-items: center; gap: 8px; font-size: 11.5px; line-height: 1.25; }}
.ley > div:first-child {{ flex: 0 0 58px; text-align: center; }}
svg.sim {{ display: block; margin: auto; }}
table {{ width: 100%; border-collapse: collapse; font-size: 13px; }}
th, td {{ border: 1px solid #999; padding: 5px 7px; vertical-align: top; text-align: left; }}
th {{ background: #eee; }} td.n {{ text-align: right; white-space: nowrap; }} td.c {{ text-align: center; }}
td.nota {{ font-size: 11px; color: #333; }} td.letra {{ font-weight: bold; text-align: center; width: 50px; }}
tr {{ page-break-inside: avoid; }} thead {{ display: table-header-group; }}
tr.tot td {{ font-weight: bold; background: #f5f5f5; }}
table.cuenta td.blanco {{ width: 18%; }}
.amb {{ font-size: 11px; color: #555; }}
tr.espera td {{ background: #fdeaea; }} .aviso {{ color: #b00; font-weight: bold; margin-top: 3px; }}
table.medir td {{ font-size: 15px; height: 34px; }} td.sup {{ color: #555; }} td.blanco {{ width: 30%; }}
.ver {{ float: right; font-size: 13px; font-weight: normal; color: #555; border: 1px solid #999; border-radius: 10px;
  padding: 2px 10px; margin-top: 4px; }}
.ver.nueva {{ color: #fff; background: #b71c1c; border-color: #b71c1c; font-weight: bold; }}
.vgr {{ font-size: 22px; color: #fff; background: #b71c1c; border-radius: 6px; padding: 2px 10px; vertical-align: 5px; }}
ol.cambios li {{ font-size: 17px; margin: 10px 0; line-height: 1.4; }}
.plano.alb {{ max-height: 228mm; }}
.plano.corte {{ max-height: 120mm; display: block; margin: 0 auto 6px; }}
.bod {{ display: grid; grid-template-columns: 0.85fr 1fr; gap: 14px; }} .bod img {{ width: 100%; max-height: 92mm; object-fit: contain; display: block; }}
.bod > div:first-child img {{ max-height: 150mm; }}
p.lee {{ font-size: 13px; margin: 2px 0; }}
.tarjetas {{ display: grid; grid-template-columns: repeat(5, 1fr); gap: 8px; }}
.tarjeta {{ border: 2px solid #333; border-radius: 6px; padding: 4px 6px; break-inside: avoid; }}
.tarjeta .cod {{ font-size: 28px; font-weight: bold; color: #b71c1c; float: left; margin: -2px 8px 0 0; }}
.tarjeta .que {{ font-size: 12px; min-height: 30px; }} .tarjeta .como {{ font-size: 11px; color: #333; }}
svg.frente {{ display: block; max-width: 100%; height: auto; margin: 2px auto; }}
</style>"""


def escribir(nombre, titulo, hojas):
    h = SALIDA / f"{nombre}.html"
    h.write_text(f'<!doctype html><html lang="es"><head><meta charset="utf-8"><title>{titulo}</title>{ESTILO}</head>'
                 f'<body>{"".join(hojas)}</body></html>', encoding="utf-8")
    print("ok", h.relative_to(RAIZ))
    return h


HTML = escribir("cuaderno-obra", f"Casa — cuaderno de obra v{VERSION}", partes)
sitio_obra.generar(HOJAS, partes[0], ESTILO, VERSION, CUAD.get("fecha", hoy), SALIDA, [
    ("Fachada norte", "fachada-norte.svg", "🏠"), ("Fachada sur", "fachada-sur.svg", "🏠"),
    ("Fachada este (patio)", "fachada-este.svg", "🏠"), ("Fachada oeste (frente)", "fachada-oeste.svg", "🏠"),
    ("Planta baja", "planta-pb.svg", "🗺️"), ("Primer piso", "planta-p1.svg", "🗺️"), ("Altillo", "planta-altillo.svg", "🗺️"),
    ("Techos", "planta-techos.svg", "🗺️"), ("Vista 3D", "visor-3d.html", "🧊")])
if "--solo-sitio" in sys.argv:
    sys.exit(0)
CORTO = escribir(f"cuaderno-obra-v{VERSION}-hojas-nuevas", f"Casa — hojas nuevas v{VERSION}", NUEVAS)
chrome = CHROME if pathlib.Path(CHROME).exists() else shutil.which("google-chrome") or shutil.which("chromium")
if not chrome:
    print("sin Chrome: abrir el HTML e imprimir a PDF (A3 apaisado)")
    sys.exit(0)
for h in (HTML, CORTO):
    pdf = h.with_suffix(".pdf")
    subprocess.run([chrome, "--headless", "--disable-gpu", "--no-pdf-header-footer", "--allow-file-access-from-files",
                    f"--print-to-pdf={pdf}", h.as_uri()], check=True, capture_output=True)
    print("ok", pdf.relative_to(RAIZ))
