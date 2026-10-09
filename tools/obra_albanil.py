"""Cuaderno para el maestro albañil (A3 apaisado): paso a paso, medidas a tomar, niveles, plantas, muros y vanos.

Genera salida/obra-albanil.html y, si hay Google Chrome, salida/obra-albanil.pdf. Se corre con `make albanil`
(después de `make build`, porque usa las plantas SVG de salida/).
"""
import datetime
import html
import pathlib
import re
import shutil
import subprocess
import sys

import casa as C

RAIZ = pathlib.Path(__file__).resolve().parent.parent
SALIDA = RAIZ / "salida"
CHROME = "/Applications/Google Chrome.app/Contents/MacOS/Google Chrome"

c = C.cargar()
est = c["estructura"]
EX = sorted((v, k) for k, v in est["ejes_x"].items())
EY = sorted((v, k) for k, v in est["ejes_y"].items())
NIVELES = [("pb", "Planta baja"), ("p1", "Primer piso"), ("altillo", "Altillo")]
COTA = {n["id"]: n.get("cota", 0) for n in c["niveles"]}

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
        tipo += " · al ras EXTERIOR de las columnas"
    aviso = esperar(nivel, m["eje"], m["val"], m["de"], m["a"])
    clase = ' class="espera"' if aviso else ""
    aviso = f'<div class="aviso">✗ NO LEVANTAR TODAVÍA: {html.escape(aviso)} → ingeniero</div>' if aviso else ""
    otro = EX if m["eje"] == "y" else EY
    vanos = "<br>".join(f"{nombre_vano(v[4])} {v[3] - v[2]:.2f} ({ref(v[2], otro)} a {ref(v[3], otro)})"
                        for v in m["vanos"]) or "—"
    return (f"<tr{clase}><td>{html.escape(donde)}<div class=amb>{html.escape(' · '.join(m['ambs']))}</div>{aviso}</td>"
            f"<td>{html.escape(tramo)}</td><td class=n>{m['a'] - m['de']:.2f}</td><td>{tipo}</td><td>{vanos}</td></tr>")


def tabla_vanos(nivel):
    filas = []
    for ab in C.aberturas(c, nivel):
        if ab.get("en_cerco") or ab["tipo"] == "porton":
            continue
        (x0, y0), (x1, y1) = ab["de"], ab["a"]
        ancho = abs(x1 - x0) + abs(y1 - y0)
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
                      f"<tr><td>{nombre_vano(ab)}</td><td>{html.escape(ab.get('id', ''))}</td><td>{html.escape(donde)}</td>"
                      f"<td class=n><b>{ancho:.2f}</b></td><td class=n>{ap}</td><td class=n>{dint}</td>"
                      f"<td class=nota>{html.escape(corto(ab.get('nota', '')))}</td></tr>"))
    filas.sort(key=lambda f: (f[0], f[1]))
    return "".join(f[2] for f in filas)


def svg_casa(nivel, desde_x=-3.6):
    """Planta del nivel recortada desde `desde_x` (m) hacia el fondo: deja afuera el frente, que todavía no se hace."""
    s = (SALIDA / f"planta-{nivel}.svg").read_text(encoding="utf-8")
    vb = re.search(r'viewBox="0 0 ([\d.]+) ([\d.]+)"', s)
    losa = re.search(r'<polygon points="([\d.]+),[\d.]+ ([\d.]+),', s)  # contorno de la losa = huella_casa
    if not (vb and losa):
        return f"planta-{nivel}.svg"
    hx0, _, hx1, _ = C.huella_casa(c)
    px0, px1 = float(losa.group(1)), float(losa.group(2))
    x = max(0.0, px0 + (desde_x - hx0) * (px1 - px0) / (hx1 - hx0))
    s = s.replace(vb.group(0), f'viewBox="{x:.1f} 0 {float(vb.group(1)) - x:.1f} {vb.group(2)}"', 1)
    destino = f"obra-albanil-{nivel}.svg"
    (SALIDA / destino).write_text(s, encoding="utf-8")
    return destino


def hoja(titulo, cuerpo, clase=""):
    return f'<section class="hoja {clase}"><h2 class="tit">{titulo}</h2>{cuerpo}</section>'


def lista(items, clase=""):
    return f'<ul class="{clase}">' + "".join(f"<li>{i}</li>" for i in items) + "</ul>"


