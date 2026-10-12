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

from casa import SALIDA, _intervalo, aberturas, ambientes, area, caja, cargar, centroide, columnas, dentro, muebles, muros
from render_svg import ESC, Lienzo, dibujar_aberturas, dibujar_columnas, dibujar_escalera, dibujar_muros, flecha_norte, leyenda

TENSION = 220  # V

# Circuitos por nivel: (id, nombre, tipo)
CIRCUITOS = {
    "pb": [
        ("C1", "Iluminación zona social y exteriores", "luz"),
        ("C2", "Iluminación zona de servicio y estudio", "luz"),
        ("C3", "Tomas living, hall, ingreso y estudio", "toma"),
        ("C4", "Tomas comedor y cocina (generales)", "toma"),
        ("C5", "Cocina: refrigerador, freezer, campana, microondas", "especial"),
        ("C6", "Lavado: lavadoras (con diferencial)", "especial"),
        ("C7", "Tomas baño, depósito, almacén (con diferencial)", "toma"),
        ("C18", "Horno eléctrico", "especial"),
        ("C19", "Lavavajillas (con diferencial)", "especial"),
        ("C20", "Bomba de la cisterna (guardamotor + flotante)", "especial"),
        ("C21", "Tomas exteriores con tapa (con diferencial)", "toma"),
        ("C22", "Portón eléctrico", "especial"),
        ("C23", "Seguridad: alarma, cámaras, portero (con respaldo)", "especial"),
        ("C24", "Tomas estudio / invitados (computadora, router)", "toma"),
        ("C27", "Iluminación exterior: frente y retiro norte (balizas, apliques y sensores; fotocélula + reloj, con diferencial)", "luz"),
    ],
    "p1": [
        ("C8", "Iluminación P1: suite, hall, estar y blancos", "luz"),
        ("C9", "Tomas suite principal, hall y estar", "toma"),
        ("C10", "Tomas baños, blancos y vestidor; extractores (con diferencial)", "toma"),
        ("C11", "Tomas cuartos de los hijos", "toma"),
        ("C26", "Iluminación P1: cuartos de los hijos, sus baños, pasillo y vestíbulo", "luz"),
    ],
    "altillo": [
        ("C13", "Iluminación altillo (interior, terraza y franja)", "luz"),
        ("C14", "Tomas estar y dormitorio", "toma"),
        ("C15", "Tomas cocina, baño y lavandería (con diferencial)", "toma"),
        ("C16", "Anafe eléctrico", "especial"),
        ("C25", "Altillo: lavandería y tomas exteriores (con diferencial)", "toma"),
    ],
}
# Tomas comunes que se pasan a otro circuito según el ambiente (para no sobrecargar uno solo)
# Luces (y sus teclas) que se pasan a otro circuito de iluminación según el ambiente
LUZ_POR_AMBIENTE = {"p1": {a: "C26" for a in ("cuarto_hijo_1", "cuarto_hijo_2", "bano_hijo_1", "bano_hijo_2",
                                               "pasillo_p1", "vestibulo_hijos")}}
TOMA_POR_AMBIENTE = {"pb": {"estudio": "C24"}, "p1": {"cuarto_hijo_1": "C11", "cuarto_hijo_2": "C11"}}
# Qué circuito usa cada clase de punto, por nivel
USO = {
    "pb": {"luz_social": "C1", "luz": "C2", "luz_ext": "C1", "toma": "C3", "toma_comedor": "C4", "toma_humeda": "C7",
           "isla": "C4", "cocina_esp": "C5", "lavado": "C6", "horno": "C18", "lavavajillas": "C19", "bomba": "C20",
           "toma_ext": "C21", "porton": "C22", "seguridad": "C23"},
    "p1": {"luz_social": "C8", "luz": "C8", "luz_ext": "C8", "toma": "C9", "toma_comedor": "C9", "toma_humeda": "C10",
           "isla": "C9", "toma_ext": "C10"},
    "altillo": {"luz_social": "C13", "luz": "C13", "luz_ext": "C13", "toma": "C14", "toma_comedor": "C15",
                "toma_humeda": "C15", "isla": "C15", "cocina_esp": "C15", "anafe": "C16",
                "toma_ext": "C25", "lavado": "C25", "horno": "C15", "lavavajillas": "C15"},
}
SOCIALES = {"living", "ingreso", "hall", "pasillo_pb", "comedor", "terraza", "acceso"}
VA_LUZ, VA_TOMA = 100, 200

# Muebles que piden una toma especial: tipo/nombre -> [(letra, VA, clase de circuito, descripción)]
ESPECIALES = {
    "refrigerador": [("R", 300, "cocina_esp", "refrigerador")],
    "Freezer": [("F", 300, "cocina_esp", "freezer")],
    "Torre horno": [("H", 2500, "horno", "horno eléctrico"), ("M", 1200, "cocina_esp", "microondas")],
    "cocina": [("C", 150, "cocina_esp", "campana + encendido")],
    "Anafe": [("A", 3000, "anafe", "anafe eléctrico / inducción")],
    "Lavavajillas": [("LV", 1800, "lavavajillas", "lavavajillas")],
    "L": [("L", 800, "lavado", "lavadora")],
    "S": [("S", 2500, "lavado", "secadora")],
    "Lavadora manual": [("LM", 500, "lavado", "lavadora semiautomática")],
    "Termotanque": [("T", 2000, "termo", "termotanque eléctrico")],
}
# Muebles que piden una toma común extra en el muro de atrás (clase de uso)
TOMA_JUNTO = {"escritorio": "toma", "TV": "toma", "Isla": "isla", "lavamanos": "toma_humeda"}
# Muebles que no tapan un enchufe ni un interruptor (bajos o que se corren)
NO_TAPAN = {"alfombra", "mesa", "silla", "taburete"}
# Familias de puntos: un punto puesto a mano en `electrico.puntos` reemplaza a los generados de su familia en su ambiente
FAMILIA = {"interruptor": "tecla", "conmutador": "tecla", "toma": "toma", "toma_piso": "toma", "toma_ext": "toma",
           "datos": "datos", "luz": "luz"}


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


def _amb_de(casa, nivel_id, pos):
    return next((a for a in ambientes(casa, nivel_id) if dentro(a["poly"], *pos)), None)


def _dist_seg(p, a, b):
    dx, dy = b[0] - a[0], b[1] - a[1]
    L2 = dx * dx + dy * dy or 1e-9
    t = max(0, min(1, ((p[0] - a[0]) * dx + (p[1] - a[1]) * dy) / L2))
    return math.dist(p, (a[0] + t * dx, a[1] + t * dy))


def _dist_rect(p, r):
    dx = max(r[0] - p[0], 0, p[0] - r[2])
    dy = max(r[1] - p[1], 0, p[1] - r[3])
    return math.hypot(dx, dy)


