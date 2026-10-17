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


# ── lugares ocupados (en metros): para que los rótulos no se pisen con nada ─────────────────────────
ESC_M = 50.0        # px por metro (render_svg.ESC)


def caja_texto(x, y, txt, tam, vertical=False):
    """Caja (x0, y0, x1, y1) en m de un texto centrado en x con la base en y (o girado 90°, centrado en y)."""
    w = len(str(txt)) * tam * 0.56 / ESC_M + 0.04
    h = tam / ESC_M
    if vertical:
        return (x - h * 0.85, y - w / 2, x + h * 0.2, y + w / 2)
    return (x - w / 2, y - h * 0.82, x + w / 2, y + h * 0.22)


def solape(a, b):
    dx = min(a[2], b[2]) - max(a[0], b[0])
    dy = min(a[3], b[3]) - max(a[1], b[1])
    return dx * dy if dx > 0 and dy > 0 else 0.0


def _cruza_caja(p, q, c):
    """¿El segmento p→q pasa por dentro de la caja c? (Liang–Barsky)"""
    (x0, y0), (x1, y1) = p, q
    t0, t1 = 0.0, 1.0
    dx, dy = x1 - x0, y1 - y0
    for pp, qq in ((-dx, x0 - c[0]), (dx, c[2] - x0), (-dy, y0 - c[1]), (dy, c[3] - y0)):
        if abs(pp) < 1e-9:
            if qq < 0:
                return False
            continue
        r = qq / pp
        if pp < 0:
            t0 = max(t0, r)
        else:
            t1 = min(t1, r)
        if t0 > t1:
            return False
    return t1 - t0 > 0.02


def _cruzan(a, b, c, d):
    """¿Se cruzan los segmentos a→b y c→d?"""
    def o(p, q, r):
        return (q[0] - p[0]) * (r[1] - p[1]) - (q[1] - p[1]) * (r[0] - p[0])
    return (o(a, b, c) * o(a, b, d) < 0) and (o(c, d, a) * o(c, d, b) < 0)


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
        # afuera = sin ambiente o un ambiente exterior (no "fuera de la huella": el volado de la suite está fuera de ella)
        if amb is None or amb["tipo"] == "exterior":
            return s
        a = C.area(amb["poly"])
        if a > area:
            mejor, area = s, a
    return mejor


def dibujar_cadena(L, casa, nid, ln, occ=None):
    occ = occ if occ is not None else []
    pts, macizos = puntos_cadena(casa, nid, ln)
    if len(pts) < 2:
        return
    v, g = ln["vertical"], ln["grosor"]
    s = lado_libre(casa, nid, ln)
    d = ln["centro"] + s * (g / 2 + 0.42)        # línea de cota
    P = (lambda t, o: (o, t)) if v else (lambda t, o: (t, o))
    estilo = 'stroke="#333" stroke-width="1"'
    L.linea(*P(pts[0], d), *P(pts[-1], d), estilo)
    (ax, ay), (bx, by) = P(pts[0], d), P(pts[-1], d)
    occ.append((min(ax, bx) - 0.03, min(ay, by) - 0.03, max(ax, bx) + 0.03, max(ay, by) + 0.03, 3.0))
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
        occ.append(caja_texto(tx, ty, txt, TAM_COTA, v) + (8.0,))


def rotulo_texto(ab, codigo):
    """Las tres líneas del rótulo: código, medidas y antepecho (o alto)."""
    ap, arriba = alturas(ab)
    w = ancho(ab)
    if ab["tipo"] == "ventana":
        lineas = [f"{fmt(w)} × {fmt(arriba - ap)}", f"ant. {fmt(ap)}"]
    elif ab["tipo"] == "corrediza":
        lineas = [f"{fmt(w)} × {fmt(arriba)}", "desde el piso"]
    else:
        lineas = [f"hueco {fmt(w)}", f"alto {fmt(arriba)}"]
    return [codigo] + lineas


def info_vano(ab, codigo, donde=None):
    """Texto completo de una abertura (cuadrito al tocar el código en la página web)."""
    ap, arriba = alturas(ab)
    w = ancho(ab)
    nombre = {"ventana": "Ventana", "puerta": "Puerta", "corrediza": "Corrediza", "puerta_corrediza": "Puerta corrediza"}.get(ab["tipo"], "Abertura")
    partes = [f"{codigo} · {nombre}"]
    if ab["tipo"] == "ventana":
        partes.append(f"{fmt(w)} de ancho × {fmt(arriba - ap)} de alto; antepecho {fmt(ap)} (del piso a la parte de abajo); arriba a {fmt(arriba)}")
    elif ab["tipo"] == "corrediza":
        partes.append(f"{fmt(w)} de ancho × {fmt(arriba)} de alto, desde el piso")
    else:
        partes.append(f"hueco {fmt(w)} (lo que deja el albañil) × alto {fmt(arriba)}")
    if donde:
        partes.append(f"Entre: {donde}")
    if ab.get("obra"):
        partes.append(ab["obra"])
    return " — ".join(partes)


TAM_COD = TAM_ROTULO + 4
PASO = 0.33         # m entre líneas del rótulo


