"""Planos de instalaciones (ESQUEMA PRELIMINAR) generados desde el modelo.

Uso: python tools/instalaciones.py

- Eléctrico: luces, interruptores, tomacorrientes y tomas especiales salen de los ambientes, sus
  puertas y sus muebles; se agrupan en circuitos y se arma un cuadro de cargas.
- Sanitario + gas: los puntos de agua y desagüe salen de los artefactos (muebles de tipo inodoro,
  lavamanos, ducha, lavaplatos, lavadora, lavadero). Cada punto se une con una rama recta a la
  troncal más cercana definida en `instalaciones` del modelo.

No reemplaza el proyecto de un ingeniero (eléctrico: NB 777; sanitario y gas: normas de la
empresa de agua y de YPFB). Sirve para ubicar y conversar.
"""
import math

from casa import SALIDA, _intervalo, aberturas, ambientes, area, caja, cargar, centroide, dentro, muebles
from render_svg import ESC, Lienzo, dibujar_aberturas, dibujar_columnas, dibujar_escalera, dibujar_muros, flecha_norte, leyenda

TENSION = 220  # V

# Circuitos: (id, nombre, tipo)
CIRCUITOS = [
    ("C1", "Iluminación zona social", "luz"),
    ("C2", "Iluminación zona de servicio y estudio", "luz"),
    ("C3", "Tomas living, hall, ingreso y estudio", "toma"),
    ("C4", "Tomas comedor y cocina (generales)", "toma"),
    ("C5", "Cocina: refrigerador, horno, campana", "especial"),
    ("C6", "Lavado: lavadora y secadora", "especial"),
    ("C7", "Tomas baño, depósito, almacén (con diferencial)", "toma"),
]
SOCIALES = {"living", "ingreso", "hall", "pasillo_pb", "comedor", "terraza", "acceso"}
VA_LUZ, VA_TOMA = 100, 200

# Muebles que piden una toma especial: tipo/nombre -> (letra, VA, circuito, descripción)
ESPECIALES = {
    "refrigerador": ("R", 300, "C5", "refrigerador"),
    "Torre horno": ("H", 2000, "C5", "horno / microondas"),
    "cocina": ("C", 150, "C5", "campana + encendido"),
    "L": ("L", 800, "C6", "lavadora"),
    "S": ("S", 2500, "C6", "secadora"),
}
# Muebles que piden una toma común extra junto a ellos
TOMA_JUNTO = {"escritorio": "C3", "TV": "C3", "Isla": "C4", "lavamanos": "C7"}


def _borde_de(amb, ab):
    """¿La abertura está sobre un borde del ambiente?"""
    pts = amb["poly"]
    for a, b in zip(pts, pts[1:] + pts[:1]):
        iv = _intervalo(a, b, ab["de"], ab["a"])
        if iv and iv[0] >= -0.01 and iv[1] <= 1.01:
            return a, b
    return None


def _del_otro_lado(casa, nivel_id, amb, ab):
    """Ambiente al otro lado de la abertura (o None si da al exterior)."""
    (ax, ay), (bx, by) = ab["de"], ab["a"]
    mx, my = (ax + bx) / 2, (ay + by) / 2
    cx, cy = centroide(amb["poly"])
    nx, ny = -(by - ay), bx - ax
    L = math.hypot(nx, ny)
    nx, ny = nx / L * 0.3, ny / L * 0.3
    if (cx - mx) * nx + (cy - my) * ny > 0:
        nx, ny = -nx, -ny
    for otro in ambientes(casa, nivel_id):
        if otro is not amb and dentro(otro["poly"], mx + nx, my + ny):
            return otro
    return None


def _prioridad_entrada(casa, nivel_id, amb, ab):
    """Orden para elegir dónde va el interruptor: se entra desde la circulación."""
    otro = _del_otro_lado(casa, nivel_id, amb, ab)
    desde_circulacion = otro is not None and otro["tipo"] == "circulacion"
    if amb["tipo"] == "circulacion":
        return (0 if ab["tipo"] == "vano" else 1, 0)
    return (0 if desde_circulacion else 1, 0 if ab["tipo"].startswith("puerta") else 1)