def _caras(casa, nivel_id, amb):
    """Tramos de muro de LADRILLO del ambiente, sobre la cara que da al ambiente (con su espesor real):
    [(p, q, (nx, ny))], n = normal hacia adentro. Celosías, vanos y aberturas no son pared."""
    out = []
    pts = amb["poly"]
    for m in muros(casa, nivel_id):
        if m["tipo"] != "ladrillo":
            continue
        for p, q in zip(pts, pts[1:] + pts[:1]):
            iv = _intervalo(m["de"], m["a"], p, q)
            if not iv:
                continue
            t0, t1 = max(0.0, iv[0]), min(1.0, iv[1])
            (ax, ay), (bx, by) = m["de"], m["a"]
            s0 = (ax + (bx - ax) * t0, ay + (by - ay) * t0)
            s1 = (ax + (bx - ax) * t1, ay + (by - ay) * t1)
            L = math.dist(s0, s1)
            if L < 0.05:
                continue
            ux, uy = (s1[0] - s0[0]) / L, (s1[1] - s0[1]) / L
            nx, ny = -uy, ux
            mx, my = (s0[0] + s1[0]) / 2, (s0[1] + s1[1]) / 2
            if not dentro(pts, mx + nx * 0.2, my + ny * 0.2):
                nx, ny = -nx, -ny
            off = m["grosor"] / 2 + m["dx"] * nx + m["dy"] * ny
            r = 0.08 if L > 0.30 else 0.0       # sin las esquinas: ahí está el muro que llega de costado
            s0 = (s0[0] + ux * r, s0[1] + uy * r)
            s1 = (s1[0] - ux * r, s1[1] - uy * r)
            out.append(((s0[0] + nx * off, s0[1] + ny * off), (s1[0] + nx * off, s1[1] + ny * off), (nx, ny)))
    return out


def _en_cara(caras, pt, tol=0.03):
    return any(_dist_seg(pt, p, q) < tol for p, q, _ in caras)


def _giro(ab, ambs):
    """Rectángulo que barre una puerta batiente del lado al que abre (None si no aplica)."""
    if ab["tipo"] != "puerta" or ab.get("abre_hacia") not in ambs:
        return None
    (x0, y0), (x1, y1) = ab["de"], ab["a"]
    largo = math.dist((x0, y0), (x1, y1))
    cx, cy = centroide(ambs[ab["abre_hacia"]]["poly"])
    nx, ny = -(y1 - y0) / largo, (x1 - x0) / largo
    if (cx - x0) * nx + (cy - y0) * ny < 0:
        nx, ny = -nx, -ny
    xs = [x0, x1, x0 + nx * largo, x1 + nx * largo]
    ys = [y0, y1, y0 + ny * largo, y1 + ny * largo]
    return (min(xs), min(ys), max(xs), max(ys))


class _Entorno:
    """Lo que estorba a un enchufe o un interruptor en un nivel: columnas, aberturas, giros de puertas y muebles."""

    def __init__(self, casa, nivel_id):
        s = casa["estructura"]["seccion_columna"] / 2 + 0.05
        self.columnas = [(c["x"] - s, c["y"] - s, c["x"] + s, c["y"] + s) for c in columnas(casa)]
        self.aberturas = aberturas(casa, nivel_id)
        ambs = {a["id"]: a for a in ambientes(casa, nivel_id)}
        self.giros = [g for g in (_giro(ab, ambs) for ab in self.aberturas) if g]
        self.muebles = [m["rect"] for m in muebles(casa, nivel_id) if m["tipo"] not in NO_TAPAN]

    def libre(self, pt, margen_abertura=0.30, muebles=True):
        if any(_dist_rect(pt, r) < 0.01 for r in self.columnas):
            return False
        if any(_dist_seg(pt, ab["de"], ab["a"]) < margen_abertura for ab in self.aberturas):
            return False
        if any(_dist_rect(pt, g) < 0.01 for g in self.giros):
            return False
        if muebles and any(_dist_rect(pt, r) < 0.12 for r in self.muebles):
            return False
        return True


def _repartir(caras, n, libre, ocupados, sep=0.6):
    """n puntos repartidos sobre las caras de muro, en lugares libres y separados de `ocupados`."""
    cand = []
    for p, q, nrm in caras:
        L = math.dist(p, q)
        k = int(L / 0.05)
        for i in range(1, k):
            pt = (p[0] + (q[0] - p[0]) * i / k, p[1] + (q[1] - p[1]) * i / k)
            cand.append(pt)
    total = len(cand)
    out = []
    for j in range(n):
        objetivo = int(total * (j + 0.5) / n) if total else 0
        for d in range(total):
            hecho = False
            for idx in (objetivo + d, objetivo - d):
                if 0 <= idx < total:
                    pt = cand[idx]
                    if libre(pt) and all(math.dist(pt, o) >= sep for o in ocupados + out):
                        out.append(pt)
                        hecho = True
                        break
            if hecho:
                break
    return out


def _detras(rect, caras):
    """Punto del muro contra el que está apoyado el mueble (o None si está suelto, como una isla)."""
    x0, y0, x1, y1 = rect
    c = ((x0 + x1) / 2, (y0 + y1) / 2)
    mejor, clave = None, None
    for p, q, (nx, ny) in caras:
        if abs(nx) > 0.5:      # muro vertical: el mueble se apoya con su lado x0 o x1
            lo, hi = sorted([p[1], q[1]])
            if min(y1, hi) - max(y0, lo) < 0.10:
                continue
            d = (x0 - p[0]) if nx > 0 else (p[0] - x1)
            apoyo = min(y1, hi) - max(y0, lo)
            pt = (p[0], min(max(c[1], lo + 0.05), hi - 0.05))
        else:
            lo, hi = sorted([p[0], q[0]])
            if min(x1, hi) - max(x0, lo) < 0.10:
                continue
            d = (y0 - p[1]) if ny > 0 else (p[1] - y1)
            apoyo = min(x1, hi) - max(x0, lo)
            pt = (min(max(c[0], lo + 0.05), hi - 0.05), p[1])
        # el muro más cercano; si dos están igual de cerca (rincón), el del lado largo del mueble
        k = (round(d / 0.10), -round(apoyo, 2), d)
        if -0.05 <= d < 0.30 and (clave is None or k < clave):
            mejor, clave = pt, k
    return mejor


def _correr_fuera_de_columna(pt, caras, ent):
    """Si el punto cae en una columna, lo desliza por su muro hasta salir de ella."""
    if ent.libre(pt, margen_abertura=0.0, muebles=False):
        return pt
    for p, q, _ in caras:
        if _dist_seg(pt, p, q) > 0.03:
            continue
        L = math.dist(p, q)
        ux, uy = (q[0] - p[0]) / L, (q[1] - p[1]) / L
        for d in [k * 0.05 for k in range(1, 20)]:
            for sg in (1, -1):
                c = (pt[0] + ux * d * sg, pt[1] + uy * d * sg)
                if _dist_seg(c, p, q) < 0.01 and ent.libre(c, margen_abertura=0.0, muebles=False):
                    return c
    return pt


def _tecla_junto(casa, nivel_id, amb, ab, caras, ent, cara_amb=None):
    """Interruptor a 0.15 del marco, del lado de la manija si se puede, sobre muro del ambiente."""
    (ax, ay), (bx, by) = ab["de"], ab["a"]
    L = math.hypot(bx - ax, by - ay)
    ux, uy = (bx - ax) / L, (by - ay) / L
    for ex, ey, sg in ((bx, by, 1), (ax, ay, -1)):     # `a` = lado de la manija (la bisagra va en `de`)
        sx, sy = ex + ux * 0.15 * sg, ey + uy * 0.15 * sg
        for p, q, (nx, ny) in caras:
            d = (sx - p[0]) * nx + (sy - p[1]) * ny     # distancia del eje de la abertura a la cara
            if abs(d) > 0.30:                           # no es la línea de este muro
                continue
            pt = (sx - nx * d, sy - ny * d)
            if _dist_seg(pt, p, q) < 0.02 and ent.libre(pt, margen_abertura=0.10, muebles=True):
                return pt
    return None


def _accesos(casa, nivel_id, amb, abs_):
    propias = [ab for ab in abs_ if _borde_de(amb, ab) and ab["tipo"] != "ventana"]
    propias.sort(key=lambda ab: _prioridad_entrada(casa, nivel_id, amb, ab))
    return propias