def dibujar_rotulos(L, casa, nid, occ=None, limites=None, donde=None):
    """Código + medidas de cada abertura, en GRANDE, en el primer lugar libre cerca de ella (del lado de su cadena, afuera
    de la casa si el muro da afuera). Si no entra al lado, se aleja con una rayita guía hasta la abertura. Fondo blanco.
    Se eligen todos juntos: primero cada uno en su mejor lugar, después varias vueltas en que cada rótulo se vuelve a
    acomodar viendo dónde quedaron los demás (que no se pisen ni se crucen las rayitas)."""
    occ = occ if occ is not None else []
    cod = codigos(casa, nid)
    lx0, lx1, ly0, ly1 = limites or (-1e9, 1e9, -1e9, 1e9)
    hx0, hy0, hx1, hy1 = C.huella_casa(casa)

    def adentro(ln):
        """Muro interior: hay ambientes (no exteriores) de los dos lados."""
        v, c, mid = ln["vertical"], ln["centro"], (ln["lo"] + ln["hi"]) / 2
        for d in (0.4, -0.4):
            x, y = (c + d, mid) if v else (mid, c + d)
            amb = C.ambiente_en(casa, nid, x, y)
            if amb is None or amb["tipo"] == "exterior":
                return False
        return True

    rot = []        # por abertura: datos y lista de lugares posibles [(costo fijo, cx, cy, caja, o, q, guia?)]
    for ln in lineas_de_muro(casa, nid):
        s = lado_libre(casa, nid, ln)
        v, g = ln["vertical"], ln["grosor"]
        for ab in ln["vanos"]:
            (x0, y0), (x1, y1) = ab["de"], ab["a"]
            t = ((y0 + y1) / 2) if v else ((x0 + x1) / 2)
            lineas = rotulo_texto(ab, cod[ab["id"]])
            tams = [TAM_COD] + [TAM_ROTULO] * (len(lineas) - 1)
            bw = max(len(l) * tm * 0.56 for l, tm in zip(lineas, tams)) / ESC_M + 0.16
            bh = PASO * (len(lineas) - 1) + TAM_COD / ESC_M + 0.12
            prof = bw if v else bh
            lugares = []
            for k_lado, lado in enumerate([s] if not adentro(ln) else [s, -s]):
                cara_l = ln["centro"] + lado * g / 2
                o_ = (cara_l, t) if v else (t, cara_l)
                for dist in (0.95, 1.25, 1.60, 2.0, 2.45, 2.95, 3.5):
                    for corr in (0, 0.45, -0.45, 0.9, -0.9, 1.35, -1.35, 1.8, -1.8, 2.3, -2.3, 2.8, -2.8, 3.3, -3.3):
                        cn = cara_l + lado * (dist if not v else dist + prof / 2 - 0.55)
                        cx, cy = (cn, t + corr) if v else (t + corr, cn)
                        caja = (cx - bw / 2, cy - bh / 2, cx + bw / 2, cy + bh / 2)
                        fuera = max(0, lx0 - caja[0]) + max(0, caja[2] - lx1) + max(0, ly0 - caja[1]) + max(0, caja[3] - ly1)
                        choque = sum(solape(caja, o[:4]) * o[4] for o in occ) + fuera * 50
                        # un rótulo de un muro interior no se va afuera de la casa (no se sabría de qué abertura es)
                        afuera = adentro(ln) and not (hx0 < cx < hx1 and hy0 < cy < hy1)
                        q_ = (min(max(o_[0], caja[0]), caja[2]), min(max(o_[1], caja[1]), caja[3]))
                        largo = ((q_[0] - o_[0]) ** 2 + (q_[1] - o_[1]) ** 2) ** 0.5
                        guia = largo > 0.6 or (abs(cx - o_[0]) > bw / 2 + 0.05 if not v else abs(cy - o_[1]) > bh / 2 + 0.05)
                        fijo = choque * 100 + dist * 0.6 + abs(corr) * 0.5 + k_lado * 1.5 + afuera * 15 + largo * 0.8
                        lugares.append((fijo, cx, cy, caja, o_, q_, guia))
            lugares.sort(key=lambda l: l[0])
            rot.append({"ab": ab, "lineas": lineas, "tams": tams, "bw": bw, "bh": bh, "lugares": lugares[:260],
                        "adentro": adentro(ln)})

    def costo(i, lug, elegidos):
        fijo, cx, cy, caja, o_, q_, guia = lug
        c = fijo
        for j, otro in elegidos.items():
            if j == i:
                continue
            c += solape(caja, otro[3]) * 20 * 100
            if guia and _cruza_caja(o_, q_, otro[3]):
                c += 25
            if otro[6] and _cruza_caja(otro[4], otro[5], caja):
                c += 25
            if guia and otro[6] and _cruzan(o_, q_, otro[4], otro[5]):
                c += 25
        return c

    elegidos = {}
    orden = sorted(range(len(rot)), key=lambda i: not rot[i]["adentro"])     # primero los de adentro (menos lugar)
    for i in orden:
        elegidos[i] = min(rot[i]["lugares"], key=lambda l: costo(i, l, elegidos))
    for _ in range(4):                                                       # vueltas de mejora
        cambio = False
        for i in orden:
            mejor = min(rot[i]["lugares"], key=lambda l: costo(i, l, elegidos))
            if mejor is not elegidos[i] and costo(i, mejor, elegidos) < costo(i, elegidos[i], elegidos) - 0.01:
                elegidos[i], cambio = mejor, True
        if not cambio:
            break
    # si dos rayitas se cruzan, se prueba intercambiar los lugares de esos dos rótulos
    def cerca(i, c):
        return min(rot[i]["lugares"], key=lambda l: (l[1] - c[0]) ** 2 + (l[2] - c[1]) ** 2)
    for i in orden:
        for j in orden:
            if i >= j:
                continue
            li, lj = elegidos[i], elegidos[j]
            if not (li[6] and lj[6] and _cruzan(li[4], li[5], lj[4], lj[5])):
                continue
            ni, nj = cerca(i, (lj[1], lj[2])), cerca(j, (li[1], li[2]))
            antes = costo(i, li, elegidos) + costo(j, lj, elegidos)
            prueba = dict(elegidos)
            prueba[i], prueba[j] = ni, nj
            if costo(i, ni, prueba) + costo(j, nj, prueba) < antes:
                elegidos[i], elegidos[j] = ni, nj

    for i, r in enumerate(rot):
        _, cx, cy, caja, (ox, oy), (px, py), guia = elegidos[i]
        occ.append(caja + (20.0,))
        if guia:
            L.linea(ox, oy, px, py, f'stroke="{ROJO}" stroke-width="1" stroke-dasharray="3 2"')
            a, b = L.p(ox, oy)
            L.add(f'<circle cx="{a:.1f}" cy="{b:.1f}" r="3" fill="{ROJO}"/>')
    for i, r in enumerate(rot):
        _, cx, cy, caja, *_ = elegidos[i]
        ab = r["ab"]
        info = info_vano(ab, cod[ab["id"]], (donde or {}).get(ab["id"]))
        a, b = L.p(caja[0], caja[1])
        L.add(f'<g class="rot" data-info="{escape(info, quote=True)}"><title>{escape(info)}</title>'
              f'<rect x="{a:.1f}" y="{b:.1f}" width="{r["bw"] * ESC_M:.1f}" height="{r["bh"] * ESC_M:.1f}" rx="5" '
              f'fill="#fff" fill-opacity="0.92" stroke="#d7d7d7" stroke-width="0.8"/>')
        yb = caja[1] + 0.06 + TAM_COD / ESC_M * 0.82
        for k, (txt, tm) in enumerate(zip(r["lineas"], r["tams"])):
            est = f'font-weight="bold" fill="{ROJO}"' if k == 0 else f'fill="{AZUL}"'
            L.texto(cx, yb + k * PASO, txt, tm, est)
        L.add("</g>")


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


