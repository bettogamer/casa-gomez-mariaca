"""Plano del albañil (cuaderno de obra v2): sin muebles, con cada puerta y ventana rotulada en GRANDE y cadenas de
medidas de cara a cara (columna → ladrillo → ventana → ...), y las aberturas dibujadas de frente con sus alturas.

Pedido del maestro (2026-10-16): "ver los datos en una tabla no ayuda; los valores tienen que estar en el plano, y los
números no muy chicos". Lo usa tools/cuaderno_obra.py.
"""
from html import escape

import casa as C
from render_svg import Lienzo, dibujar_aberturas, dibujar_columnas, dibujar_escalera, dibujar_muros

TAM_COTA = 13       # px: medidas de las cadenas
TAM_ROTULO = 14     # px: código y medidas de cada abertura
AZUL = "#0d47a1"
ROJO = "#b71c1c"
SIN_ROTULO = ("vano", "porton")
LETRA = {"ventana": "V", "puerta": "P", "corrediza": "C", "puerta_corrediza": "P"}


def de_obra(casa, nid):
    return [ab for ab in C.aberturas(casa, nid) if ab["tipo"] not in SIN_ROTULO and not ab.get("en_cerco")]


def codigos(casa, nid):
    """V1, V2… / P1, P2… / C1… recorriendo la planta de noroeste a sureste (mismo código en plano, frentes y tabla)."""
    cuenta, out = {}, {}
    for ab in sorted(de_obra(casa, nid), key=lambda a: (round(min(a["de"][1], a["a"][1]), 1), min(a["de"][0], a["a"][0]))):
        L = LETRA.get(ab["tipo"], "A")
        cuenta[L] = cuenta.get(L, 0) + 1
        out[ab["id"]] = f"{L}{cuenta[L]}"
    return out


def ancho(ab):
    (x0, y0), (x1, y1) = ab["de"], ab["a"]
    return abs(x1 - x0) + abs(y1 - y0)


def alturas(ab):
    """(antepecho, borde de arriba) desde el piso terminado."""
    if ab["tipo"] == "ventana":
        return ab.get("antepecho", 1.0), ab.get("alto", 2.10)
    return 0.0, ab.get("alto", 2.10)


def fmt(v):
    """Metros con 2 decimales, o 3 si hay medio centímetro (0.125)."""
    t = f"{v:.3f}"
    return t if t[-1] != "0" else f"{v:.2f}"


HALO = 'stroke="#fff" stroke-width="4" stroke-linejoin="round" paint-order="stroke" '


def _rotar(L, x, y, t, tam, estilo, vertical):
    a, b = L.p(x, y)
    rot = f' transform="rotate(-90 {a:.1f} {b:.1f})"' if vertical else ""
    L.add(f'<text x="{a:.1f}" y="{b:.1f}" font-size="{tam}" text-anchor="middle"{rot} {estilo}>{escape(t)}</text>')


def _rect_muro(m):
    (x0, y0), (x1, y1) = m["de"], m["a"]
    g = m["grosor"] / 2
    x0, x1, y0, y1 = x0 + m["dx"], x1 + m["dx"], y0 + m["dy"], y1 + m["dy"]
    if abs(x0 - x1) < 0.01:
        return x0 - g, min(y0, y1), x0 + g, max(y0, y1)
    return min(x0, x1), y0 - g, max(x0, x1), y0 + g


def lineas_de_muro(casa, nid):
    """Muros rectos (corridos) con sus aberturas: [{vertical, val, lo, hi, centro (eje real), grosor, vanos}]."""
    segs = []
    for m in C.muros(casa, nid):
        if m["tipo"] != "ladrillo":
            continue
        (x0, y0), (x1, y1) = m["de"], m["a"]
        v = abs(x0 - x1) < 0.01
        segs.append((v, round(x0 if v else y0, 3), min(y0, y1) if v else min(x0, x1), max(y0, y1) if v else max(x0, x1),
                     m["grosor"], (x0 + m["dx"]) if v else (y0 + m["dy"]), None))
    for ab in C.aberturas(casa, nid):
        if ab.get("en_cerco") or ab["tipo"] == "porton":
            continue
        g, sx, sy = C.seccion_muro(casa, nid, ab["de"], ab["a"])
        (x0, y0), (x1, y1) = ab["de"], ab["a"]
        v = abs(x0 - x1) < 0.01
        segs.append((v, round(x0 if v else y0, 3), min(y0, y1) if v else min(x0, x1), max(y0, y1) if v else max(x0, x1),
                     g, (x0 + sx) if v else (y0 + sy), ab))
    grupos = {}
    for s in segs:
        grupos.setdefault((s[0], s[1]), []).append(s)
    out = []
    for (v, val), ss in grupos.items():
        ss.sort(key=lambda s: s[2])
        corrida = []
        for s in ss + [None]:
            if s is None or (corrida and s[2] > max(c[3] for c in corrida) + 0.02):
                if corrida and any(c[6] is not None and c[6]["tipo"] != "vano" for c in corrida):
                    muro = [c for c in corrida if c[6] is None] or corrida
                    out.append({"vertical": v, "val": val, "lo": min(c[2] for c in corrida), "hi": max(c[3] for c in corrida),
                                "centro": muro[0][5], "grosor": muro[0][4],
                                "vanos": [c[6] for c in corrida if c[6] is not None and c[6]["tipo"] != "vano"]})
                corrida = []
            if s is not None:
                corrida.append(s)
    return out