def electrico(casa, nivel_id):
    """Devuelve (puntos, cables). puntos: dict(tipo, pos, circuito, etiqueta, va, amb, gen)."""
    puntos, cables = [], []
    uso = USO.get(nivel_id, USO["pb"])
    abs_ = aberturas(casa, nivel_id)
    mbs = muebles(casa, nivel_id)
    ambs = ambientes(casa, nivel_id)
    ent = _Entorno(casa, nivel_id)
    cfg = casa.get("instalaciones", {}).get(nivel_id, {}).get("electrico", {})
    extras = cfg.get("luces_extra") or []
    caras_de = {a["id"]: _caras(casa, nivel_id, a) for a in ambs}

    def agregar(**p):
        p.setdefault("gen", True)
        puntos.append(p)
        return len(puntos) - 1

    for amb in ambs:
        social = amb["id"] in SOCIALES
        circ_luz = uso["luz_social"] if social else uso["luz"]
        x0, y0, x1, y1 = caja(amb["poly"])
        caras = caras_de[amb["id"]]
        # luces
        if amb["tipo"] == "exterior":
            # bajo techo solo donde lo dice el modelo (luces_extra); si no hay, una al centro
            luces = [] if any(dentro(amb["poly"], *l["pos"]) for l in extras) else [centroide(amb["poly"])]
        elif area(amb["poly"]) < 12 or amb["tipo"] == "circulacion":
            luces = [centroide(amb["poly"])]
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
        for l in luces:
            agregar(tipo="luz", pos=l, circuito=circ_luz, va=VA_LUZ, amb=amb["id"])
        # interruptor junto al acceso principal; conmutador si hay un segundo acceso lejos (pasillos, halls, salas)
        if amb["tipo"] != "exterior":
            teclas = []
            for ab in _accesos(casa, nivel_id, amb, abs_):
                pt = _tecla_junto(casa, nivel_id, amb, ab, caras, ent)
                if pt is None:
                    continue
                if not teclas:
                    teclas.append(pt)
                elif amb["tipo"] in ("circulacion", "social") and math.dist(pt, teclas[0]) >= 3.0:
                    teclas.append(pt)
                    break
            for pt in teclas:
                agregar(tipo="conmutador" if len(teclas) > 1 else "interruptor", pos=pt, circuito=circ_luz, va=0,
                        amb=amb["id"])
        # tomas generales repartidas por los muros (no en exteriores ni en la cocina: van por mesón)
        if amb["tipo"] in ("social", "dormitorio", "servicio") or amb["id"] == "hall":
            per = sum(math.dist(a, b) for a, b in zip(amb["poly"], amb["poly"][1:] + amb["poly"][:1]))
            n = {"social": max(2, math.ceil(per / 4)), "dormitorio": max(3, math.ceil(per / 4))}.get(amb["tipo"], 1)
            circ = uso["toma_comedor"] if amb["id"] == "comedor" else (uso["toma_humeda"] if amb["tipo"] == "servicio" else uso["toma"])
            ocupados = [q["pos"] for q in puntos if q["tipo"] in ("toma", "interruptor", "conmutador")]
            for pt in _repartir(caras, n, ent.libre, ocupados):
                agregar(tipo="toma", pos=pt, circuito=circ, va=VA_TOMA, amb=amb["id"])
    # muebles: tomas especiales y tomas junto a muebles, en el muro de atrás
    especiales = []
    for m in mbs:
        x0, y0, x1, y1 = m["rect"]
        c = ((x0 + x1) / 2, (y0 + y1) / 2)
        amb = _amb_de(casa, nivel_id, c)
        caras = caras_de[amb["id"]] if amb else []
        atras = _detras(m["rect"], caras)
        if atras:
            atras = _correr_fuera_de_columna(atras, caras, ent)
        clave = m.get("nombre") if m.get("nombre") in ESPECIALES else m["tipo"]
        for k, (letra, va, circ, desc) in enumerate(ESPECIALES.get(clave, [])):
            base = atras or c
            v = _vertical(base, caras)
            pos = (base[0] + (0 if v else 0.30 * k), base[1] + (0.30 * k if v else 0))
            especiales.append(m["rect"])
            agregar(tipo="especial", pos=pos, circuito=uso.get(circ, uso["toma"]), va=va, etiqueta=letra, desc=desc,
                    amb=amb and amb["id"])
        clave = m.get("nombre") if m.get("nombre") in TOMA_JUNTO else m["tipo"]
        if clave in TOMA_JUNTO:
            circ = uso[TOMA_JUNTO[clave]]
            if atras:
                agregar(tipo="toma", pos=atras, circuito=circ, va=VA_TOMA, amb=amb and amb["id"])
            else:
                agregar(tipo="toma_piso", pos=c, circuito=circ, va=VA_TOMA, amb=amb and amb["id"])
            if clave in ("escritorio", "TV") and atras:
                v = _vertical(atras, caras)
                agregar(tipo="datos", pos=(atras[0] + (0 if v else 0.25), atras[1] + (0.25 if v else 0)),
                        circuito="-", va=0, amb=amb and amb["id"])
    # tomas sobre el mesón cada ~1.2 m, en el muro de atrás, a ≥ 0.60 de hornallas y lavaplatos
    peligro = [m["rect"] for m in mbs if m["tipo"] in ("cocina", "lavaplatos") or m.get("nombre") in ("Anafe",)]
    for m in mbs:
        if m["tipo"] != "meson" or m.get("nombre"):
            continue
        x0, y0, x1, y1 = m["rect"]
        amb = _amb_de(casa, nivel_id, ((x0 + x1) / 2, (y0 + y1) / 2))
        caras = caras_de[amb["id"]] if amb else []
        atras = _detras(m["rect"], caras)
        if not atras:
            continue
        horizontal = abs(atras[1] - (y0 + y1) / 2) > abs(atras[0] - (x0 + x1) / 2)
        lo, hi = (x0, x1) if horizontal else (y0, y1)
        cand = [lo + 0.15 + k * 0.05 for k in range(int((hi - lo - 0.30) / 0.05) + 1)]
        elegidos = []
        for t in cand:
            pt = (t, atras[1]) if horizontal else (atras[0], t)
            if any(_dist_rect(pt, r) < 0.60 for r in peligro):
                continue
            if any(_dist_rect(pt, r) < 0.05 for r in especiales):
                continue
            if not ent.libre(pt, margen_abertura=0.15, muebles=False):
                continue
            if all(math.dist(pt, e) >= 1.2 for e in elegidos):
                elegidos.append(pt)
        for pt in elegidos:
            agregar(tipo="toma", pos=pt, circuito=uso["toma_comedor"], va=VA_TOMA, amb=amb["id"])
    # extractores: al inicio de los ductos de ventilación que lo piden
    vent = casa.get("instalaciones", {}).get(nivel_id, {}).get("ventilacion", {})
    for d in vent.get("ductos") or []:
        if d.get("extractor"):
            agregar(tipo="extractor", pos=tuple(d["linea"][0]), circuito=uso["luz"] if nivel_id == "pb" else uso["toma_humeda"], va=50,
                    amb=None, gen=False)
    # luces puestas en el modelo: circuito según dónde caen
    for l in extras:
        amb = _amb_de(casa, nivel_id, l["pos"])
        if amb is None or amb["tipo"] == "exterior":
            circ = uso["luz_ext"]
        else:
            circ = uso["luz_social"] if amb["id"] in SOCIALES else uso["luz"]
        agregar(tipo="luz", pos=tuple(l["pos"]), circuito=circ, va=VA_LUZ, amb=amb and amb["id"], gen=False, id=l.get("id"))
    # bomba de agua (en la cisterna o en el pozo)
    san = casa.get("instalaciones", {}).get(nivel_id, {}).get("sanitario", {})
    fuente = san.get("cisterna") or san.get("pozo")
    if fuente and "bomba" in uso:
        agregar(tipo="especial", pos=tuple(fuente.get("bomba") or fuente["pos"]), circuito=uso["bomba"], va=fuente.get("va_bomba", 750), etiqueta="B",
                desc="bomba de agua", amb=None, gen=False)
    # seguridad: cargas del portón y de alarma + cámaras + portero (se dibujan aparte)
    seg = cfg.get("seguridad") or {}
    if seg.get("porton") and "porton" in uso:
        agregar(tipo="carga", pos=tuple(seg["porton"]["pos"]), circuito=uso["porton"], va=500, amb=None, gen=False)
    if (seg.get("alarma") or seg.get("camaras") or seg.get("portero")) and "seguridad" in uso:
        agregar(tipo="carga", pos=(0, 0), circuito=uso["seguridad"], va=50 + 15 * len(seg.get("camaras") or []) + 30, amb=None, gen=False)
    # puntos puestos a mano (interiorista): reemplazan a los generados de su familia en su ambiente
    manuales = cfg.get("puntos") or []

    def familia(q):    # una toma especial a mano reemplaza solo a la de su misma letra
        return ("especial", q.get("etiqueta")) if q["tipo"] == "especial" else FAMILIA.get(q["tipo"], q["tipo"])

    quitar = set()
    for mp in manuales:
        amb_id = mp.get("amb") or (_amb_de(casa, nivel_id, mp["pos"]) or {}).get("id")
        quitar.add((amb_id, familia(mp)))
    puntos[:] = [q for q in puntos if not (q.get("gen") and (q.get("amb"), familia(q)) in quitar)]
    for mp in manuales:
        if mp.get("quitar"):     # `quitar: true` = solo saca el generado (ej.: un exterior que no lleva luz propia)
            continue
        amb_id = mp.get("amb") or (_amb_de(casa, nivel_id, mp["pos"]) or {}).get("id")
        t = mp["tipo"]
        if mp.get("circuito"):
            circ = mp["circuito"]
        elif t in ("interruptor", "conmutador", "luz"):
            amb = next((a for a in ambs if a["id"] == amb_id), None)
            circ = uso["luz_social"] if amb_id in SOCIALES or (amb and amb["tipo"] == "exterior") else uso["luz"]
        elif t == "toma_ext":
            circ = uso["toma_ext"]
        elif t == "datos":
            circ = "-"
        else:
            amb = next((a for a in ambs if a["id"] == amb_id), None)
            tipo_amb = amb["tipo"] if amb else "social"
            circ = (uso["toma_comedor"] if tipo_amb == "cocina" or amb_id == "comedor"
                    else uso["toma_humeda"] if tipo_amb in ("bano", "servicio") else uso["toma"])
        if t == "especial" and not mp.get("circuito"):
            gen = next((q for q in ESPECIALES.values() for q in q if q[0] == mp.get("etiqueta")), None)
            circ = uso.get(gen[2], uso["toma"]) if gen else uso["toma"]
        va = mp.get("va", VA_TOMA if FAMILIA.get(t) == "toma" else VA_LUZ if t == "luz" else 0)
        if t == "especial" and "va" not in mp:
            va = next((q[1] for q in ESPECIALES.values() for q in q if q[0] == mp.get("etiqueta")), VA_TOMA)
        if t == "detector":
            circ, va = "-", 0
        agregar(tipo=t if t in FAMILIA or t in ("especial", "detector") else "toma", pos=tuple(mp["pos"]), circuito=circ, va=va,
                etiqueta=mp.get("etiqueta", ""), amb=amb_id, gen=False, manual=True, luces=mp.get("luces"),
                id=mp.get("id"), alto=mp.get("alto"))
    # luces y teclas a otro circuito de iluminación según el ambiente
    for q in puntos:
        nuevo = LUZ_POR_AMBIENTE.get(nivel_id, {}).get(q.get("amb"))
        if nuevo and q["tipo"] in ("luz", "interruptor", "conmutador") and q["circuito"] in (uso["luz"], uso["luz_social"]):
            q["circuito"] = nuevo
    # tomas comunes a otro circuito según el ambiente
    for amb in ambs:
        nuevo = TOMA_POR_AMBIENTE.get(nivel_id, {}).get(amb["id"])
        if nuevo:
            for q in puntos:
                if q["tipo"] == "toma" and q["circuito"] == uso["toma"] and dentro(amb["poly"], *q["pos"]):
                    q["circuito"] = nuevo
    # sin repetidos: tomas a menos de 0.25 de otra se juntan
    limpio = []
    for q in puntos:
        if q["tipo"] in ("toma", "toma_piso") and any(o["tipo"] == q["tipo"] and o.get("amb") == q.get("amb")
                                                      and math.dist(o["pos"], q["pos"]) < 0.25 for o in limpio):
            continue
        limpio.append(q)
    puntos[:] = limpio
    # cables: cada tecla a las luces de su ambiente, o a lo que dice `luces` (ids de ambientes o de luces).
    # Una luz con `id` nombrada por alguna tecla solo se une a las teclas que la nombran.
    nombradas = {d for q in puntos if q["tipo"] in ("interruptor", "conmutador") for d in (q.get("luces") or [])}
    for q in puntos:
        if q["tipo"] not in ("interruptor", "conmutador"):
            continue
        destinos = set(q.get("luces") or [q.get("amb")])
        for l in puntos:
            if l["tipo"] != "luz":
                continue
            if l.get("id") and l["id"] in nombradas:
                if l["id"] in destinos:
                    cables.append((q["pos"], l["pos"]))
            elif l.get("amb") in destinos:
                cables.append((q["pos"], l["pos"]))
    return puntos, cables