def rotular_ambientes_simple(L, casa, nid, occ=None):
    """Nombre de cada ambiente; con `occ`, se corre un poco (dentro del ambiente) hasta un lugar libre."""
    for a in C.ambientes(casa, nid):
        if a["tipo"] == "exterior":
            continue
        cx, cy = a.get("etiqueta") or C.centroide(a["poly"])
        txt = a["nombre"].upper()
        if occ is not None:
            mejor = None
            for dy in (0, 0.3, -0.3, 0.6, -0.6, 0.9, -0.9):
                for dx in (0, 0.4, -0.4, 0.8, -0.8):
                    x, y = cx + dx, cy + dy
                    if C.ambiente_en(casa, nid, x, y - 0.1) is not a and (C.ambiente_en(casa, nid, x, y - 0.1) or {}).get("id") != a["id"]:
                        continue
                    caja = caja_texto(x, y, txt, 12)
                    costo = sum(solape(caja, o[:4]) * o[4] for o in occ) * 100 + abs(dx) + abs(dy)
                    if mejor is None or costo < mejor[0]:
                        mejor = (costo, x, y, caja)
            if mejor:
                _, cx, cy, caja = mejor
                occ.append(caja + (4.0,))
        L.texto(cx, cy, txt, 12, f'{HALO}font-weight="bold" fill="#9aa"')


def ocupacion_fija(casa, nid, y0, izq):
    """Muros, columnas, escalera, la fila de "entre ejes" y las burbujas de los ejes: [(x0, y0, x1, y1, peso)]."""
    occ = []
    for m in C.muros(casa, nid):
        if m["tipo"] == "ladrillo":
            occ.append(_rect_muro(m) + (6.0,))
    r = casa["estructura"]["seccion_columna"] / 2
    for col in C.columnas(casa):
        occ.append((col["x"] - r, col["y"] - r, col["x"] + r, col["y"] + r, 6.0))
    for e in C.escalera(casa):
        if e["desde"] == nid:
            for p in e["peldanos"] + [e["descanso"]]:
                occ.append((p["x0"], p["y0"], p["x1"], p["y1"], 1.0))
            pr = e["peldanos"][0]
            cx = (pr["x0"] + pr["x1"]) / 2
            occ.append((cx - 0.55, e["inicio_y"] + 0.05, cx + 0.55, e["inicio_y"] + 0.70, 8.0))   # "▲ SUBE" y su medida
    est = casa["estructura"]
    xs = sorted(est["ejes_x"].values())
    occ.append((xs[0], y0 - 2.75, xs[-1], y0 - 2.30, 10.0))           # fila "entre ejes"
    for x in xs:
        occ.append((x - 0.32, y0 - 3.37, x + 0.32, y0 - 2.73, 10.0))   # burbujas 1·2·3…
    for y in est["ejes_y"].values():
        occ.append((izq - 0.32, y - 0.32, izq + 0.32, y + 0.32, 10.0))  # burbujas A·B·C
    return occ


def planta_obra(casa, nivel, desde_x=None, hasta_x=None, desde_y=None, hasta_y=None, donde=None):
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
    izq = (desde_x if desde_x is not None else x0 - 3.0) + 0.45
    ejes_lejos(L, casa, x0, y0, x1, y1, izq)
    occ = ocupacion_fija(casa, nid, y0, izq)
    dibujar_muros(L, casa, nid)
    dibujar_aberturas(L, casa, nid, rotulos=False)
    dibujar_columnas(L, casa, nid)
    for ln in lineas_de_muro(casa, nid):
        dibujar_cadena(L, casa, nid, ln, occ)
    lim = (desde_x if desde_x is not None else x0 - 3.6, hasta_x if hasta_x is not None else x1 + 3.6,
           desde_y if desde_y is not None else y0 - 3.6, hasta_y if hasta_y is not None else y1 + 3.6)
    lim = (lim[0] + 0.9, lim[1] - 0.1, lim[2] + 0.1, lim[3] - 0.1)
    dibujar_rotulos(L, casa, nid, occ, lim, donde)
    rotular_ambientes_simple(L, casa, nid, occ)       # al final: buscan lugar entre lo que ya está
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


# ── techo del altillo (hojas del albañil) ───────────────────────────────────────

def _agua(casa, aid):
    return next(a for a in (casa.get("techos") or {}).get("aguas", []) if a["id"] == aid)