def _hacia_adentro(amb, x, y, d):
    cx, cy = centroide(amb["poly"])
    L = math.hypot(cx - x, cy - y) or 1
    return x + (cx - x) / L * d, y + (cy - y) / L * d


def electrico(casa, nivel_id):
    """Devuelve (puntos, cables). puntos: dict(tipo, pos, circuito, etiqueta, va)."""
    puntos, cables = [], []
    abs_ = aberturas(casa, nivel_id)
    mbs = muebles(casa, nivel_id)
    for amb in ambientes(casa, nivel_id):
        social = amb["id"] in SOCIALES
        circ_luz = "C1" if social else "C2"
        x0, y0, x1, y1 = caja(amb["poly"])
        # luces
        if amb["tipo"] == "exterior":
            luces = [centroide(amb["poly"])]
        elif area(amb["poly"]) < 12 or amb["tipo"] == "circulacion":
            luces = [amb.get("etiqueta") and centroide(amb["poly"]) or centroide(amb["poly"])]
        else:
            if x1 - x0 >= y1 - y0:
                luces = [(x0 + (x1 - x0) * f, (y0 + y1) / 2) for f in (0.3, 0.7)]
            else:
                luces = [((x0 + x1) / 2, y0 + (y1 - y0) * f) for f in (0.3, 0.7)]
            luces = [l if dentro(amb["poly"], *l) else centroide(amb["poly"]) for l in luces]
        mesa = [m for m in mbs if m["tipo"] == "mesa" and dentro(amb["poly"], (m["rect"][0] + m["rect"][2]) / 2,
                                                              (m["rect"][1] + m["rect"][3]) / 2) and m.get("alto", 0.75) >= 0.7]
        if mesa and amb["tipo"] != "exterior":
            r = mesa[0]["rect"]
            luces = [((r[0] + r[2]) / 2, (r[1] + r[3]) / 2)]
        ids_luz = []
        for l in luces:
            puntos.append({"tipo": "luz", "pos": l, "circuito": circ_luz, "va": VA_LUZ, "amb": amb["id"]})
            ids_luz.append(len(puntos) - 1)
        # interruptor junto a la primera puerta (o paso) del ambiente
        if amb["tipo"] != "exterior" or amb["id"] == "terraza":
            propias = [ab for ab in abs_ if _borde_de(amb, ab)]
            propias.sort(key=lambda ab: _prioridad_entrada(casa, nivel_id, amb, ab))
            if propias:
                ab = propias[0]
                (ax, ay), (bx, by) = ab["de"], ab["a"]
                L = math.hypot(bx - ax, by - ay)
                ux, uy = (bx - ax) / L, (by - ay) / L
                sx, sy = bx + ux * 0.15, by + uy * 0.15
                if not dentro(amb["poly"], *_hacia_adentro(amb, sx, sy, 0.12)):
                    sx, sy = ax - ux * 0.15, ay - uy * 0.15
                sx, sy = _hacia_adentro(amb, sx, sy, 0.12)
                puntos.append({"tipo": "interruptor", "pos": (sx, sy), "circuito": circ_luz, "va": 0, "amb": amb["id"]})
                for i in ids_luz:
                    cables.append(((sx, sy), puntos[i]["pos"]))
        # tomas generales repartidas por el perímetro (no en exteriores ni en la cocina: van por mesón)
        if amb["tipo"] in ("social", "dormitorio") or amb["id"] in ("hall", "deposito_patio", "almacen", "lavado"):
            per = sum(math.dist(a, b) for a, b in zip(amb["poly"], amb["poly"][1:] + amb["poly"][:1]))
            n = {"social": max(2, math.ceil(per / 4)), "dormitorio": max(3, math.ceil(per / 4))}.get(amb["tipo"], 1)
            circ = "C4" if amb["id"] == "comedor" else ("C7" if amb["id"] in ("deposito_patio", "almacen", "lavado") else "C3")
            for pt in _repartir(amb, abs_, n):
                puntos.append({"tipo": "toma", "pos": pt, "circuito": circ, "va": VA_TOMA, "amb": amb["id"]})
    # muebles: tomas especiales y tomas junto a muebles
    for m in mbs:
        x0, y0, x1, y1 = m["rect"]
        c = ((x0 + x1) / 2, (y0 + y1) / 2)
        clave = m.get("nombre") if m.get("nombre") in ESPECIALES else m["tipo"]
        if clave in ESPECIALES:
            letra, va, circ, desc = ESPECIALES[clave]
            puntos.append({"tipo": "especial", "pos": c, "circuito": circ, "va": va, "etiqueta": letra, "desc": desc})
        clave = m.get("nombre") if m.get("nombre") in TOMA_JUNTO else m["tipo"]
        if clave in TOMA_JUNTO:
            puntos.append({"tipo": "toma", "pos": (x1 + 0.12, c[1]) if clave != "TV" else (c[0], y1 + 0.10),
                           "circuito": TOMA_JUNTO[clave], "va": VA_TOMA})
            if clave in ("escritorio", "TV"):
                puntos.append({"tipo": "datos", "pos": (x1 + 0.12, c[1] + 0.25) if clave != "TV" else (c[0] + 0.3, y1 + 0.10),
                               "circuito": "-", "va": 0})
        if m["tipo"] == "meson" and not m.get("nombre"):
            # tomas sobre el mesón cada ~1.2 m
            largo = max(x1 - x0, y1 - y0)
            for k in range(max(1, int(largo / 1.2))):
                f = (k + 0.5) / max(1, int(largo / 1.2))
                pos = (x0 + (x1 - x0) * f, c[1]) if x1 - x0 >= y1 - y0 else (c[0], y0 + (y1 - y0) * f)
                if not any(math.dist(pos, q["pos"]) < 0.5 for q in puntos if q["tipo"] == "especial"):
                    puntos.append({"tipo": "toma", "pos": pos, "circuito": "C4", "va": VA_TOMA})
    # extractores: al inicio de los ductos de ventilación que lo piden
    vent = casa.get("instalaciones", {}).get(nivel_id, {}).get("ventilacion", {})
    for d in vent.get("ductos") or []:
        if d.get("extractor"):
            puntos.append({"tipo": "extractor", "pos": tuple(d["linea"][0]), "circuito": "C2", "va": 50})
    for l in (casa.get("instalaciones", {}).get(nivel_id, {}).get("electrico", {}).get("luces_extra") or []):
        puntos.append({"tipo": "luz", "pos": tuple(l["pos"]), "circuito": "C2", "va": VA_LUZ})
    return puntos, cables