def puntos_cadena(casa, nid, ln):
    """Puntos (a lo largo del muro) donde cambia algo: caras de columnas, caras de muros que llegan, bordes de vanos."""
    m = casa["estructura"]["seccion_columna"] / 2
    v, val, lo, hi = ln["vertical"], ln["val"], ln["lo"], ln["hi"]
    pts, macizos = set(), []
    prolongar = (casa["estructura"].get("prolongar_columnas") or {}).get(nid)
    for col in C.columnas(casa):
        if prolongar is not None and col["id"] not in prolongar:
            continue
        a, b = (col["y"], col["x"]) if v else (col["x"], col["y"])     # a: a lo largo del muro; b: de través
        if abs(b - val) < m + 0.01 and lo - 0.2 < a < hi + 0.2:
            pts |= {round(a - m, 3), round(a + m, 3)}
            macizos.append((a - m, a + m))
    for mu in C.muros(casa, nid):
        if mu["tipo"] != "ladrillo":
            continue
        x0, y0, x1, y1 = _rect_muro(mu)
        (p0, p1), (q0, q1) = ((y0, y1), (x0, x1)) if v else ((x0, x1), (y0, y1))
        cruza = q0 - 0.01 <= val + 0.13 and q1 + 0.01 >= val - 0.13      # llega hasta este muro
        perpendicular = (abs(mu["de"][1] - mu["a"][1]) < 0.01) == v       # por su dirección, no por su forma
        if perpendicular and cruza and lo - 0.2 < (p0 + p1) / 2 < hi + 0.2 and p1 - p0 < 0.3:
            pts |= {round(p0, 3), round(p1, 3)}
            macizos.append((p0, p1))
    for ab in ln["vanos"]:
        (x0, y0), (x1, y1) = ab["de"], ab["a"]
        a, b = (min(y0, y1), max(y0, y1)) if v else (min(x0, x1), max(x0, x1))
        pts |= {round(a, 3), round(b, 3)}
    pts = sorted(p for p in pts if lo - 0.2 <= p <= hi + 0.2)
    return pts, macizos


def lado_libre(casa, nid, ln):
    """+1/-1: hacia dónde va la cadena (afuera si el muro da afuera; si no, hacia el ambiente más grande)."""
    v, c = ln["vertical"], ln["centro"]
    mid = (ln["lo"] + ln["hi"]) / 2
    hx0, hy0, hx1, hy1 = C.huella_casa(casa)
    mejor, area = 1, -1
    for s in (1, -1):
        x, y = (c + s * 0.4, mid) if v else (mid, c + s * 0.4)
        amb = C.ambiente_en(casa, nid, x, y)
        if amb is None or amb["tipo"] == "exterior" or not (hx0 < x < hx1 and hy0 < y < hy1):
            return s
        a = C.area(amb["poly"])
        if a > area:
            mejor, area = s, a
    return mejor