def planta_techo_obra(casa):
    """Planta del techo del altillo para la obra: caída, cotas de los bordes, antepechos, canaleta, gárgolas, bajantes,
    tanque y lo que atraviesa la calamina. Números grandes."""
    t = casa.get("techos") or {}
    nv = next(n for n in casa["niveles"] if n["id"] == "altillo")
    hx0, hy0, hx1, hy1 = C.huella_casa(casa)
    import render_svg
    margen, render_svg.MARGEN = render_svg.MARGEN, 3.6
    L = Lienzo(hx0, hy0, hx1, hy1)
    render_svg.MARGEN = margen
    L.poly([[hx0, hy0], [hx1, hy0], [hx1, hy1], [hx0, hy1]], 'fill="#f6f6f6" stroke="#bbb"')
    dep, ter = _agua(casa, "techo_depto"), _agua(casa, "techo_terraza")
    for ag, fill in ((dep, "#cfd8dc"), (ter, "#e0e4e6")):
        L.poly(ag["poly"], f'fill="{fill}" stroke="#455a64" stroke-width="1.5"')
    # ondas de la calamina (siguen la caída)
    x = 4.65
    while x < 16.8:
        L.linea(x, 0.10, x, 4.55, 'stroke="#90a4ae" stroke-width="0.6"')
        x += 0.30
    y = 0.25
    while y < 4.6:
        L.linea(-1.10, y, 4.30, y, 'stroke="#b0bec5" stroke-width="0.6"')
        y += 0.30
    sol = t.get("solar")
    if sol:
        sx0, sy0, sx1, sy1 = sol["rect"]
        L.poly([[sx0, sy0], [sx1, sy0], [sx1, sy1], [sx0, sy1]], 'fill="none" stroke="#f9a825" stroke-width="2" stroke-dasharray="8 4"')
        L.texto((sx0 + sx1) / 2 + 1.6, sy1 - 0.25, "lugar reservado: paneles / calentador solar", 12, f'{HALO}fill="#8d6e00"')
    for m in t.get("antepechos", []):
        if m["cota_tope"] > 10:
            L.linea(*m["de"], *m["a"], 'stroke="#424242" stroke-width="7"')
    # caída
    al_norte = dep["cae_hacia"] == "norte"
    _flecha_gruesa(L, (12.0, 3.3), (12.0, 1.0)) if al_norte else _flecha_gruesa(L, (12.0, 0.9), (12.0, 3.3))
    L.texto(13.9, 1.95, f"CAE {dep['pendiente'] * 100:.0f}% AL {dep['cae_hacia'].upper()}", 17, f'{HALO}font-weight="bold" fill="{ROJO}"')
    L.texto(13.9, 2.40, "(hacia el retiro norte)" if al_norte else "(hacia la franja)", 13, f'{HALO}fill="{ROJO}"')
    _flecha_gruesa(L, (2.6, 1.6), (0.6, 1.6))
    L.texto(1.6, 1.15, f"CAE {ter['pendiente'] * 100:.0f}% AL FRENTE", 15, f'{HALO}font-weight="bold" fill="{ROJO}"')
    L.texto(1.6, 3.2, "TECHO DE LA TERRAZA", 13, f'{HALO}font-weight="bold" fill="#333"')
    L.texto(1.6, 3.55, "calamina sobre fierro a la vista", 12, f'{HALO}fill="#333"')
    # cotas de los bordes
    y_norte, y_sur = (15.4, 1.30), (9.2, 4.28)
    alto_, bajo_ = (y_sur, y_norte) if al_norte else (y_norte, y_sur)
    L.texto(*alto_, f"borde alto ≈ +{dep['cota_alta']:.2f}", 14, f'{HALO}font-weight="bold" fill="#111"')
    L.texto(*bajo_, f"borde bajo ≈ +{dep['cota_baja']:.2f}", 14, f'{HALO}font-weight="bold" fill="#111"')
    _rotar(L, 4.05, 2.3, f"alto ≈ +{ter['cota_alta']:.2f}", 13, f'{HALO}font-weight="bold" fill="#111"', True)
    _rotar(L, -0.75, 2.3, f"bajo ≈ +{ter['cota_baja']:.2f}", 13, f'{HALO}font-weight="bold" fill="#111"', True)
    top = max(m["cota_tope"] for m in t.get("antepechos", []))
    L.texto(10.6, -1.55, f"ANTEPECHO todo alrededor del departamento hasta +{top:.2f} (tapa el techo)", 14,
            f'{HALO}font-weight="bold" fill="#424242"')
    # canaletas y gárgolas
    for cn in t.get("canaletas", []):
        L.linea(*cn["de"], *cn["a"], f'stroke="{AZUL}" stroke-width="5"')
    c0 = t["canaletas"][0]
    cy_ = c0["de"][1]
    L.texto(11.7, cy_ + (0.55 if cy_ < 2 else -0.30), f"canaleta por DENTRO del antepecho, {c0.get('pendiente', 0.005) * 100:.1f}% → bajante", 13,
            f'{HALO}fill="{AZUL}"')
    for gg in t.get("gargolas", []):
        gx, gy = gg["pos"]
        afuera = -0.45 if gy < 2 else 0.45
        L.linea(gx, cy_, gx, gy + afuera, f'stroke="{AZUL}" stroke-width="3"')
        L.add(f'<circle cx="{L.p(gx, gy + afuera)[0]:.1f}" cy="{L.p(gx, gy + afuera)[1]:.1f}" r="4" fill="{AZUL}"/>')
        L.texto(gx - 0.15, gy + (-0.42 if gy < 2 else 0.75), f"gárgola de rebalse (+{gg.get('cota', 9.2):.2f})", 12, f'{HALO}fill="{AZUL}" text-anchor="end"')
    for bp in t.get("bajantes", []):
        bx, by = bp["pos"]
        L.add(f'<circle cx="{L.p(bx, by)[0]:.1f}" cy="{L.p(bx, by)[1]:.1f}" r="8" fill="{AZUL}"/>')
        if bx > 17:
            L.texto(bx + 0.18, by + 0.10, f"{bp['id']} ↓", 13, f'{HALO}font-weight="bold" fill="{AZUL}" text-anchor="start"')
        else:
            L.texto(bx + 0.4, by + 0.55, f"{bp['id']} ↓", 13, f'{HALO}font-weight="bold" fill="{AZUL}"')
    for cx_ in t.get("conexiones", []):
        for a, b in zip(cx_, cx_[1:]):
            L.linea(*a, *b, f'stroke="{AZUL}" stroke-width="2" stroke-dasharray="5 3"')
    for po in t.get("postes", []):
        px, py = po["pos"]
        L.poly([[px - 0.09, py - 0.09], [px + 0.09, py - 0.09], [px + 0.09, py + 0.09], [px - 0.09, py + 0.09]], 'fill="#212121"')
    # tanque y lo que atraviesa la calamina
    tq = t.get("tanque")
    if tq:
        qx0, qy0, qx1, qy1 = tq["rect"]
        L.poly([[qx0, qy0], [qx1, qy0], [qx1, qy1], [qx0, qy1]], 'fill="#e6e1d8" stroke="#555" stroke-width="2"')
        L.texto((qx0 + qx1) / 2, (qy0 + qy1) / 2 - 0.05, "TANQUE", 13, 'font-weight="bold"')
        L.texto((qx0 + qx1) / 2, (qy0 + qy1) / 2 + 0.30, f"base +{tq['cota_base']:.2f}", 12, "")
    pases = [((7.20, 0.27), "caños del tanque (ducto A3)"), ((10.93, 0.27), "ventilación Ø110 sobre el techo (ducto A4)")]
    for (px, py), txt in pases:
        L.add(f'<circle cx="{L.p(px, py)[0]:.1f}" cy="{L.p(px, py)[1]:.1f}" r="7" fill="#fff" stroke="#6d4c41" stroke-width="2.5"/>')
    L.texto(8.4, -1.05, "○ pasan la calamina: caños del tanque (ducto A3) y ventilación Ø110 (ducto A4): con babeta y sombrerete", 12,
            f'{HALO}fill="#6d4c41"')
    L.texto(5.7, 5.95, "franja 2 m descubierta (losa)", 12, 'fill="#777" font-style="italic"')
    ejes_lejos(L, casa, hx0, hy0, hx1, hy1, -2.6)
    dibujar_columnas(L, casa, "altillo")
    return L.svg("Altillo — techo", desde_x=-3.2, hasta_x=19.0, desde_y=-3.6, hasta_y=7.4)