def _repartir(amb, abs_, n):
    """n puntos sobre el perímetro del ambiente, lejos de puertas y ventanas, 0.12 m hacia adentro."""
    pts = amb["poly"]
    bordes = list(zip(pts, pts[1:] + pts[:1]))
    per = sum(math.dist(a, b) for a, b in bordes)
    out = []
    for k in range(n):
        objetivo = per * (k + 0.5) / n
        for intento in range(40):
            t = (objetivo + intento * 0.25) % per
            acc = 0
            for a, b in bordes:
                L = math.dist(a, b)
                if acc + L >= t:
                    f = (t - acc) / L
                    x, y = a[0] + (b[0] - a[0]) * f, a[1] + (b[1] - a[1]) * f
                    break
                acc += L
            libre = True
            for ab in abs_:
                iv = _intervalo(a, b, ab["de"], ab["a"])
                if iv and iv[0] - 0.4 / L <= f <= iv[1] + 0.4 / L:
                    libre = False
            if libre:
                out.append(_hacia_adentro(amb, x, y, 0.12))
                break
    return out


def cuadro_cargas(puntos):
    filas = []
    for cid, nombre, tipo in CIRCUITOS:
        ps = [p for p in puntos if p["circuito"] == cid]
        va = sum(p["va"] for p in ps)
        amp = va / TENSION
        if tipo == "luz":
            prot, cable = "10 A", "1.5 mm²"
        elif va > 2600:
            prot, cable = "25 A", "4 mm²"
        else:
            prot, cable = "16 A", "2.5 mm²"
        filas.append({"id": cid, "nombre": nombre, "puntos": len(ps), "va": va, "a": amp, "prot": prot, "cable": cable})
    return filas