def _vertical(pt, caras):
    """¿El punto está sobre un muro vertical (x constante)?"""
    for p, q, (nx, ny) in caras:
        if _dist_seg(pt, p, q) < 0.03:
            return abs(nx) > 0.5
    return False


def cuadro_cargas(puntos, nivel_id="pb"):
    filas = []
    for cid, nombre, tipo in CIRCUITOS[nivel_id]:
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
    "Lavadora manual": (True, False, "50"), "Lavavajillas": (True, False, "50"), "Piletas": (True, True, "50"),
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
        if clave not in ARTEFACTOS and not m.get("agua"):
            continue
        af, ac, ds = ARTEFACTOS.get(clave, (True, False, None))    # `agua: true` = solo agua fría (dispensador)
        x0, y0, x1, y1 = m["rect"]
        c = ((x0 + x1) / 2, (y0 + y1) / 2)
        puntos.append({"pos": c, "af": af, "ac": ac, "desague": ds, "nombre": m.get("nombre") or m["tipo"]})
    for cn in cfg.get("canillas") or []:     # canillas de afuera: solo agua fría, sin desagüe
        puntos.append({"pos": tuple(cn["pos"]), "af": True, "ac": False, "desague": None, "nombre": "canilla",
                       "recorrido": [tuple(q) for q in cn.get("recorrido") or []]})   # `recorrido` = caño real (no la L más corta)
    ramas = {"agua_fria": [], "agua_caliente": [], "desague": []}
    for p in puntos:
        if p.get("recorrido"):
            ramas["agua_fria"].append(p["recorrido"])
        elif p["af"] and cfg.get("agua_fria"):
            ramas["agua_fria"].append(_escuadra(p["pos"], _proyectar(p["pos"], cfg["agua_fria"])))
        if p["ac"] and cfg.get("agua_caliente"):
            ramas["agua_caliente"].append(_escuadra(p["pos"], _proyectar(p["pos"], cfg["agua_caliente"])))
        if not p["desague"]:
            continue
        if cfg.get("colector"):
            ramas["desague"].append((_escuadra(p["pos"], _proyectar(p["pos"], cfg["colector"])), p["desague"]))
        elif cfg.get("bajantes"):
            amb = next((a["id"] for a in ambientes(casa, nivel_id) if dentro(a["poly"], *p["pos"])), None)
            cand = [b for b in cfg["bajantes"] if amb in b.get("ambientes", [amb])] or cfg["bajantes"]
            b = min(cand, key=lambda b: math.dist(p["pos"], b["pos"]))
            if b.get("entrada"):     # `entrada` = punto por donde los caños llegan a una bajante que está por fuera
                ruta = _escuadra(p["pos"], tuple(b["entrada"])) + [tuple(b["pos"])]
            else:
                ruta = _escuadra(p["pos"], tuple(b["pos"]))
            ramas["desague"].append((ruta, p["desague"]))
    # bajantes de los pisos de arriba: llegan a este nivel y van al colector por debajo del piso
    ramas["llegan"] = []
    if cfg.get("colector"):
        cota = {n["id"]: n["cota"] for n in casa["niveles"]}
        for nid, inst in (casa.get("instalaciones") or {}).items():
            if cota.get(nid, 0) <= cota.get(nivel_id, 0):
                continue
            for b in (inst.get("sanitario") or {}).get("bajantes") or []:
                if b.get("hasta") and cota.get(b["hasta"], 0) > cota.get(nivel_id, 0):
                    continue     # se une a otra bajante en un piso de arriba
                pos = tuple(b["pos"])
                if any(math.dist(pos, q[0]) < 0.3 for q in ramas["llegan"]):
                    continue
                ruta = [tuple(q) for q in b["recorrido_pb"]] if b.get("recorrido_pb") else _escuadra(pos, _proyectar(pos, cfg["colector"]))
                ramas["llegan"].append((pos, ruta, b.get("etiqueta", "")))
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
    dibujar_columnas(L, casa, nivel["id"])
    for a in ambs:
        cx, cy = a.get("etiqueta") or centroide(a["poly"])
        L.texto(cx, cy + 0.35, a["nombre"].upper(), 8, 'fill="#999" font-weight="bold"')
    flecha_norte(L, casa, x1 + 0.2, y1 + 1.4)
    leyenda(L, x0 - 0.5, y1 + 1.6, titulo, subt)
    return L, (x0, y0, x1, y1)