def dibujar_cadena(L, casa, nid, ln):
    pts, macizos = puntos_cadena(casa, nid, ln)
    if len(pts) < 2:
        return
    v, g = ln["vertical"], ln["grosor"]
    s = lado_libre(casa, nid, ln)
    d = ln["centro"] + s * (g / 2 + 0.42)        # línea de cota
    P = (lambda t, o: (o, t)) if v else (lambda t, o: (t, o))
    estilo = 'stroke="#333" stroke-width="1"'
    L.linea(*P(pts[0], d), *P(pts[-1], d), estilo)
    for t in pts:
        L.linea(*P(t, ln["centro"] + s * (g / 2 + 0.05)), *P(t, d + s * 0.08), 'stroke="#777" stroke-width="0.6"')
        a, b = P(t, d)
        L.linea(a - 0.07, b + 0.07 if v else b + 0.07, a + 0.07, b - 0.07, 'stroke="#333" stroke-width="1.6"')
    vanos = []
    for ab in ln["vanos"]:
        (x0, y0), (x1, y1) = ab["de"], ab["a"]
        vanos.append((min(y0, y1), max(y0, y1)) if v else (min(x0, x1), max(x0, x1)))
    ocupado = {1: [], -1: []}       # fila afuera (1) y fila entre la línea y el muro (-1): tramos ya usados

    def lugar(centro, w, prefer):
        for fila in (prefer, -prefer):
            if all(centro + w / 2 < a0 or centro - w / 2 > a1 for a0, a1 in ocupado[fila]):
                return fila, centro
        fila = prefer
        fin = max(a1 for a0, a1 in ocupado[fila])
        return fila, fin + w / 2 + 0.03

    for a, b in zip(pts, pts[1:]):
        largo = b - a
        if largo < 0.04:
            continue
        es_vano = any(abs(a - p) < 0.01 and abs(b - q) < 0.01 for p, q in vanos)
        es_macizo = any(a >= p - 0.01 and b <= q + 0.01 for p, q in macizos)
        if es_macizo and not es_vano:
            continue                    # columna o muro que llega: no se rotula (es el ancho de la columna o del muro)
        col = AZUL if es_vano else "#111"
        peso = 'font-weight="bold" ' if es_vano else ""
        txt = fmt(largo)
        # afuera de la línea de cota; las medidas chicas (no entra el número) prefieren ir entre la línea y el muro
        w = len(txt) * TAM_COTA * 0.58 / 50 + 0.06
        fila, centro = lugar((a + b) / 2, w, -1 if largo < w else 1)
        ocupado[fila].append((centro - w / 2, centro + w / 2))
        k = s * fila
        if v:
            tx, ty = d + (0.30 if k > 0 else -0.12), centro
        else:
            tx, ty = centro, d + (0.30 if k > 0 else -0.10)
        _rotar(L, tx, ty, txt, TAM_COTA, f'{HALO}{peso}fill="{col}"', v)


def dibujar_rotulos(L, casa, nid):
    """Código + medidas de cada abertura, del mismo lado que la cadena y más afuera (afuera de la casa si el muro da afuera)."""
    cod = codigos(casa, nid)
    for ln in lineas_de_muro(casa, nid):
        s = lado_libre(casa, nid, ln)
        v, g = ln["vertical"], ln["grosor"]
        for ab in ln["vanos"]:
            (x0, y0), (x1, y1) = ab["de"], ab["a"]
            t = ((y0 + y1) / 2) if v else ((x0 + x1) / 2)
            ap, arriba = alturas(ab)
            w = ancho(ab)
            if ab["tipo"] == "ventana":
                lineas = [f"{fmt(w)} × {fmt(arriba - ap)}", f"ant. {fmt(ap)}"]
            elif ab["tipo"] == "corrediza":
                lineas = [f"{fmt(w)} × {fmt(arriba)}", "desde el piso"]
            else:
                lineas = [f"hueco {fmt(w)}", f"alto {fmt(arriba)}"]
            filas = [(cod[ab["id"]], f'{HALO}font-weight="bold" fill="{ROJO}"', TAM_ROTULO + 4)] + \
                    [(l, f'{HALO}fill="{AZUL}"', TAM_ROTULO) for l in lineas]
            cara = ln["centro"] + s * g / 2
            if v:
                x = cara + s * 1.70
                for k, (txt, est, tam) in enumerate(filas):
                    L.texto(x, t - 0.22 + k * 0.33, txt, tam, est)
            else:
                y0r = cara + (1.22 if s > 0 else -1.62)
                for k, (txt, est, tam) in enumerate(filas):
                    L.texto(t, y0r + k * 0.33, txt, tam, est)