# ── sanitario ────────────────────────────────────────────────────────────────

ARTEFACTOS = {  # tipo/nombre de mueble -> (agua fría, agua caliente, desagüe Ø)
    "inodoro": (True, False, "110"), "lavamanos": (True, True, "50"), "ducha": (True, True, "50"),
    "lavaplatos": (True, True, "50"), "L": (True, False, "50"), "lavadero": (True, True, "50"),
}


def _lineas(cfg_linea):
    """Acepta una polilínea o una lista de polilíneas."""
    if not cfg_linea:
        return []
    return cfg_linea if isinstance(cfg_linea[0][0], (list, tuple)) else [cfg_linea]


def _proyectar(p, linea):
    """Punto más cercano a p sobre una polilínea o lista de polilíneas."""
    mejor, dmin = None, 1e9
    segs = [(a, b) for l in _lineas(linea) for a, b in zip(l, l[1:])]
    for a, b in segs:
        dx, dy = b[0] - a[0], b[1] - a[1]
        L2 = dx * dx + dy * dy
        t = max(0, min(1, ((p[0] - a[0]) * dx + (p[1] - a[1]) * dy) / L2))
        q = (a[0] + t * dx, a[1] + t * dy)
        d = math.dist(p, q)
        if d < dmin:
            mejor, dmin = q, d
    return mejor


def _escuadra(p, q):
    """Recorrido en L de p a q (primero en la dirección más larga)."""
    if abs(p[0] - q[0]) < 0.01 or abs(p[1] - q[1]) < 0.01:
        return [p, q]
    return [p, (q[0], p[1]), q] if abs(p[0] - q[0]) <= abs(p[1] - q[1]) else [p, (p[0], q[1]), q]


def sanitario(casa, nivel_id):
    cfg = casa.get("instalaciones", {}).get(nivel_id, {}).get("sanitario", {})
    puntos = []
    for m in muebles(casa, nivel_id):
        clave = m.get("nombre") if m.get("nombre") in ARTEFACTOS else m["tipo"]
        if clave not in ARTEFACTOS:
            continue
        af, ac, ds = ARTEFACTOS[clave]
        x0, y0, x1, y1 = m["rect"]
        c = ((x0 + x1) / 2, (y0 + y1) / 2)
        puntos.append({"pos": c, "af": af, "ac": ac, "desague": ds, "nombre": m.get("nombre") or m["tipo"]})
    ramas = {"agua_fria": [], "agua_caliente": [], "desague": []}
    for p in puntos:
        if p["af"] and cfg.get("agua_fria"):
            ramas["agua_fria"].append(_escuadra(p["pos"], _proyectar(p["pos"], cfg["agua_fria"])))
        if p["ac"] and cfg.get("agua_caliente"):
            ramas["agua_caliente"].append(_escuadra(p["pos"], _proyectar(p["pos"], cfg["agua_caliente"])))
        if cfg.get("colector"):
            ramas["desague"].append((_escuadra(p["pos"], _proyectar(p["pos"], cfg["colector"])), p["desague"]))
    return cfg, puntos, ramas


# ── dibujo ───────────────────────────────────────────────────────────────────

def _base(casa, nivel, titulo, subt, extra=()):
    ambs = ambientes(casa, nivel["id"])
    pts = [p for a in ambs for p in a["poly"]] + [list(e) for e in extra]
    x0, y0 = min(p[0] for p in pts), min(p[1] for p in pts) - 1.0
    x1, y1 = max(p[0] for p in pts) + 1.0, max(p[1] for p in pts)
    L = Lienzo(x0 - 1.0, y0, x1, y1)
    for a in ambs:
        estilo = 'fill="#fafafa" stroke="#bbb" stroke-width="0.8"' + (' stroke-dasharray="5 3"' if a["tipo"] == "exterior" else "")
        L.poly(a["poly"], estilo)
    dibujar_escalera(L, casa, nivel["id"])
    dibujar_muros(L, casa, nivel["id"])
    dibujar_aberturas(L, casa, nivel["id"])
    dibujar_columnas(L, casa)
    for a in ambs:
        cx, cy = a.get("etiqueta") or centroide(a["poly"])
        L.texto(cx, cy + 0.35, a["nombre"].upper(), 8, 'fill="#999" font-weight="bold"')
    flecha_norte(L, casa, x1 + 0.2, y1 + 1.4)
    leyenda(L, x0 - 0.5, y1 + 1.6, titulo, subt)
    return L, (x0, y0, x1, y1)