def paso(n, titulo, items, quien=""):
    q = f'<span class="quien">{quien}</span>' if quien else ""
    return (f'<div class="paso"><div class="num">{n}</div><div><h3>{titulo}{q}</h3>'
            + "".join(f'<p class="chk">☐ {i}</p>' for i in items) + "</div></div>")


alb = c.get("albanileria", {})
uc = alb.get("union_columnas", {})
hoy = datetime.date.today().isoformat()
ejes_x = " · ".join(f"{k}" for _, k in EX) + " = " + " · ".join(f"{v:.2f}".replace("0.00", "0") for v, _ in EX)
ejes_y = " · ".join(f"{k}" for _, k in EY) + " = " + " · ".join(f"{v:.2f}".replace("0.00", "0") for v, _ in EY)
partes = []

# 1. Portada
partes.append(f"""
<section class="hoja portada">
<h1>Casa — cuaderno del maestro albañil</h1>
<p class="sub">Paso a paso, medidas, niveles, muros, puertas y ventanas · generado del modelo el {hoy} ·
<b>PRELIMINAR</b>: lo que dice "ingeniero" se espera a su respuesta</p>
<div class="cols">
<div>
<h2>Qué hay en este cuaderno</h2>
<ol>
<li><b>Paso a paso</b>: el orden de los trabajos, con casillas para ir marcando.</li>
<li><b>Medidas a tomar</b>: una hoja para anotar lo que se mide en obra (se la devuelve al dueño).</li>
<li><b>Niveles de piso</b> de la planta baja y del patio, retiro y frente.</li>
<li>Por cada piso: <b>planta</b>, <b>muros</b> (dónde va cada uno, medido desde los ejes) y <b>puertas y ventanas</b>.</li>
<li>Planta baja: <b>plano de desagües</b> (para las zanjas, junto con el plomero).</li>
</ol>
<h2>Ladrillo y forma de asentar</h2>
<ul>
<li><b>Ladrillo:</b> {html.escape(alb.get('ladrillo', ''))}, en toda la casa (también los tabiques; no hay drywall).</li>
<li><b>Casi todos los muros van de SOGA</b> (~0.15 terminado).</li>
<li><b>Living: los muros de afuera van de CABEZA</b> (~0.25, al ras de las columnas).</li>
<li><b>Muros de afuera de soga: AL RAS DE LA CARA EXTERIOR de las columnas</b> (fachada lisa; la columna sobresale ~0.10 hacia adentro).</li>
<li><b>Muros de adentro:</b> centrados en la línea indicada.</li>
</ul>
</div>
<div>
<h2>Cómo leer las medidas</h2>
<ul>
<li>Todo se mide desde los <b>EJES DE LAS COLUMNAS</b> (el centro de la columna), no desde la cara.</li>
<li>Ejes a lo largo (de la calle al fondo): <b>{ejes_x}</b> m.</li>
<li>Ejes a lo ancho (del retiro norte al vecino sur): <b>{ejes_y}</b> m.</li>
<li>"eje 3 + 1.65" = a 1.65 m del eje 3 hacia el fondo (o hacia el sur, si es A · B · C).</li>
<li>Puertas y ventanas: <b>ancho del hueco terminado</b>. Ventanas con <b>antepecho</b> (del piso a la parte de abajo
de la ventana) y <b>dintel</b> (del piso a la parte de arriba), desde el piso terminado.</li>
<li><b>Junto a una columna o a otro muro, dejar siempre al menos 12.5 cm de muro</b> para que entre el marco.</li>
<li>Antes de marcar: <b>comprobar con cinta</b> las distancias entre columnas. Si algo no coincide en más de 2 cm,
<b>parar y avisar</b>.</li>
</ul>
<h2>Nunca</h2>
<ul class="no">
<li>Picar columnas o vigas para pasar caños o cables.</li>
<li>Cavar una zanja más honda que la base de una zapata o de un cimiento.</li>
<li>Levantar un muro marcado "NO LEVANTAR TODAVÍA" sin la respuesta del ingeniero.</li>
</ul>
</div>
</div>
</section>""")