def ejes_lejos(L, casa, x0, y0, x1, y1, izq):
    """Ejes con sus burbujas lejos del muro (deja lugar a cadenas y rótulos). `izq`: dónde van las burbujas A·B·C."""
    est = casa["estructura"]
    roja = 'stroke="#d33" stroke-width="1" stroke-dasharray="8 4 2 4"'
    for nombre, x in est["ejes_x"].items():
        L.linea(x, y0 - 2.75, x, y1 + 0.4, roja)
        bx, by = L.p(x, y0 - 3.05)
        L.add(f'<circle cx="{bx:.1f}" cy="{by:.1f}" r="15" fill="#fff" stroke="#333" stroke-width="1.5"/>')
        L.texto(x, y0 - 3.05 + 0.12, nombre, 16, 'font-weight="bold"')
    for nombre, y in est["ejes_y"].items():
        L.linea(izq + 0.3, y, x1 + 0.4, y, roja)
        bx, by = L.p(izq, y)
        L.add(f'<circle cx="{bx:.1f}" cy="{by:.1f}" r="15" fill="#fff" stroke="#333" stroke-width="1.5"/>')
        L.texto(izq, y + 0.12, nombre, 16, 'font-weight="bold"')
    xs = sorted(est["ejes_x"].values())
    yc = y0 - 2.45
    L.linea(xs[0], yc, xs[-1], yc, 'stroke="#555" stroke-width="0.8"')
    for x in xs:
        L.linea(x - 0.08, yc + 0.08, x + 0.08, yc - 0.08, 'stroke="#555" stroke-width="1.5"')
    for a, b in zip(xs, xs[1:]):
        L.texto((a + b) / 2, yc - 0.1, f"{b - a:.2f} entre ejes", 12, 'fill="#555"')


def rotular_ambientes_simple(L, casa, nid):
    for a in C.ambientes(casa, nid):
        if a["tipo"] == "exterior":
            continue
        cx, cy = a.get("etiqueta") or C.centroide(a["poly"])
        L.texto(cx, cy, a["nombre"].upper(), 12, 'font-weight="bold" fill="#9aa"')


def planta_obra(casa, nivel, desde_x=None, hasta_x=None, desde_y=None, hasta_y=None):
    nid = nivel["id"]
    ambs = C.ambientes(casa, nid)
    hx0, hy0, hx1, hy1 = C.huella_casa(casa)
    pts = [p for a in ambs for p in a["poly"]] + [[hx0, hy0], [hx1, hy1]]
    x0, y0 = min(p[0] for p in pts), min(p[1] for p in pts)
    x1, y1 = max(p[0] for p in pts), max(p[1] for p in pts)
    import render_svg
    margen, render_svg.MARGEN = render_svg.MARGEN, 3.6
    L = Lienzo(x0, y0, x1, y1)
    render_svg.MARGEN = margen
    for a in ambs:      # rellenos muy claros: que resalten muros y números
        L.poly(a["poly"], 'fill="#f4f8fb" stroke="none"' if a["tipo"] != "exterior" else 'fill="#f3f7ef" stroke="#999" stroke-width="1" stroke-dasharray="6 3"')
    dibujar_escalera(L, casa, nid)
    ejes_lejos(L, casa, x0, y0, x1, y1, (desde_x if desde_x is not None else x0 - 3.0) + 0.45)
    rotular_ambientes_simple(L, casa, nid)
    dibujar_muros(L, casa, nid)
    dibujar_aberturas(L, casa, nid, rotulos=False)
    dibujar_columnas(L, casa, nid)
    for ln in lineas_de_muro(casa, nid):
        dibujar_cadena(L, casa, nid, ln)
    dibujar_rotulos(L, casa, nid)
    return L.svg(f"{nivel['nombre']} — albañil", desde_x=desde_x, hasta_x=hasta_x, desde_y=desde_y, hasta_y=hasta_y)


# ── aberturas de frente ─────────────────────────────────────────────────────────