def _circulo(L, x, y, r, estilo):
    a, b = L.p(x, y)
    L.add(f'<circle cx="{a:.1f}" cy="{b:.1f}" r="{r * ESC:.1f}" {estilo}/>')


def plano_electrico(casa, nivel):
    puntos, cables = electrico(casa, nivel["id"])
    cfg = casa.get("instalaciones", {}).get(nivel["id"], {}).get("electrico", {})
    L, (x0, y0, x1, y1) = _base(casa, nivel, f"{nivel['nombre'].upper()} — ELÉCTRICO (esquema)",
                                "Preliminar, para conversar con el electricista. Diseño definitivo según NB 777.")
    naranja = "#e65100"
    for a, b in cables:
        L.linea(a[0], a[1], b[0], b[1], f'stroke="{naranja}" stroke-width="0.8" stroke-dasharray="4 3"')
    for p in puntos:
        x, y = p["pos"]
        t = p["tipo"]
        if t == "luz":
            _circulo(L, x, y, 0.16, f'fill="#fff3e0" stroke="{naranja}" stroke-width="1.2"')
            L.linea(x - 0.11, y - 0.11, x + 0.11, y + 0.11, f'stroke="{naranja}" stroke-width="1"')
            L.linea(x - 0.11, y + 0.11, x + 0.11, y - 0.11, f'stroke="{naranja}" stroke-width="1"')
        elif t == "interruptor":
            _circulo(L, x, y, 0.07, f'fill="{naranja}"')
            L.texto(x + 0.18, y + 0.05, "S", 7, f'fill="{naranja}" font-weight="bold"')
        elif t == "toma":
            _circulo(L, x, y, 0.09, 'fill="#fff" stroke="#1565c0" stroke-width="1.2"')
            L.linea(x - 0.04, y - 0.05, x - 0.04, y + 0.05, 'stroke="#1565c0" stroke-width="1"')
            L.linea(x + 0.04, y - 0.05, x + 0.04, y + 0.05, 'stroke="#1565c0" stroke-width="1"')
            L.texto(x, y - 0.14, p["circuito"], 6, 'fill="#1565c0"')
        elif t == "especial":
            L.poly([[x - 0.13, y - 0.13], [x + 0.13, y - 0.13], [x + 0.13, y + 0.13], [x - 0.13, y + 0.13]], 'fill="#1565c0"')
            L.texto(x, y + 0.05, p["etiqueta"], 8, 'fill="#fff" font-weight="bold"')
            L.texto(x, y - 0.20, p["circuito"], 6, 'fill="#1565c0"')
        elif t == "datos":
            L.poly([[x, y - 0.11], [x + 0.11, y + 0.09], [x - 0.11, y + 0.09]], 'fill="#6a1b9a"')
        elif t == "extractor":
            _circulo(L, x, y, 0.16, 'fill="#e8f5e9" stroke="#2e7d32" stroke-width="1.2"')
            L.texto(x, y + 0.05, "E", 8, 'fill="#2e7d32" font-weight="bold"')
    if cfg.get("tablero"):
        x, y = cfg["tablero"]["pos"]
        L.poly([[x - 0.30, y - 0.10], [x + 0.30, y - 0.10], [x + 0.30, y + 0.08], [x - 0.30, y + 0.08]], 'fill="#212121"')
        L.texto(x, y + 0.03, "TD", 7, 'fill="#fff" font-weight="bold"')
        L.texto(x, y - 0.18, "tablero", 7, 'fill="#212121"')
    if cfg.get("acometida"):
        x, y = cfg["acometida"]["pos"]
        tx, ty = cfg["tablero"]["pos"]
        L.linea(x - 1.4, y, x, y, 'stroke="#212121" stroke-width="2"')
        L.linea(x, y, tx, ty, 'stroke="#212121" stroke-width="1.2" stroke-dasharray="6 3"')
        L.texto(x - 1.0, y - 0.15, "← medidor (calle)", 7, 'fill="#212121"')
    if cfg.get("timbre"):
        x, y = cfg["timbre"]
        _circulo(L, x, y, 0.08, 'fill="#fff" stroke="#212121"')
        L.texto(x - 0.3, y + 0.05, "timbre", 6, 'fill="#212121"')
    # leyenda de símbolos
    lx, ly = x0 + 6, y1 + 1.15
    items = [("luz", "luz de techo"), ("interruptor", "interruptor"), ("toma", "tomacorriente (circuito)"),
             ("especial", "toma especial"), ("datos", "datos / TV"), ("extractor", "extractor")]
    for k, (t, txt) in enumerate(items):
        cx = lx + k * 2.2
        fake = {"tipo": t, "pos": (cx, ly), "circuito": "", "etiqueta": "X"}
        _dibujar_simbolo(L, fake, naranja)
        L.texto(cx + 0.25, ly + 0.05, txt, 7, 'fill="#444" text-anchor="start"')
    return L.svg(f"{nivel['nombre']} — eléctrico"), puntos