def _flecha_gruesa(L, a, b):
    import math
    (x0, y0), (x1, y1) = a, b
    L.linea(x0, y0, x1, y1, f'stroke="{ROJO}" stroke-width="5"')
    ang = math.atan2(y1 - y0, x1 - x0)
    pts = [(x1, y1), (x1 - 0.35 * math.cos(ang - 0.45), y1 - 0.35 * math.sin(ang - 0.45)),
           (x1 - 0.35 * math.cos(ang + 0.45), y1 - 0.35 * math.sin(ang + 0.45))]
    L.poly(pts, f'fill="{ROJO}"')


def corte_techo_svg(casa, x_corte=12.35):
    """Corte NORTE–SUR del departamento del altillo (por el estar): muros que suben hasta el antepecho, techo inclinado,
    canaleta y gárgola, ventanas del corte. Horizontal = y (norte a la izquierda), vertical = cota."""
    t = casa.get("techos") or {}
    dep = _agua(casa, "techo_depto")
    top = max(m["cota_tope"] for m in t.get("antepechos", []) if m["cota_tope"] > 10)
    ciego = next((m["cota_tope"] for m in t.get("antepechos", []) if m["cota_tope"] < 10), None)
    E = 95                                  # px por metro
    Y0, Y1, Z0, Z1 = -1.6, 8.8, 6.10, 10.85
    W, H = (Y1 - Y0) * E, (Z1 - Z0) * E
    X = lambda y: (y - Y0) * E
    Z = lambda z: (Z1 - z) * E
    g = 0.15
    p = [f'<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 {W:.0f} {H:.0f}" class="corte" font-family="Helvetica, Arial, sans-serif">',
         f'<rect width="{W:.0f}" height="{H:.0f}" fill="#fff"/>']

    def rect(y0, z0, y1, z1, fill, extra=""):
        p.append(f'<rect x="{X(y0):.1f}" y="{Z(z1):.1f}" width="{(y1 - y0) * E:.1f}" height="{(z1 - z0) * E:.1f}" fill="{fill}" {extra}/>')

    def txt(y, z, s, tam=16, est="", ancla="middle"):
        p.append(f'<text x="{X(y):.1f}" y="{Z(z):.1f}" font-size="{tam}" text-anchor="{ancla}" {HALO}{est}>{escape(s)}</text>')

    def cota_v(y, z0, z1, s, lado=1):
        p.append(f'<line x1="{X(y):.1f}" y1="{Z(z0):.1f}" x2="{X(y):.1f}" y2="{Z(z1):.1f}" stroke="#333" stroke-width="1.2"/>')
        for z in (z0, z1):
            p.append(f'<line x1="{X(y) - 7:.1f}" y1="{Z(z) + 7:.1f}" x2="{X(y) + 7:.1f}" y2="{Z(z) - 7:.1f}" stroke="#333" stroke-width="2"/>')
        a, b = X(y) + lado * 8, Z((z0 + z1) / 2)
        p.append(f'<text x="{a:.1f}" y="{b:.1f}" font-size="15" font-weight="bold" text-anchor="middle" transform="rotate(-90 {a:.1f} {b:.1f})" {HALO}>{escape(s)}</text>')

    # losa del altillo y franja
    rect(-1.0, 6.40, 6.795, 6.60, "#bdbdbd", 'stroke="#555"')
    txt(2.3, 6.25, "losa del altillo (ya hecha) — piso terminado +6.60", 14, 'fill="#444"')
    # muro norte (al ras exterior: y -0.125 a 0.025) y muro sur del departamento (eje y 4.67)
    yn0, yn1 = -0.125, 0.025
    ys0, ys1 = 4.67 - g / 2, 4.67 + g / 2
    for a, b in ((yn0, yn1), (ys0, ys1)):
        rect(a, 6.60, b, top, "#e0dcd5", 'stroke="#333" stroke-width="1.5"')
    # ventanas del corte: alta del estar (norte) y corrediza (sur)
    vn = next((ab for ab in C.aberturas(casa, "altillo") if ab["id"] == "ventana_estar_alt"), None)
    if vn:
        ap, al = alturas(vn)
        rect(yn0, 6.60 + ap, yn1, 6.60 + al, "#bfe3f5", 'stroke="#111" stroke-width="1.5"')
        txt(0.35, 6.60 + (ap + al) / 2, f"ventana alta: {ap:.2f} a {al:.2f} del piso", 13, 'fill="#0d47a1"', "start")
    cz = next((ab for ab in C.aberturas(casa, "altillo") if ab["tipo"] == "corrediza"), None)
    if cz:
        rect(ys0, 6.60, ys1, 6.60 + alturas(cz)[1], "#bfe3f5", 'stroke="#111" stroke-width="1.5"')
        txt(4.40, 7.70, f"corrediza (hasta {alturas(cz)[1]:.2f})", 13, 'fill="#0d47a1"', "end")
    # muro ciego al vecino
    if ciego:
        rect(6.67 - 0.075, 6.60, 6.67 + 0.075, ciego, "#e0dcd5", 'stroke="#333" stroke-width="1.5"')
        txt(6.67, ciego + 0.12, f"muro ciego al vecino +{ciego:.2f}", 13, "", "middle")
    # techo: calamina del borde alto al borde bajo, por dentro de los muros; canaleta y gárgola del lado bajo
    za, zb = dep["cota_alta"], dep["cota_baja"]
    al_norte = dep["cae_hacia"] == "norte"
    y_bajo, y_alto = (yn1 + 0.12, ys0 - 0.05) if al_norte else (ys0 - 0.12, yn1 + 0.05)
    zr = lambda y: zb + (za - zb) * (y - y_bajo) / (y_alto - y_bajo)
    p.append(f'<line x1="{X(y_alto):.1f}" y1="{Z(za):.1f}" x2="{X(y_bajo):.1f}" y2="{Z(zb):.1f}" stroke="#37474f" stroke-width="6"/>')
    for k in range(5):
        yy = y_bajo + (y_alto - y_bajo) * (k + 0.5) / 5
        rect(yy - 0.05, zr(yy) - 0.15, yy + 0.05, zr(yy) - 0.03, "#8d6e63", 'stroke="#4e342e"')
    txt(2.6, zr(2.6) + 0.22, "calamina + correas (las define el carpintero / ingeniero)", 14, 'fill="#37474f"')
    flecha = f"← cae {dep['pendiente'] * 100:.0f}% al norte" if al_norte else f"cae {dep['pendiente'] * 100:.0f}% al sur →"
    txt(2.6, zr(2.6) + 0.45, flecha, 15, f'font-weight="bold" fill="{ROJO}"')
    if al_norte:
        rect(yn1, zb - 0.16, y_bajo + 0.02, zb - 0.02, "#90caf9", f'stroke="{AZUL}" stroke-width="1.5"')
        p.append(f'<line x1="{X(yn1):.1f}" y1="{Z(zb - 0.12):.1f}" x2="{X(yn0 - 0.35):.1f}" y2="{Z(zb - 0.16):.1f}" stroke="{AZUL}" stroke-width="5"/>')
        txt(-0.10, 10.45, "canaleta por dentro del antepecho norte → bajante BP3 (esquina A5); 1 gárgola de rebalse al retiro", 13,
            f'fill="{AZUL}"', "start")
        p.append(f'<line x1="{X(0.0):.1f}" y1="{Z(10.40):.1f}" x2="{X(0.0):.1f}" y2="{Z(zb + 0.02):.1f}" stroke="{AZUL}" stroke-width="1" stroke-dasharray="3 3"/>')
    else:
        rect(y_bajo - 0.02, zb - 0.16, ys0, zb - 0.02, "#90caf9", f'stroke="{AZUL}" stroke-width="1.5"')
        p.append(f'<line x1="{X(ys0):.1f}" y1="{Z(zb - 0.12):.1f}" x2="{X(ys1 + 0.35):.1f}" y2="{Z(zb - 0.16):.1f}" stroke="{AZUL}" stroke-width="5"/>')
        txt(ys1 + 0.40, zb - 0.10, "gárgola de rebalse", 13, f'fill="{AZUL}"', "start")
        txt(ys1 + 0.40, zb - 0.38, "canaleta (por dentro) → bajante", 13, f'fill="{AZUL}"', "start")
    # cielo raso (a definir): debajo del borde bajo y de la canaleta
    zc = round(zb - 0.20, 2)
    p.append(f'<line x1="{X(yn1):.1f}" y1="{Z(zc):.1f}" x2="{X(ys0):.1f}" y2="{Z(zc):.1f}" stroke="#777" stroke-width="2" stroke-dasharray="10 6"/>')
    txt(2.6, zc - 0.25, f"cielo raso con aislación, ~+{zc:.2f} (≈{zc - 6.60:.2f} libres, debajo de la canaleta): a definir", 14, 'fill="#555"')
    # cotas
    cota_v(-0.55, 6.60, top, f"muro hasta +{top:.2f} ({top - 6.60:.2f} sobre el piso)", -1)
    z_n, z_s = (zb, za) if al_norte else (za, zb)
    cota_v(-1.15, 6.60, z_n, f"techo +{z_n:.2f}", -1)
    cota_v(7.80, 6.60, z_s, f"techo +{z_s:.2f}", 1)
    cota_v(8.35, 6.60, top, f"muro hasta +{top:.2f}", 1)
    for y, s in ((-0.05, "NORTE (retiro)"), (4.70, "SUR (franja)")):
        txt(y, Z1 - 0.18, s, 16, 'font-weight="bold"')
    txt(2.3, 7.30, "ESTAR", 18, 'font-weight="bold" fill="#9aa"')
    txt(5.7, 6.80, "FRANJA", 15, 'font-weight="bold" fill="#9aa"')
    p.append("</svg>")
    return "".join(p)