# 2. Paso a paso
pasos_a = [
    paso(1, "Antes de empezar: medir y avisar", [
        "Medir con cinta las distancias entre ejes de columnas en cada piso y compararlas con los ejes de la portada.",
        "Con manguera de nivel: cuánto más alto que la <b>vereda</b> está el piso de PB (losa o contrapiso), la tierra del "
        "<b>patio</b> y la del <b>retiro norte</b>.",
        "Cuánto <b>cuelga cada viga</b> bajo la losa (ver la hoja de medidas). De eso dependen los dinteles altos y el cielo falso.",
        "Anotar todo en la hoja <b>Medidas a tomar</b> y pasársela al dueño.",
    ], "maestro"),
    paso(2, "Bajo el piso de planta baja (antes del contrapiso)", [
        "Zanjas de desagüe y cámaras según el plano de desagües, <b>junto con el plomero</b>. Pendiente de los caños: 2 %.",
        "La cámara de la entrada (junto al acceso) se hace <b>antes</b> del piso del acceso, con tapa hermética de 0.60 × 0.60.",
        "Por dónde cruzan los caños el cimiento del eje A (junto a A3 y A4): <b>esperar al ingeniero</b>.",
        "Cerca de las zapatas de B1, C1 y del muro sur: antes, <b>pozo de prueba</b> para ver su profundidad.",
    ], "albañil + plomero"),
    paso(3, "Marcar los muros de planta baja", [
        "Tirar hilos por los ejes de columnas. Marcar cada muro con tiza según la tabla <b>Planta baja — muros</b>.",
        "Marcar los huecos de puertas y ventanas según la tabla de <b>puertas y ventanas</b> (el ancho es del hueco terminado).",
        "Comprobar que junto a cada columna queden al menos 12.5 cm de muro para el marco.",
    ], "maestro"),
    paso(4, "Levantar los muros de planta baja", [
        "Soga en casi todo; de cabeza solo los muros de afuera del living. Los de afuera, al ras de la cara exterior de las columnas.",
        f"<b>Unión con las columnas:</b> {html.escape(uc.get('chicotes', ''))}.",
        "Dintel de hormigón sobre cada puerta y ventana.",
        "<b>Ductos de caños</b> de ladrillo en los rincones de las columnas A2 (escalera/depósito), A3 (baño) y A4 (estudio), "
        "como están dibujados en la planta, con tapa de registro donde indica el plano.",
        "Puerta de entrada (1.05, pivotante) y ranura del living (0.30): altas hasta 2.60; "
        "ventana del living de 3.00: <b>antes medir cuánto cuelgan las vigas</b> del eje 1 y del eje A.",
        f"<b>Última hilada:</b> {html.escape(uc.get('remate_losa', ''))}.",
    ], "albañil"),
]
pasos_b = [
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
    ], ""),
]
partes.append(hoja("Paso a paso (1 de 2)", '<div class="pasos">' + "".join(pasos_a) + "</div>"))
partes.append(hoja("Paso a paso (2 de 2)", '<div class="pasos">' + "".join(pasos_b) + "</div>"))

# 3. Medidas a tomar
medir = [
    ("Distancias entre ejes de columnas, a lo largo (1–2, 2–3, 3–4, 4–5)", "4.40 · 2.65 · 4.15 · 5.70"),
    ("Distancias entre ejes de columnas, a lo ancho (A–B, B–C)", "2.68 · 3.99"),
    ("Tamaño real de las columnas", "0.25 × 0.25"),
    ("Espesor de las losas", "?"),
    ("Piso de PB (losa o contrapiso) sobre la vereda", "piso terminado +0.20"),
    ("Tierra del patio sobre la vereda", "+0.05 terminado"),
    ("Tierra del retiro norte sobre la vereda", "+0.05 terminado"),
    ("Cuánto cuelga la viga del eje 1 (A1–B1 y B1–C1)", "puerta de entrada y ranura a 2.60"),
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
                   f"</thead><tbody>{filas}</tbody></table>"))

# 4. Niveles
niv = sorted((c.get("niveles_piso") or {}).get("pb", []), key=lambda n: n["cota"])
filas = "".join(f"<tr><td><b>{html.escape(n['etiqueta'])}</b></td><td class=n>{n['cota']:+.2f}</td>"
                f"<td class=nota>{html.escape(corto(n.get('nota', ''), 260))}</td></tr>" for n in niv)
partes.append(hoja("Niveles de piso — planta baja y exteriores (PROPUESTOS, falta medir)",
                   "<p>±0.00 = vereda pública frente al portón. Todo se mide con manguera de nivel desde ahí.</p>"
                   f"<table><thead><tr><th>Lugar</th><th>Cota</th><th>Cómo</th></tr></thead><tbody>{filas}</tbody></table>"))