def _dibujar_simbolo(L, p, naranja):
    x, y = p["pos"]
    t = p["tipo"]
    if t == "luz":
        _circulo(L, x, y, 0.13, f'fill="#fff3e0" stroke="{naranja}" stroke-width="1.2"')
    elif t == "interruptor":
        _circulo(L, x, y, 0.07, f'fill="{naranja}"')
    elif t == "toma":
        _circulo(L, x, y, 0.09, 'fill="#fff" stroke="#1565c0" stroke-width="1.2"')
    elif t == "especial":
        L.poly([[x - 0.11, y - 0.11], [x + 0.11, y - 0.11], [x + 0.11, y + 0.11], [x - 0.11, y + 0.11]], 'fill="#1565c0"')
    elif t == "datos":
        L.poly([[x, y - 0.11], [x + 0.11, y + 0.09], [x - 0.11, y + 0.09]], 'fill="#6a1b9a"')
    elif t == "extractor":
        _circulo(L, x, y, 0.13, 'fill="#e8f5e9" stroke="#2e7d32" stroke-width="1.2"')


def plano_sanitario(casa, nivel):
    cfg, puntos, ramas = sanitario(casa, nivel["id"])
    extra = [cfg["pozo"]["pos"]] if cfg.get("pozo") else []
    L, (x0, y0, x1, y1) = _base(casa, nivel, f"{nivel['nombre'].upper()} — AGUA, DESAGÜE, GAS Y VENTILACIÓN (esquema)",
                                "Preliminar: recorridos y diámetros a confirmar con el instalador (agua/desagüe) y con YPFB (gas natural).",
                                extra)
    AZUL, ROJO, CAFE, GAS = "#1565c0", "#c62828", "#6d4c41", "#f9a825"

    def poli(linea, estilo):
        L.add('<polyline points="%s" fill="none" %s/>' % (" ".join("%.1f,%.1f" % L.p(*q) for q in linea), estilo))

    # desagüe
    if cfg.get("colector"):
        poli(cfg["colector"], f'stroke="{CAFE}" stroke-width="4"')
        a, b = cfg["colector"][-2], cfg["colector"][-1]
        L.texto(b[0] + 0.1, b[1] - 0.2, "← a la red pública (calle)  Ø110, pend. ≥2%", 8, f'fill="{CAFE}" text-anchor="start"')
        for c in cfg.get("camaras", []):
            L.poly([[c[0] - 0.30, c[1] - 0.30], [c[0] + 0.30, c[1] - 0.30], [c[0] + 0.30, c[1] + 0.30], [c[0] - 0.30, c[1] + 0.30]],
                   f'fill="#efebe9" stroke="{CAFE}" stroke-width="1.5"')
            L.texto(c[0], c[1] + 0.05, "CI", 7, f'fill="{CAFE}" font-weight="bold"')
        if cfg.get("desgrasadora"):
            c = cfg["desgrasadora"]
            L.poly([[c[0] - 0.30, c[1] - 0.30], [c[0] + 0.30, c[1] - 0.30], [c[0] + 0.30, c[1] + 0.30], [c[0] - 0.30, c[1] + 0.30]],
                   f'fill="#fff8e1" stroke="{CAFE}" stroke-width="1.5"')
            L.texto(c[0], c[1] + 0.05, "DG", 7, f'fill="{CAFE}" font-weight="bold"')
            L.texto(c[0] + 0.45, c[1] + 0.05, "desgrasadora", 7, f'fill="{CAFE}" text-anchor="start"')
    for ruta, d in ramas["desague"]:
        poli(ruta, f'stroke="{CAFE}" stroke-width="2" stroke-dasharray="7 3"')
        p, q = ruta[0], ruta[1]
        L.texto((p[0] + q[0]) / 2 + 0.12, (p[1] + q[1]) / 2, f"Ø{d}", 6, f'fill="{CAFE}" text-anchor="start"')
    # agua fría y caliente
    for linea in _lineas(cfg.get("agua_fria")):
        poli(linea, f'stroke="{AZUL}" stroke-width="2.5"')
    if cfg.get("bajada_tanque"):
        x, y = cfg["bajada_tanque"]["pos"]
        _circulo(L, x, y, 0.13, f'fill="{AZUL}"')
        L.texto(x + 0.25, y - 0.25, "AF ↓ bajada del tanque elevado", 7, f'fill="{AZUL}" text-anchor="start"')
    if cfg.get("impulsion"):
        poli(cfg["impulsion"], 'stroke="#00838f" stroke-width="2" stroke-dasharray="3 3"')
        a, b = cfg["impulsion"][0], cfg["impulsion"][-1]
        _circulo(L, b[0], b[1], 0.10, 'fill="#00838f"')
        L.texto(b[0] + 0.2, b[1] - 0.15, "↑ sube al tanque", 7, 'fill="#00838f" text-anchor="start"')
    if cfg.get("pozo"):
        x, y = cfg["pozo"]["pos"]
        _circulo(L, x, y, 0.45, 'fill="#e0f7fa" stroke="#00838f" stroke-width="1.5"')
        L.texto(x, y + 0.05, "POZO", 7, 'fill="#00838f" font-weight="bold"')
        L.texto(x, y + 0.70, "+ bomba", 7, 'fill="#00838f"')
    for ruta in ramas["agua_fria"]:
        poli([(x - 0.05, y) for x, y in ruta], f'stroke="{AZUL}" stroke-width="1.2"')
    for linea in _lineas(cfg.get("agua_caliente")):
        poli(linea, f'stroke="{ROJO}" stroke-width="2.5"')
    for ruta in ramas["agua_caliente"]:
        poli([(x + 0.05, y) for x, y in ruta], f'stroke="{ROJO}" stroke-width="1.2"')
    # gas
    if cfg.get("gas"):
        poli(cfg["gas"], f'stroke="{GAS}" stroke-width="2.5" stroke-dasharray="10 4"')
        a = cfg["gas"][0]
        L.texto(a[0] - 0.15, a[1] - 0.15, "GN ← medidor de gas (calle)", 7, 'fill="#9a6700" text-anchor="end"')
        b = cfg["gas"][-1]
        _circulo(L, b[0], b[1], 0.10, f'fill="{GAS}"')
        L.texto(b[0], b[1] - 0.18, "cocina", 6, 'fill="#9a6700"')
    if cfg.get("calefon"):
        x, y = cfg["calefon"]["pos"]
        L.poly([[x - 0.18, y - 0.30], [x + 0.18, y - 0.30], [x + 0.18, y + 0.30], [x - 0.18, y + 0.30]], f'fill="#fff" stroke="{ROJO}" stroke-width="1.5"')
        L.texto(x - 0.30, y - 0.40, "CALEFÓN (GN)", 7, f'fill="{ROJO}" font-weight="bold" text-anchor="end"')
    # ventilación: cielos falsos, cajones y ductos
    vent = casa.get("instalaciones", {}).get(nivel["id"], {}).get("ventilacion", {})
    VERDE = "#2e7d32"
    for c in (vent.get("cielos_falsos") or []) + (vent.get("cajones") or []):
        x0_, y0_, x1_, y1_ = c["rect"]
        L.poly([[x0_, y0_], [x1_, y0_], [x1_, y1_], [x0_, y1_]], f'fill="{VERDE}" fill-opacity="0.08" stroke="{VERDE}" stroke-width="0.8" stroke-dasharray="2 2"')
    for d in vent.get("ductos") or []:
        poli(d["linea"], f'stroke="{VERDE}" stroke-width="3.5" stroke-opacity="0.75"')
        (ax, ay), (bx, by) = d["linea"][-2], d["linea"][-1]
        n = math.hypot(bx - ax, by - ay)
        ux, uy = (bx - ax) / n, (by - ay) / n
        L.poly([[bx + ux * 0.25, by + uy * 0.25], [bx - uy * 0.15, by + ux * 0.15], [bx + uy * 0.15, by - ux * 0.15]], f'fill="{VERDE}"')
        sx, sy = d["linea"][0]
        if d.get("extractor"):
            _circulo(L, sx, sy, 0.16, f'fill="#e8f5e9" stroke="{VERDE}" stroke-width="1.2"')
            L.texto(sx, sy + 0.05, "E", 8, f'fill="{VERDE}" font-weight="bold"')
        L.texto(bx + ux * 0.4 + (0.1 if ux else 0), by + uy * 0.4 + (0.1 if uy else 0), f"Ø{d['diametro']} {d['id']}", 7,
                f'fill="{VERDE}" font-weight="bold" text-anchor="{"start" if ux >= 0 else "end"}"')
    # puntos de artefactos
    for p in puntos:
        x, y = p["pos"]
        _circulo(L, x, y, 0.09, f'fill="#fff" stroke="{CAFE}" stroke-width="1.5"')
    # leyenda
    lx, ly = x0 + 6, y1 + 1.15
    for k, (col, txt, dash) in enumerate([(AZUL, "agua fría", ""), (ROJO, "agua caliente", ""), ("#00838f", "pozo → tanque", 'stroke-dasharray="3 3"'),
                                          (CAFE, "desagüe", 'stroke-dasharray="7 3"'), (GAS, "gas natural", 'stroke-dasharray="10 4"'),
                                          ("#2e7d32", "ducto de aire (cielo falso punteado)", 'stroke-opacity="0.75"')]):
        cx = lx + k * 2.4
        L.linea(cx, ly, cx + 0.6, ly, f'stroke="{col}" stroke-width="2.5" {dash}')
        L.texto(cx + 0.75, ly + 0.05, txt, 7, 'fill="#444" text-anchor="start"')
    return L.svg(f"{nivel['nombre']} — sanitario y gas"), puntos


def main():
    casa = cargar()
    SALIDA.mkdir(exist_ok=True)
    salida = {}
    for nivel in casa["niveles"]:
        if not casa.get("instalaciones", {}).get(nivel["id"]):
            continue
        svg, puntos = plano_electrico(casa, nivel)
        f = SALIDA / f"planta-{nivel['id']}-electrico.svg"
        f.write_text(svg, encoding="utf-8")
        print("→", f.relative_to(SALIDA.parent))
        salida[nivel["id"]] = cuadro_cargas(puntos)
        svg, _ = plano_sanitario(casa, nivel)
        f = SALIDA / f"planta-{nivel['id']}-sanitario.svg"
        f.write_text(svg, encoding="utf-8")
        print("→", f.relative_to(SALIDA.parent))
    return salida


if __name__ == "__main__":
    for nivel, filas in main().items():
        print(f"\nCuadro de cargas {nivel}:")
        for r in filas:
            print(f"  {r['id']} {r['nombre']:45s} {r['puntos']:3d} pts {r['va']:6.0f} VA {r['a']:5.1f} A  {r['prot']:5s} {r['cable']}")