# ── bodega bajo la escalera de planta baja (2026-10-16: el maestro no entendía cómo era) ─────────────────────────

def _libre(casa, p, base):
    """Altura libre (desde el piso de PB) bajo un peldaño o el descanso."""
    ch = casa["estructura"]["escalera"]["contrahuella"]
    return p["z"] - (ch if "n" in p else 0) - C.GARGANTA - base


def bodega_planta_svg(casa):
    e = C.escalera(casa)[0]
    base = e["base"]
    E = 120
    X0, X1, Y0, Y1 = 3.75, 7.75, -1.05, 4.75
    W, H = (X1 - X0) * E, (Y1 - Y0) * E
    X = lambda x: (x - X0) * E
    Y = lambda y: (y - Y0) * E
    p = [f'<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 {W:.0f} {H:.0f}" class="bodega" font-family="Helvetica, Arial, sans-serif">',
         f'<rect width="{W:.0f}" height="{H:.0f}" fill="#fff"/>']

    def rect(x0, y0, x1, y1, est):
        p.append(f'<rect x="{X(x0):.1f}" y="{Y(y0):.1f}" width="{(x1 - x0) * E:.1f}" height="{(y1 - y0) * E:.1f}" {est}/>')

    def txt(x, y, s, tam=14, est="", ancla="middle"):
        p.append(f'<text x="{X(x):.1f}" y="{Y(y):.1f}" font-size="{tam}" text-anchor="{ancla}" {HALO}{est}>{escape(s)}</text>')

    # bodega: piso
    rect(4.525, 0.025, 6.925, 2.555, 'fill="#fff8e1" stroke="none"')
    # escalera: peldaños con la altura libre debajo
    for q in e["peldanos"] + [e["descanso"]]:
        lib = _libre(casa, q, base)
        fill = "#ffe0b2" if lib < 1.0 else "#fff3e0" if lib < 1.8 else "#e8f5e9"
        rect(q["x0"], q["y0"], q["x1"], q["y1"], f'fill="{fill}" fill-opacity="0.85" stroke="#8a6a45" stroke-width="1" stroke-dasharray="4 3"')
        if "n" in q:
            txt((q["x0"] + q["x1"]) / 2, (q["y0"] + q["y1"]) / 2 + 0.06,
                f"{q['n']} · {lib:.2f}" if lib > 0 else f"{q['n']} · macizo", 12, 'fill="#5d4037"')
        else:
            txt((q["x0"] + q["x1"]) / 2, (q["y0"] + q["y1"]) / 2 - 0.05, "DESCANSO encima", 13, 'font-weight="bold" fill="#5d4037"')
            txt((q["x0"] + q["x1"]) / 2, (q["y0"] + q["y1"]) / 2 + 0.22, f"debajo {lib:.2f} libres: se entra de pie", 13, 'fill="#2e7d32"')
    # muros reales
    for m in C.muros(casa, "pb"):
        if m["tipo"] != "ladrillo":
            continue
        x0, y0, x1, y1 = _rect_muro(m)
        if x1 < X0 or x0 > X1 or y1 < Y0 or y0 > Y1:
            continue
        rect(max(x0, X0), max(y0, Y0), min(x1, X1), min(y1, Y1), 'fill="#222"')
    for col in C.columnas(casa):
        if X0 < col["x"] < X1 and Y0 < col["y"] < Y1:
            rect(col["x"] - 0.125, col["y"] - 0.125, col["x"] + 0.125, col["y"] + 0.125, 'fill="#c62828" stroke="#600"')
    # puerta de la bodega (al retiro) y su giro
    ab = next(a for a in C.aberturas(casa, "pb") if a["id"] == "puerta_deposito")
    (hx, _), (ox, _) = ab["de"], ab["a"]
    rect(min(hx, ox), -0.125, max(hx, ox), 0.025, 'fill="#fff" stroke="none"')
    w = abs(hx - ox)
    p.append(f'<line x1="{X(hx):.1f}" y1="{Y(-0.125):.1f}" x2="{X(hx):.1f}" y2="{Y(-0.125 - w):.1f}" stroke="#222" stroke-width="2"/>')
    p.append(f'<path d="M {X(hx):.1f} {Y(-0.125 - w):.1f} A {w * E:.1f} {w * E:.1f} 0 0 0 {X(ox):.1f} {Y(-0.125):.1f}" fill="none" stroke="#777" stroke-dasharray="4 3"/>')
    txt((hx + ox) / 2, -0.55, f"PUERTA {w:.2f} × {ab.get('alto', 2.1):.2f}", 14, 'font-weight="bold" fill="#b71c1c"')
    txt((hx + ox) / 2, -0.33, "abre al retiro · escalón 0.15", 12, 'fill="#b71c1c"')
    # muebles de la bodega y la cajonera del hall
    for mb in casa["muebles"]["pb"]:
        if mb.get("nombre") in ("Herramientas", "Cajonera"):
            x0, y0, x1, y1 = mb["rect"]
            rect(x0, y0, x1, y1, 'fill="#d7ccc8" stroke="#5d4037" stroke-width="1.5"')
    txt(4.72, 1.45, "estante", 12, 'fill="#4e342e" transform="rotate(-90 {:.1f} {:.1f})"'.format(X(4.72), Y(1.45)))
    txt(5.09, 3.08, "cajones → hall", 12, 'font-weight="bold" fill="#4e342e"')
    # ducto de A2 (agua caliente)
    rect(4.525, 0.025, 4.675, 0.30, 'fill="#9e9e9e"')
    # rótulos de ambientes
    txt(6.30, 2.30, "BODEGA", 18, 'font-weight="bold" fill="#e65100"')
    txt(6.30, 2.50, "(solo desde el retiro)", 12, 'fill="#e65100"')
    txt(6.40, 3.60, "HALL", 16, 'font-weight="bold" fill="#999"')
    txt(4.05, 2.20, "LIVING", 14, 'font-weight="bold" fill="#999" transform="rotate(-90 {:.1f} {:.1f})"'.format(X(4.05), Y(2.20)))
    txt(7.40, 1.30, "BAÑO", 14, 'font-weight="bold" fill="#999" transform="rotate(-90 {:.1f} {:.1f})"'.format(X(7.40), Y(1.30)))
    txt(5.70, -0.85, "RETIRO NORTE", 14, 'font-weight="bold" fill="#999"')
    # líneas de corte
    for xc, k in ((5.125, 1), (6.325, 2)):
        p.append(f'<line x1="{X(xc):.1f}" y1="{Y(-0.95):.1f}" x2="{X(xc):.1f}" y2="{Y(4.65):.1f}" stroke="#1565c0" stroke-width="2" stroke-dasharray="10 5"/>')
        txt(xc, 4.70, f"CORTE {k}", 13, 'font-weight="bold" fill="#1565c0"')
    p.append("</svg>")
    return "".join(p)