def _circulo(L, x, y, r, estilo):
    a, b = L.p(x, y)
    L.add(f'<circle cx="{a:.1f}" cy="{b:.1f}" r="{r * ESC:.1f}" {estilo}/>')


NARANJA = "#e65100"
# capas de los planos para el cuaderno de obra: qué tipos de punto entran en cada una
CAPA_LUCES = {"luz", "interruptor", "conmutador", "extractor", "detector"}
CAPA_TOMAS = {"toma", "toma_piso", "toma_ext", "especial", "datos"}


def _dibujar_punto(L, p, naranja=NARANJA):
    """Símbolo de un punto eléctrico (se usa en el plano y en las leyendas)."""
    x, y = p["pos"]
    t = p["tipo"]
    if t == "luz":
        _circulo(L, x, y, 0.16, f'fill="#fff3e0" stroke="{naranja}" stroke-width="1.2"')
        L.linea(x - 0.11, y - 0.11, x + 0.11, y + 0.11, f'stroke="{naranja}" stroke-width="1"')
        L.linea(x - 0.11, y + 0.11, x + 0.11, y - 0.11, f'stroke="{naranja}" stroke-width="1"')
    elif t in ("interruptor", "conmutador"):
        _circulo(L, x, y, 0.07, f'fill="{naranja}"')
        L.texto(x + 0.20, y + 0.05, "S" if t == "interruptor" else "Sc", 7, f'fill="{naranja}" font-weight="bold"')
    elif t in ("toma", "toma_piso", "toma_ext"):
        if t == "toma_piso":
            L.poly([[x - 0.13, y - 0.13], [x + 0.13, y - 0.13], [x + 0.13, y + 0.13], [x - 0.13, y + 0.13]],
                   'fill="none" stroke="#1565c0" stroke-width="1"')
        _circulo(L, x, y, 0.09, f'fill="{"#e3f2fd" if t == "toma_ext" else "#fff"}" stroke="#1565c0" stroke-width="1.2"')
        L.linea(x - 0.04, y - 0.05, x - 0.04, y + 0.05, 'stroke="#1565c0" stroke-width="1"')
        L.linea(x + 0.04, y - 0.05, x + 0.04, y + 0.05, 'stroke="#1565c0" stroke-width="1"')
        L.texto(x, y - 0.14, p.get("circuito", "") + (" IP" if t == "toma_ext" else ""), 6, 'fill="#1565c0"')
    elif t == "especial":
        L.poly([[x - 0.13, y - 0.13], [x + 0.13, y - 0.13], [x + 0.13, y + 0.13], [x - 0.13, y + 0.13]], 'fill="#1565c0"')
        et = p.get("etiqueta") or ""
        L.texto(x, y + 0.05, et, 8 if len(et) < 2 else 6, 'fill="#fff" font-weight="bold"')
        L.texto(x, y - 0.20, p.get("circuito", ""), 6, 'fill="#1565c0"')
    elif t == "datos":
        L.poly([[x, y - 0.11], [x + 0.11, y + 0.09], [x - 0.11, y + 0.09]], 'fill="#6a1b9a"')
    elif t == "extractor":
        _circulo(L, x, y, 0.16, 'fill="#e8f5e9" stroke="#2e7d32" stroke-width="1.2"')
        L.texto(x, y + 0.05, "E", 8, 'fill="#2e7d32" font-weight="bold"')
    elif t == "detector":
        _circulo(L, x, y, 0.13, 'fill="#fff" stroke="#c62828" stroke-width="1.5"')
        L.texto(x, y + 0.04, (p.get("etiqueta") or "D")[:1], 7, 'fill="#c62828" font-weight="bold"')