def frente_svg(ab, codigo, esc=52, alto_muro=2.60):
    """Una puerta o ventana vista de frente, con ancho, antepecho, alto y dintel (desde el piso terminado)."""
    w = ancho(ab)
    ap, arriba = alturas(ab)
    lado = 0.45
    W, H = (w + 2 * lado) * esc + 110, alto_muro * esc + 60
    X = lambda m: 40 + (m + lado) * esc
    Y = lambda h: 30 + (alto_muro - h) * esc
    # misma escala en todas las tarjetas (ancho en px fijo): se comparan a ojo
    p = [f'<svg viewBox="0 0 {W:.0f} {H:.0f}" width="{W:.0f}" height="{H:.0f}" class="frente" font-family="Helvetica, Arial, sans-serif">']
    p.append(f'<rect x="{X(-lado):.1f}" y="{Y(alto_muro):.1f}" width="{(w + 2 * lado) * esc:.1f}" height="{alto_muro * esc:.1f}" fill="#eee" stroke="#999"/>')
    for k in range(1, int(alto_muro / 0.25) + 1):        # hiladas de referencia (no a escala de ladrillo)
        y = Y(k * 0.25)
        p.append(f'<line x1="{X(-lado):.1f}" y1="{y:.1f}" x2="{X(w + lado):.1f}" y2="{y:.1f}" stroke="#ddd" stroke-width="0.6"/>')
    color = "#bfe3f5" if ab["tipo"] in ("ventana", "corrediza") else "#fff"
    p.append(f'<rect x="{X(0):.1f}" y="{Y(arriba):.1f}" width="{w * esc:.1f}" height="{(arriba - ap) * esc:.1f}" fill="{color}" stroke="#111" stroke-width="2.5"/>')
    p.append(f'<rect x="{X(-0.1):.1f}" y="{Y(arriba + 0.15):.1f}" width="{(w + 0.2) * esc:.1f}" height="{0.15 * esc:.1f}" fill="#9e9e9e" stroke="#555"/>')
    p.append(f'<line x1="{X(-lado) - 10:.1f}" y1="{Y(0):.1f}" x2="{X(w + lado) + 10:.1f}" y2="{Y(0):.1f}" stroke="#111" stroke-width="3"/>')
    p.append(f'<text x="{X(w + lado) + 8:.1f}" y="{Y(0) + 16:.1f}" font-size="12" text-anchor="end" fill="#444">piso terminado</text>')
    # ancho (arriba de la abertura)
    yc = Y(arriba) - 0.42 * esc
    p.append(f'<line x1="{X(0):.1f}" y1="{yc:.1f}" x2="{X(w):.1f}" y2="{yc:.1f}" stroke="{AZUL}" stroke-width="1.4"/>')
    for x in (X(0), X(w)):
        p.append(f'<line x1="{x:.1f}" y1="{yc - 6:.1f}" x2="{x:.1f}" y2="{yc + 6:.1f}" stroke="{AZUL}" stroke-width="1.4"/>')
    p.append(f'<text x="{(X(0) + X(w)) / 2:.1f}" y="{yc - 6:.1f}" font-size="19" font-weight="bold" text-anchor="middle" fill="{AZUL}">{w:.2f}</text>')
    # alturas: a la izquierda, antepecho; a la derecha, hasta arriba
    xl = X(-lado) + 16
    if ap > 0:
        p.append(f'<line x1="{xl:.1f}" y1="{Y(0):.1f}" x2="{xl:.1f}" y2="{Y(ap):.1f}" stroke="{ROJO}" stroke-width="1.4"/>')
        p.append(f'<text x="{xl + 6:.1f}" y="{(Y(0) + Y(ap)) / 2 + 6:.1f}" font-size="18" font-weight="bold" fill="{ROJO}">{ap:.2f}</text>')
        p.append(f'<line x1="{X(0):.1f}" y1="{Y(ap):.1f}" x2="{xl - 4:.1f}" y2="{Y(ap):.1f}" stroke="{ROJO}" stroke-width="0.8" stroke-dasharray="3 2"/>')
    xr = X(w) + 14
    p.append(f'<line x1="{xr:.1f}" y1="{Y(0):.1f}" x2="{xr:.1f}" y2="{Y(arriba):.1f}" stroke="#111" stroke-width="1.4"/>')
    p.append(f'<text x="{xr + 5:.1f}" y="{Y(arriba) + 18:.1f}" font-size="18" font-weight="bold" fill="#111">{arriba:.2f}</text>')
    if ab["tipo"] == "ventana" and w * esc > 75:
        p.append(f'<text x="{(X(0) + X(w)) / 2:.1f}" y="{(Y(ap) + Y(arriba)) / 2 + 6:.1f}" font-size="15" text-anchor="middle" fill="#333">alto {arriba - ap:.2f}</text>')
    p.append("</svg>")
    return "".join(p)


def frentes_html(casa, nid, donde):
    """Tarjetas: código, dónde está, y la abertura de frente. `donde(ab)` describe el lugar en palabras."""
    cod = codigos(casa, nid)
    tarjetas = []
    for ab in sorted(de_obra(casa, nid), key=lambda a: (cod[a["id"]][0], int(cod[a["id"]][1:]))):
        ap, arriba = alturas(ab)
        tipo = {"ventana": "Ventana", "puerta": "Puerta", "corrediza": "Corrediza"}.get(ab["tipo"], ab["tipo"])
        tarjetas.append(f'<div class="tarjeta"><div class="cod">{cod[ab["id"]]}</div><div class="que"><b>{tipo}</b> · '
                        f'{escape(donde(ab))}</div>{frente_svg(ab, cod[ab["id"]])}'
                        f'<div class="como">{escape(ab.get("obra", ""))}</div></div>')
    return '<div class="tarjetas">' + "".join(tarjetas) + "</div>"