def bodega_corte_svg(casa, xc, titulo):
    """Corte de norte (izquierda) a sur (derecha) por x = xc: escalera, altura libre debajo, muros y puerta."""
    e = C.escalera(casa)[0]
    base = e["base"]
    ch = casa["estructura"]["escalera"]["contrahuella"]
    G = C.GARGANTA
    E = 88
    Y0, Y1, Z0, Z1 = -0.95, 4.65, -0.55, 3.85
    W, H = (Y1 - Y0) * E, (Z1 - Z0) * E
    X = lambda y: (y - Y0) * E
    Z = lambda z: (Z1 - z) * E
    p = [f'<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 {W:.0f} {H:.0f}" class="bodega" font-family="Helvetica, Arial, sans-serif">',
         f'<rect width="{W:.0f}" height="{H:.0f}" fill="#fff"/>']

    def rect(y0, z0, y1, z1, est):
        p.append(f'<rect x="{X(y0):.1f}" y="{Z(z1):.1f}" width="{(y1 - y0) * E:.1f}" height="{(z1 - z0) * E:.1f}" {est}/>')

    def txt(y, z, s, tam=14, est="", ancla="middle"):
        p.append(f'<text x="{X(y):.1f}" y="{Z(z):.1f}" font-size="{tam}" text-anchor="{ancla}" {HALO}{est}>{escape(s)}</text>')

    def cota(y, z0, z1, s, col="#2e7d32"):
        p.append(f'<line x1="{X(y):.1f}" y1="{Z(z0):.1f}" x2="{X(y):.1f}" y2="{Z(z1):.1f}" stroke="{col}" stroke-width="2"/>')
        for z in (z0, z1):
            p.append(f'<line x1="{X(y) - 7:.1f}" y1="{Z(z):.1f}" x2="{X(y) + 7:.1f}" y2="{Z(z):.1f}" stroke="{col}" stroke-width="2"/>')
        a, b = X(y) - 6, Z((z0 + z1) / 2)
        p.append(f'<text x="{a:.1f}" y="{b:.1f}" font-size="15" font-weight="bold" text-anchor="middle" fill="{col}" '
                 f'transform="rotate(-90 {a:.1f} {b:.1f})" {HALO}>{escape(s)}</text>')

    # piso de PB y losa del primer piso (al sur del eje B)
    rect(Y0, -0.20, Y1, 0.0, 'fill="#bdbdbd"')
    rect(2.555, 3.00, Y1, 3.20, 'fill="#bdbdbd" stroke="#777"')
    txt(3.65, 3.30, "losa del primer piso", 12, 'fill="#555"')
    # bodega (relleno claro)
    rect(0.025, 0.0, 2.555, 1.95, 'fill="#fff8e1"')
    # escalera en este corte
    pel = [q for q in e["peldanos"] if q["x0"] - 0.01 <= xc <= q["x1"] + 0.01]
    d = e["descanso"]
    zr = lambda z: z - base
    rect(d["y0"], zr(d["z"]) - G, d["y1"], zr(d["z"]), 'fill="#d7ccc8" stroke="#5d4037" stroke-width="1.5"')
    # el tramo como UNA losa: escalones arriba y la cara de abajo recta (si toca el piso, macizo)
    if pel:
        sube_al_sur = pel[-1]["y0"] > pel[0]["y0"] and pel[-1]["z"] > pel[0]["z"]
        orden = sorted(pel, key=lambda q: q["z"])
        arriba, abajo = [], []
        for q in orden:
            z = zr(q["z"])
            y_ent, y_sal = (q["y0"], q["y1"]) if sube_al_sur else (q["y1"], q["y0"])
            arriba += [(y_ent, z - ch), (y_ent, z), (y_sal, z)]
            abajo.append((y_ent, max(z - ch - G, 0.0)))
        abajo.append((arriba[-1][0], max(zr(orden[-1]["z"]) - ch - G, 0.0)))
        if orden[0]["z"] - base - ch - G < 0.01:         # el primer peldaño apoya en el piso
            abajo[0] = (arriba[0][0], 0.0)
        poly = arriba + list(reversed(abajo))
        p.append('<polygon points="' + " ".join(f"{X(y):.1f},{Z(z):.1f}" for y, z in poly) +
                 '" fill="#d7ccc8" stroke="#5d4037" stroke-width="1.5"/>')
    # muros cortados: norte (eje A) y eje B, hasta tocar la escalera
    lib_desc = zr(d["z"]) - G
    rect(-0.125, 0.0, 0.025, 3.0, 'fill="#222"')
    puerta = next(a for a in C.aberturas(casa, "pb") if a["id"] == "puerta_deposito")
    xs = sorted([puerta["de"][0], puerta["a"][0]])
    if xs[0] <= xc <= xs[1]:
        al = puerta.get("alto", 2.1)
        rect(-0.125, 0.0, 0.025, al, 'fill="#fff" stroke="#b71c1c" stroke-width="2"')
        txt(-0.10, al + 0.12, f"puerta ↑ {al:.2f}", 13, 'font-weight="bold" fill="#b71c1c"', "start")
        rect(-0.60, -0.15, -0.125, 0.0, 'fill="#9e9e9e"')
        txt(-0.55, -0.05, "retiro −0.15", 11, 'fill="#333"', "start")
    bajo_b = next((zr(q["z"]) - ch - G for q in pel if q["y0"] - 0.01 <= 2.63 <= q["y1"] + 0.01), 3.0)
    rect(2.555, 0.0, 2.705, min(bajo_b, 3.0), 'fill="#222"')
    # cotas de altura libre
    cota(0.55, 0.0, lib_desc, f"{lib_desc:.2f} libres")
    q_b = next((q for q in pel if q["y0"] - 0.01 <= 2.40 <= q["y1"] + 0.01), None)
    if q_b:
        lb = zr(q_b["z"]) - ch - G
        cota(2.40, 0.0, lb, f"{lb:.2f}")
    # cajonera (solo en el corte del lado del living)
    caj = next((m for m in casa["muebles"]["pb"] if m.get("nombre") == "Cajonera"), None)
    if caj and caj["rect"][0] <= xc <= caj["rect"][2]:
        _, y0, _, y1 = caj["rect"]
        rect(y0, 0.0, y1, caj.get("alto", 0.4), 'fill="#bcaaa4" stroke="#4e342e" stroke-width="1.5"')
        txt((y0 + y1) / 2, caj.get("alto", 0.4) + 0.62, "cajones", 12, 'font-weight="bold" fill="#4e342e"')
        txt((y0 + y1) / 2, caj.get("alto", 0.4) + 0.42, "(abren al hall)", 11, 'fill="#4e342e"')
    txt(1.25, 1.10, "BODEGA", 18, 'font-weight="bold" fill="#e65100"')
    txt(3.65, 1.60, "HALL", 16, 'font-weight="bold" fill="#999"')
    txt(-0.50, -0.45, "← NORTE (retiro)", 13, 'font-weight="bold"', "start")
    txt(4.55, -0.45, "SUR (hall) →", 13, 'font-weight="bold"', "end")
    txt((Y0 + Y1) / 2, Z1 - 0.20, titulo, 15, 'font-weight="bold" fill="#1565c0"')
    p.append("</svg>")
    return "".join(p)