def plano_electrico(casa, nivel, capa=None, recorte=(None, None), leyenda_svg=True):
    """capa: None (todo), "luces" (luces, teclas y sus cables) o "tomas" (enchufes, especiales, tablero, débiles)."""
    puntos, cables = electrico(casa, nivel["id"])
    cfg = casa.get("instalaciones", {}).get(nivel["id"], {}).get("electrico", {})
    san = casa.get("instalaciones", {}).get(nivel["id"], {}).get("sanitario", {})
    pozo = san.get("cisterna") or san.get("pozo")
    sub = {"luces": " — LUCES E INTERRUPTORES", "tomas": " — ENCHUFES, TABLERO Y ESPECIALES"}.get(capa, "")
    L, (x0, y0, x1, y1) = _base(casa, nivel, f"{nivel['nombre'].upper()} — ELÉCTRICO{sub} (esquema)",
                                "Preliminar, para conversar con el electricista. Diseño definitivo según NB 777.",
                                [pozo["pos"]] if pozo else [])
    luces, tomas = capa in (None, "luces"), capa in (None, "tomas")
    naranja = NARANJA
    if luces:
        for a, b in cables:
            L.linea(a[0], a[1], b[0], b[1], f'stroke="{naranja}" stroke-width="0.8" stroke-dasharray="4 3"')
    for p in puntos:
        t = p["tipo"]
        if capa and t not in (CAPA_LUCES if capa == "luces" else CAPA_TOMAS):
            continue
        _dibujar_punto(L, p, naranja)
        x, y = p["pos"]
        if p.get("alto") and t != "luz":
            L.texto(x, y + 0.27, f"h{p['alto']:.2f}", 5, 'fill="#555"')
    if tomas and cfg.get("tablero"):
        x, y = cfg["tablero"]["pos"]
        L.poly([[x - 0.30, y - 0.10], [x + 0.30, y - 0.10], [x + 0.30, y + 0.08], [x - 0.30, y + 0.08]], 'fill="#212121"')
        L.texto(x, y + 0.03, "TD", 7, 'fill="#fff" font-weight="bold"')
        L.texto(x, y - 0.18, "tablero", 7, 'fill="#212121"')
    if tomas and cfg.get("acometida"):
        x, y = cfg["acometida"]["pos"]
        tx, ty = cfg["tablero"]["pos"]
        L.linea(x - 1.4, y, x, y, 'stroke="#212121" stroke-width="2"')
        L.linea(x, y, tx, ty, 'stroke="#212121" stroke-width="1.2" stroke-dasharray="6 3"')
        L.texto(x - 1.0, y - 0.15, "← medidor (calle)", 7, 'fill="#212121"')
    # alimentador entre el tablero y el montante (tubos que suben por las losas)
    for linea in _lineas(cfg.get("alimentador")) if tomas else []:
        for a, c in zip(linea, linea[1:]):
            L.linea(a[0], a[1], c[0], c[1], 'stroke="#212121" stroke-width="1.2" stroke-dasharray="6 3"')
    if tomas and cfg.get("montante"):
        x, y = cfg["montante"]["pos"]
        _circulo(L, x, y, 0.12, 'fill="#fff" stroke="#212121" stroke-width="1.5"')
        L.linea(x - 0.08, y + 0.08, x + 0.08, y - 0.08, 'stroke="#212121" stroke-width="1.2"')
        L.texto(x - 0.18, y + 0.30, cfg["montante"].get("etiqueta", "montante"), 6, 'fill="#212121" text-anchor="end"')
    if tomas and cfg.get("timbre"):
        x, y = cfg["timbre"]
        _circulo(L, x, y, 0.08, 'fill="#fff" stroke="#212121"')
        L.texto(x - 0.3, y + 0.05, "timbre", 6, 'fill="#212121"')
    for d in cfg.get("debiles") or [] if tomas else []:      # corrientes débiles: datos, cámaras, portero (tubo propio)
        L.add('<polyline points="%s" fill="none" stroke="#6a1b9a" stroke-width="1.2" stroke-dasharray="2 3"/>'
              % " ".join("%.1f,%.1f" % L.p(*q) for q in d["linea"]))
        b = d["linea"][-1]
        L.texto(b[0] + 0.15, b[1] - 0.12, d.get("etiqueta", ""), 6, 'fill="#6a1b9a" text-anchor="start"')
    if tomas and cfg.get("puesta_tierra"):
        x, y = cfg["puesta_tierra"]["pos"]
        _dibujar_tierra(L, x, y)
        L.texto(x, y + 0.40, "puesta a tierra", 6, 'fill="#2e7d32"')
        if cfg.get("tablero"):
            tx, ty = cfg["tablero"]["pos"]
            L.linea(x, y - 0.25, tx, ty, 'stroke="#2e7d32" stroke-width="1" stroke-dasharray="5 3"')
    if tomas:
        _dibujar_seguridad(L, cfg.get("seguridad") or casa.get("instalaciones", {}).get(nivel["id"], {}).get("seguridad"))
    # leyenda de símbolos
    if leyenda_svg:
        lx, ly = x0 + 6, y1 + 1.15
        items = [("luz", "luz de techo"), ("interruptor", "interruptor (Sc = conmutador)"), ("toma", "tomacorriente (circuito)"),
                 ("especial", "toma especial"), ("datos", "datos / TV"), ("extractor", "extractor")]
        for k, (t, txt) in enumerate(items):
            cx = lx + k * 2.2
            fake = {"tipo": t, "pos": (cx, ly), "circuito": "", "etiqueta": "X"}
            _dibujar_simbolo(L, fake, naranja)
            L.texto(cx + 0.25, ly + 0.05, txt, 7, 'fill="#444" text-anchor="start"')
    return L.svg(f"{nivel['nombre']} — eléctrico", *recorte), puntos


def _dibujar_tierra(L, x, y):
    for k, w in enumerate((0.22, 0.14, 0.06)):
        L.linea(x - w, y + k * 0.07, x + w, y + k * 0.07, 'stroke="#2e7d32" stroke-width="1.5"')
    L.linea(x, y - 0.25, x, y, 'stroke="#2e7d32" stroke-width="1.5"')


def _dibujar_seguridad(L, seg):
    """Portón, portero, cámaras y alarma (esquema; lo define el instalador)."""
    if not seg:
        return
    VIO = "#6a1b9a"
    if seg.get("porton"):
        x, y = seg["porton"]["pos"]
        L.linea(x - 1.4, y, x, y, f'stroke="{VIO}" stroke-width="2"')
        L.texto(x - 1.0, y - 0.15, seg["porton"].get("etiqueta", "← portón con motor + portero (calle)"), 7,
                f'fill="{VIO}" text-anchor="start"')
    if seg.get("portero"):
        x, y = seg["portero"]["pos"]
        L.poly([[x - 0.10, y - 0.10], [x + 0.10, y - 0.10], [x + 0.10, y + 0.10], [x - 0.10, y + 0.10]], f'fill="#fff" stroke="{VIO}" stroke-width="1.2"')
        L.texto(x, y + 0.04, "P", 6, f'fill="{VIO}" font-weight="bold"')
        panel = seg["portero"].get("panel") or (seg.get("porton") or {}).get("pos")   # frente de calle del portero
        tramo = seg["portero"].get("recorrido") or ([panel, [x, y]] if panel else [])   # `recorrido` = tubo real
        for (ax, ay), (bx, by) in zip(tramo, tramo[1:]):
            L.linea(ax, ay, bx, by, f'stroke="{VIO}" stroke-width="0.8" stroke-dasharray="4 3"')
    for c in seg.get("camaras") or []:
        x, y = c["pos"]
        L.poly([[x - 0.12, y - 0.08], [x + 0.08, y - 0.08], [x + 0.08, y + 0.08], [x - 0.12, y + 0.08]], f'fill="{VIO}"')
        L.poly([[x + 0.08, y - 0.04], [x + 0.18, y - 0.10], [x + 0.18, y + 0.10], [x + 0.08, y + 0.04]], f'fill="{VIO}"')
    al = seg.get("alarma") or {}
    for clave, letra in (("central", "AL"), ("teclado", "TK"), ("sirena", "SI")):
        if al.get(clave):
            x, y = al[clave]["pos"] if isinstance(al[clave], dict) else al[clave]
            L.poly([[x - 0.14, y - 0.10], [x + 0.14, y - 0.10], [x + 0.14, y + 0.10], [x - 0.14, y + 0.10]], f'fill="{VIO}"')
            L.texto(x, y + 0.04, letra, 5, 'fill="#fff" font-weight="bold"')
    for s_ in al.get("sensores") or []:
        x, y = s_["pos"]
        _circulo(L, x, y, 0.07, f'fill="#fff" stroke="{VIO}" stroke-width="1.2"')
        L.texto(x, y - 0.12, "PIR" if s_.get("tipo") == "movimiento" else "MG", 5, f'fill="{VIO}"')


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