# 5. Por nivel
for nid, nombre in NIVELES:
    svg = svg_casa(nid) if nid == "pb" else f"planta-{nid}.svg"
    partes.append(hoja(f"{nombre} — planta (piso terminado +{COTA[nid]:.2f})", f'<img class="plano" src="{svg}">'))
    if nid == "pb":
        partes.append(hoja("Planta baja — desagües y caños bajo el piso (con el plomero)",
                           '<img class="plano" src="planta-pb-sanitario.svg">'))
    ms = lineas(nid)
    partes.append(hoja(f"{nombre} — muros de ladrillo (medidos desde los ejes)",
                       "<table><thead><tr><th>Dónde va el muro</th><th>Desde / hasta</th><th>Largo</th><th>Ladrillo</th>"
                       f"<th>Huecos en ese muro</th></tr></thead><tbody>{''.join(fila_muro(nid, m) for m in ms)}</tbody></table>"))
    partes.append(hoja(f"{nombre} — puertas, ventanas y pasos",
                       "<table class=vanos><thead><tr><th>Tipo</th><th>Código</th><th>Dónde</th><th>Ancho</th><th>Antepecho</th>"
                       f"<th>Dintel</th><th>Nota</th></tr></thead><tbody>{tabla_vanos(nid)}</tbody></table>"))

HTML = SALIDA / "obra-albanil.html"
HTML.write_text(f"""<!doctype html><html lang="es"><head><meta charset="utf-8"><title>Casa — cuaderno del albañil</title>
<style>
@page {{ size: A3 landscape; margin: 12mm; }}
body {{ font-family: Helvetica, Arial, sans-serif; color: #111; margin: 0; }}
.hoja {{ page-break-after: always; }}
.hoja:last-child {{ page-break-after: auto; }}
h1 {{ font-size: 30px; margin: 0 0 4px; }} .sub {{ color: #444; margin: 0 0 18px; font-size: 15px; }}
h2 {{ font-size: 19px; margin: 14px 0 6px; }} .tit {{ border-bottom: 3px solid #111; padding-bottom: 4px; }}
.cols {{ display: grid; grid-template-columns: 1fr 1fr; gap: 36px; }}
li, p {{ font-size: 15px; margin: 5px 0; line-height: 1.35; }}
ul.no li::marker {{ content: "✗  "; color: #c00; }}
.pasos {{ display: grid; grid-template-columns: 1fr 1fr; gap: 14px 30px; }}
.paso {{ display: flex; gap: 12px; break-inside: avoid; }}
.paso .num {{ flex: 0 0 38px; height: 38px; border-radius: 50%; background: #111; color: #fff; font-size: 20px;
  font-weight: bold; display: flex; align-items: center; justify-content: center; }}
.paso h3 {{ font-size: 18px; margin: 6px 0 4px; }} .quien {{ font-size: 12px; font-weight: normal; color: #555;
  border: 1px solid #999; border-radius: 10px; padding: 1px 8px; margin-left: 10px; }}
.chk {{ margin: 4px 0 4px 1.3em; text-indent: -1.3em; }}
.plano {{ width: 100%; max-height: 245mm; object-fit: contain; }}
table {{ width: 100%; border-collapse: collapse; font-size: 13px; }}
th, td {{ border: 1px solid #999; padding: 5px 7px; vertical-align: top; text-align: left; }}
th {{ background: #eee; }} td.n {{ text-align: right; white-space: nowrap; }} td.nota {{ font-size: 11px; color: #333; }}
tr {{ page-break-inside: avoid; }} thead {{ display: table-header-group; }}
.amb {{ font-size: 11px; color: #555; }}
tr.espera td {{ background: #fdeaea; }} .aviso {{ color: #b00; font-weight: bold; margin-top: 3px; }}
table.medir td {{ font-size: 15px; height: 34px; }} td.sup {{ color: #555; }} td.blanco {{ width: 30%; }}
</style></head><body>{''.join(partes)}</body></html>""", encoding="utf-8")
print("ok", HTML.relative_to(RAIZ))

chrome = CHROME if pathlib.Path(CHROME).exists() else shutil.which("google-chrome") or shutil.which("chromium")
if not chrome:
    print("sin Chrome: abrir el HTML e imprimir a PDF (A3 apaisado)")
    sys.exit(0)
PDF = SALIDA / "obra-albanil.pdf"
subprocess.run([chrome, "--headless", "--disable-gpu", "--no-pdf-header-footer", "--allow-file-access-from-files",
                f"--print-to-pdf={PDF}", HTML.as_uri()], check=True, capture_output=True)
print("ok", PDF.relative_to(RAIZ))