def plano_sanitario(casa, nivel, capa=None, recorte=(None, None), leyenda_svg=True):
    """capa: None (todo), "agua" (fría, caliente, bomba), "desague" (cloacal y lluvia) o "gas" (gas y ventilación)."""
    cfg, puntos, ramas = sanitario(casa, nivel["id"])
    extra = [cfg[k]["pos"] for k in ("pozo", "cisterna") if cfg.get(k)]
    tit = {"agua": "AGUA FRÍA Y CALIENTE", "desague": "DESAGÜE Y LLUVIA", "gas": "GAS Y VENTILACIÓN"}.get(
        capa, "AGUA, DESAGÜE, GAS Y VENTILACIÓN")
    L, (x0, y0, x1, y1) = _base(casa, nivel, f"{nivel['nombre'].upper()} — {tit} (esquema)",
                                "Preliminar: recorridos y diámetros a confirmar con el instalador (agua/desagüe) y con YPFB (gas natural).",
                                extra)
    agua, desague, gas = (capa in (None, k) for k in ("agua", "desague", "gas"))
    AZUL, ROJO, CAFE, GAS, PLUVIAL = "#1565c0", "#c62828", "#6d4c41", "#f9a825", "#0097a7"

    def poli(linea, estilo):
        L.add('<polyline points="%s" fill="none" %s/>' % (" ".join("%.1f,%.1f" % L.p(*q) for q in linea), estilo))

    # desagüe
    if desague and cfg.get("colector"):
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
    for b in cfg.get("bajantes") or [] if desague else []:
        x, y = b["pos"]
        _circulo(L, x, y, 0.16, f'fill="#efebe9" stroke="{CAFE}" stroke-width="1.8"')
        L.texto(x, y + 0.05, "BV", 6, f'fill="{CAFE}" font-weight="bold"')
        if b.get("etiqueta"):
            L.texto(x + 0.25, y - 0.22, b["etiqueta"], 7, f'fill="{CAFE}" text-anchor="start"')
        L.texto(x + 0.25, y + 0.32, "ventila ↑ sobre el techo", 6, f'fill="{CAFE}" text-anchor="start"')
    for pos, ruta, etiqueta in ramas.get("llegan", []) if desague else []:
        poli(ruta, f'stroke="{CAFE}" stroke-width="2.5" stroke-dasharray="2 3"')
        _circulo(L, pos[0], pos[1], 0.16, f'fill="{CAFE}" stroke="{CAFE}" stroke-width="1.5"')
        L.texto(pos[0], pos[1] + 0.05, "BV", 6, 'fill="#fff" font-weight="bold"')
        L.texto(pos[0] + 0.22, pos[1] + 0.35, "↓ de arriba Ø110 (bajo el piso, antes del contrapiso)", 6, f'fill="{CAFE}" text-anchor="start"')
    for ruta, d in ramas["desague"] if desague else []:
        poli(ruta, f'stroke="{CAFE}" stroke-width="2" stroke-dasharray="7 3"')
        p, q = ruta[0], ruta[1]
        L.texto((p[0] + q[0]) / 2 + 0.12, (p[1] + q[1]) / 2, f"Ø{d}", 6, f'fill="{CAFE}" text-anchor="start"')
    # pluvial (bajantes de lluvia, sumideros de afuera): nunca al desagüe sanitario
    for pl in cfg.get("pluvial") or [] if desague else []:
        if pl.get("rect"):       # pozo de absorción, registro pluvial
            px0, py0, px1, py1 = pl["rect"]
            L.poly([[px0, py0], [px1, py0], [px1, py1], [px0, py1]], f'fill="#e0f7fa" stroke="{PLUVIAL}" stroke-width="1.5"')
            x, y = px0, py1 + 0.30
        else:
            poli(pl["linea"], f'stroke="{PLUVIAL}" stroke-width="2.2" stroke-dasharray="2 3"')
            x, y = pl["linea"][-1]
            x, y = x + 0.15, y - 0.15
        if pl.get("etiqueta_pos"):     # [x, y] a mano, el texto termina ahí (a la izquierda)
            x, y = pl["etiqueta_pos"]
        if pl.get("etiqueta"):
            L.texto(x, y, pl["etiqueta"], 6, f'fill="{PLUVIAL}" text-anchor="{"end" if pl.get("etiqueta_pos") else "start"}"')
    # agua fría y caliente
    for linea in _lineas(cfg.get("agua_fria")) if agua else []:
        poli(linea, f'stroke="{AZUL}" stroke-width="2.5"')
    if agua and cfg.get("bajada_tanque"):
        x, y = cfg["bajada_tanque"]["pos"]
        _circulo(L, x, y, 0.13, f'fill="{AZUL}"')
        L.texto(x + 0.25, y - 0.25, cfg["bajada_tanque"].get("etiqueta", "AF ↓ bajada del tanque elevado"), 7, f'fill="{AZUL}" text-anchor="start"')
    if agua and cfg.get("impulsion"):
        poli(cfg["impulsion"], 'stroke="#00838f" stroke-width="2" stroke-dasharray="3 3"')
        a, b = cfg["impulsion"][0], cfg["impulsion"][-1]
        _circulo(L, b[0], b[1], 0.10, 'fill="#00838f"')
        L.texto(b[0] + 0.2, b[1] - 0.15, "↑ sube al tanque", 7, 'fill="#00838f" text-anchor="start"')
    if agua and cfg.get("cisterna"):
        cis = cfg["cisterna"]
        x, y = cis["pos"]
        cx0, cy0, cx1, cy1 = cis.get("rect") or [x - 0.8, y - 0.6, x + 0.8, y + 0.6]
        L.poly([[cx0, cy0], [cx1, cy0], [cx1, cy1], [cx0, cy1]], 'fill="#e0f7fa" stroke="#00838f" stroke-width="1.5" stroke-dasharray="4 2"')
        if cis.get("tapa"):            # tapa de inspección 0.60 × 0.60
            tx, ty = cis["tapa"]
            L.poly([[tx - 0.3, ty - 0.3], [tx + 0.3, ty - 0.3], [tx + 0.3, ty + 0.3], [tx - 0.3, ty + 0.3]], 'fill="none" stroke="#00838f" stroke-width="1"')
        if cis.get("bomba"):           # bomba (cámara seca o sumergible)
            bx, by = cis["bomba"]
            _circulo(L, bx, by, 0.18, 'fill="#fff" stroke="#00838f" stroke-width="1.5"')
            L.texto(bx, by + 0.05, "B", 7, 'fill="#00838f" font-weight="bold"')
        L.texto(x, cy0 - 0.15, cis.get("etiqueta", "CISTERNA (existente) + bomba"), 7, 'fill="#00838f" font-weight="bold"')
        L.texto(x, cy1 + 0.30, "← SEMAPA (medidor en la calle)", 6, 'fill="#00838f"')
    if agua and cfg.get("pozo"):
        x, y = cfg["pozo"]["pos"]
        _circulo(L, x, y, 0.45, 'fill="#e0f7fa" stroke="#00838f" stroke-width="1.5"')
        L.texto(x, y + 0.05, "POZO", 7, 'fill="#00838f" font-weight="bold"')
        L.texto(x, y + 0.70, "+ bomba", 7, 'fill="#00838f"')
    for ruta in ramas["agua_fria"] if agua else []:
        poli([(x - 0.05, y) for x, y in ruta], f'stroke="{AZUL}" stroke-width="1.2"')
    for linea in _lineas(cfg.get("agua_caliente")) if agua else []:
        poli(linea, f'stroke="{ROJO}" stroke-width="2.5"')
    for ruta in ramas["agua_caliente"] if agua else []:
        poli([(x + 0.05, y) for x, y in ruta], f'stroke="{ROJO}" stroke-width="1.2"')
    # gas
    if gas and cfg.get("gas"):
        poli(cfg["gas"], f'stroke="{GAS}" stroke-width="2.5" stroke-dasharray="10 4"')
        a = cfg["gas"][0]
        L.texto(a[0] - 0.15, a[1] - 0.15, cfg.get("gas_inicio", "GN ← medidor de gas (calle)"), 7, 'fill="#9a6700" text-anchor="end"')
        b = cfg["gas"][-1]
        _circulo(L, b[0], b[1], 0.10, f'fill="{GAS}"')
        L.texto(b[0], b[1] - 0.18, cfg.get("gas_fin", "cocina"), 6, 'fill="#9a6700"')
    for g in cfg.get("gas_ramales") or [] if gas else []:     # ramales extra (p. ej. la subida al calefón)
        poli(g["linea"], f'stroke="{GAS}" stroke-width="2.5" stroke-dasharray="10 4"')
        b = g["linea"][-1]
        _circulo(L, b[0], b[1], 0.10, f'fill="{GAS}"')
        L.texto(b[0] + 0.15, b[1] - 0.18, g.get("etiqueta", ""), 6, 'fill="#9a6700" text-anchor="start"')
    if agua and cfg.get("subida_caliente"):
        x, y = cfg["subida_caliente"]["pos"]
        _circulo(L, x, y, 0.13, f'fill="{ROJO}"')
        L.texto(x - 0.25, y - 0.25, cfg["subida_caliente"].get("etiqueta", "AC ↑ desde el calefón"), 7, f'fill="{ROJO}" text-anchor="end"')
    if agua and cfg.get("termotanque"):
        x, y = cfg["termotanque"]["pos"]
        _circulo(L, x, y, 0.22, f'fill="#fff" stroke="{ROJO}" stroke-width="1.8"')
        L.texto(x, y + 0.05, "TT", 7, f'fill="{ROJO}" font-weight="bold"')
        L.texto(x + 0.30, y - 0.30, "TERMOTANQUE (eléctrico)", 7, f'fill="{ROJO}" font-weight="bold" text-anchor="start"')
    if (agua or gas) and cfg.get("calefon"):
        x, y = cfg["calefon"]["pos"]
        L.poly([[x - 0.18, y - 0.30], [x + 0.18, y - 0.30], [x + 0.18, y + 0.30], [x - 0.18, y + 0.30]], f'fill="#fff" stroke="{ROJO}" stroke-width="1.5"')
        L.texto(x - 0.30, y - 0.40, "CALEFÓN (GN)", 7, f'fill="{ROJO}" font-weight="bold" text-anchor="end"')
    # ventilación: cielos falsos, cajones y ductos
    vent = casa.get("instalaciones", {}).get(nivel["id"], {}).get("ventilacion", {})
    VERDE = "#2e7d32"
    for c in (vent.get("cielos_falsos") or []) + (vent.get("cajones") or []):
        x0_, y0_, x1_, y1_ = c["rect"]
        if c.get("ducto"):      # ducto vertical de ladrillo (caños que suben por dentro): gris macizo
            L.poly([[x0_, y0_], [x1_, y0_], [x1_, y1_], [x0_, y1_]], 'fill="#9e9e9e" fill-opacity="0.55" stroke="#424242" stroke-width="1.2"')
            continue
        if not gas:
            continue
        L.poly([[x0_, y0_], [x1_, y0_], [x1_, y1_], [x0_, y1_]], f'fill="{VERDE}" fill-opacity="0.08" stroke="{VERDE}" stroke-width="0.8" stroke-dasharray="2 2"')
    for d in vent.get("ductos") or [] if gas else []:
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
    # llaves de paso (agua y gas), rejillas de ventilación de ambientes con gas, ventilaciones de desagüe, sumideros
    for ll in cfg.get("llaves") or []:
        x, y = ll["pos"]
        if not (gas if ll.get("gas") else agua):
            continue
        col = GAS if ll.get("gas") else AZUL
        L.poly([[x - 0.10, y - 0.10], [x + 0.10, y + 0.10], [x + 0.10, y - 0.10], [x - 0.10, y + 0.10]], f'fill="{col}" stroke="{col}"')
        L.texto(x + 0.15, y - 0.12, ll.get("etiqueta", "LL"), 6, f'fill="{col}" text-anchor="start"')
    for r in cfg.get("rejillas") or [] if gas else []:
        x, y = r["pos"]
        L.poly([[x - 0.15, y - 0.06], [x + 0.15, y - 0.06], [x + 0.15, y + 0.06], [x - 0.15, y + 0.06]], 'fill="#fff" stroke="#9a6700" stroke-width="1.2"')
        L.texto(x, y - 0.12, r.get("etiqueta", "rejilla"), 6, 'fill="#9a6700"')
    for v in cfg.get("ventilaciones") or [] if desague else []:
        x, y = v["pos"]
        _circulo(L, x, y, 0.10, f'fill="#fff" stroke="{CAFE}" stroke-width="1.2" stroke-dasharray="2 1"')
        L.texto(x + 0.15, y + 0.30, v.get("etiqueta", "V ↑ sobre el techo"), 6, f'fill="{CAFE}" text-anchor="start"')
    for sd in cfg.get("sumideros") or [] if desague else []:
        x, y = sd["pos"]
        L.poly([[x - 0.10, y - 0.10], [x + 0.10, y - 0.10], [x + 0.10, y + 0.10], [x - 0.10, y + 0.10]], f'fill="#efebe9" stroke="{CAFE}" stroke-width="1.2"')
        L.texto(x + 0.15, y - 0.15, sd.get("etiqueta", "sumidero"), 6, f'fill="{CAFE}" text-anchor="start"')
    for cn in cfg.get("canillas") or [] if agua else []:
        x, y = cn["pos"]
        L.texto(x + 0.15, y + 0.25, cn.get("etiqueta", "canilla"), 6, f'fill="{AZUL}" text-anchor="start"')
    # puntos de artefactos
    for p in puntos if agua or desague else []:
        x, y = p["pos"]
        _circulo(L, x, y, 0.09, f'fill="#fff" stroke="{CAFE}" stroke-width="1.5"')
    # leyenda
    if not leyenda_svg:
        return L.svg(f"{nivel['nombre']} — sanitario y gas", *recorte), puntos
    lx, ly = x0 + 6, y1 + 1.15
    for k, (col, txt, dash) in enumerate([(AZUL, "agua fría", ""), (ROJO, "agua caliente", ""), ("#00838f", "bomba → tanque", 'stroke-dasharray="3 3"'),
                                          (CAFE, "desagüe", 'stroke-dasharray="7 3"'), (PLUVIAL, "pluvial", 'stroke-dasharray="2 3"'),
                                          (GAS, "gas natural", 'stroke-dasharray="10 4"'),
                                          ("#2e7d32", "ducto de aire (cielo falso punteado)", 'stroke-opacity="0.75"')]):
        cx = lx + k * 2.4
        L.linea(cx, ly, cx + 0.6, ly, f'stroke="{col}" stroke-width="2.5" {dash}')
        L.texto(cx + 0.75, ly + 0.05, txt, 7, 'fill="#444" text-anchor="start"')
    return L.svg(f"{nivel['nombre']} — sanitario y gas", *recorte), puntos


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
        salida[nivel["id"]] = cuadro_cargas(puntos, nivel["id"])
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
