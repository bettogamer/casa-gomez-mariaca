"""Carga del modelo `modelo/casa.yaml` y geometría básica compartida por las herramientas."""
from pathlib import Path

import yaml

RAIZ = Path(__file__).resolve().parent.parent
MODELO = RAIZ / "modelo" / "casa.yaml"
SALIDA = RAIZ / "salida"
GARGANTA = 0.15  # espesor supuesto de la losa de la escalera y del descanso (m)

COLORES_TIPO = {
    "social": "#f6e7c8",
    "dormitorio": "#d9e7f5",
    "bano": "#cdeee9",
    "cocina": "#f8d9c9",
    "servicio": "#e6e1ef",
    "circulacion": "#efefef",
    "exterior": "#e3efd6",
}


def cargar(ruta=MODELO):
    with open(ruta, encoding="utf-8") as f:
        casa = yaml.safe_load(f)
    for seccion in ("ambientes", "referencia"):
        for nivel in casa["niveles"]:
            for amb in (casa.get(seccion) or {}).get(nivel["id"]) or []:
                amb["poly"] = poligono(amb)
    return casa


def poligono(amb):
    if "rect" in amb:
        x0, y0, x1, y1 = amb["rect"]
        return [[x0, y0], [x1, y0], [x1, y1], [x0, y1]]
    return [list(p) for p in amb["poly"]]


def area(poly):
    s = 0.0
    for (x0, y0), (x1, y1) in zip(poly, poly[1:] + poly[:1]):
        s += x0 * y1 - x1 * y0
    return abs(s) / 2


def caja(poly):
    xs = [p[0] for p in poly]
    ys = [p[1] for p in poly]
    return min(xs), min(ys), max(xs), max(ys)


def centroide(poly):
    a = 0.0
    cx = cy = 0.0
    for (x0, y0), (x1, y1) in zip(poly, poly[1:] + poly[:1]):
        f = x0 * y1 - x1 * y0
        a += f
        cx += (x0 + x1) * f
        cy += (y0 + y1) * f
    if abs(a) < 1e-9:
        x0, y0, x1, y1 = caja(poly)
        return (x0 + x1) / 2, (y0 + y1) / 2
    return cx / (3 * a), cy / (3 * a)


def dentro(poly, x, y):
    """Punto en polígono (ray casting)."""
    ok = False
    n = len(poly)
    for i in range(n):
        x0, y0 = poly[i]
        x1, y1 = poly[(i + 1) % n]
        if (y0 > y) != (y1 > y) and x < (x1 - x0) * (y - y0) / (y1 - y0) + x0:
            ok = not ok
    return ok


def dist_borde(poly, x, y):
    """Distancia mínima del punto a los bordes del polígono."""
    best = float("inf")
    for (x0, y0), (x1, y1) in zip(poly, poly[1:] + poly[:1]):
        dx, dy = x1 - x0, y1 - y0
        L2 = dx * dx + dy * dy
        t = 0 if L2 == 0 else max(0, min(1, ((x - x0) * dx + (y - y0) * dy) / L2))
        px, py = x0 + t * dx, y0 + t * dy
        best = min(best, ((x - px) ** 2 + (y - py) ** 2) ** 0.5)
    return best


def columnas(casa):
    est = casa["estructura"]
    desp = est.get("desplazadas") or {}
    out = []
    for cid in est["columnas_en"]:
        fila, eje = cid[0], cid[1:]
        x = est["ejes_x"][eje]
        y = est["ejes_y"][fila]
        if cid in desp:
            x = desp[cid].get("x", x)
            y = desp[cid].get("y", y)
        out.append({"id": cid, "x": x, "y": y})
    return out


def huella_casa(casa):
    """Caja exterior de la casa (columnas extremas + media pared)."""
    cols = columnas(casa)
    m = casa["estructura"]["espesor_muro_ext"] / 2
    xs = [c["x"] for c in cols]
    ys = [c["y"] for c in cols]
    return min(xs) - m, min(ys) - m, max(xs) + m, max(ys) + m


def ambientes(casa, nivel_id):
    return casa["ambientes"].get(nivel_id) or []


def referencia(casa, nivel_id):
    return (casa.get("referencia") or {}).get(nivel_id) or []


def aberturas(casa, nivel_id):
    return (casa.get("aberturas") or {}).get(nivel_id) or []


def _intervalo(a, b, c, d, tol=0.02):
    """Si el segmento c-d es colineal con a-b, devuelve su intervalo [t0, t1] sobre a-b (0..1)."""
    dx, dy = b[0] - a[0], b[1] - a[1]
    L = (dx * dx + dy * dy) ** 0.5
    if L < 1e-9:
        return None
    for p in (c, d):
        if abs((p[0] - a[0]) * dy - (p[1] - a[1]) * dx) / L > tol:
            return None
    t = sorted(((p[0] - a[0]) * dx + (p[1] - a[1]) * dy) / (L * L) for p in (c, d))
    return t if t[1] > 0 and t[0] < 1 else None


def _restar(a, b, cortes):
    """Partes del segmento a-b que no cubren los segmentos de `cortes`."""
    tramos = [(0.0, 1.0)]
    for c, d in cortes:
        iv = _intervalo(a, b, c, d)
        if not iv:
            continue
        nuevos = []
        for t0, t1 in tramos:
            if iv[1] <= t0 or iv[0] >= t1:
                nuevos.append((t0, t1))
                continue
            if iv[0] > t0:
                nuevos.append((t0, iv[0]))
            if iv[1] < t1:
                nuevos.append((iv[1], t1))
        tramos = nuevos
    L = ((b[0] - a[0]) ** 2 + (b[1] - a[1]) ** 2) ** 0.5
    return [([a[0] + (b[0] - a[0]) * t0, a[1] + (b[1] - a[1]) * t0],
             [a[0] + (b[0] - a[0]) * t1, a[1] + (b[1] - a[1]) * t1])
            for t0, t1 in tramos if (t1 - t0) * L > 0.01]


def muros(casa, nivel_id):
    """Muros del nivel como segmentos {de, a, tipo}.

    Los bordes de ambientes no exteriores son muro de ladrillo (sin duplicar bordes
    compartidos), menos las aberturas y los muros especiales; luego se agregan los
    muros especiales (celosía, etc.) con su tipo.
    """
    especiales = (casa.get("muros") or {}).get(nivel_id) or []
    cortes = [(m["de"], m["a"]) for m in especiales] + [(ab["de"], ab["a"]) for ab in aberturas(casa, nivel_id)]
    hechos = []
    out = []
    for amb in ambientes(casa, nivel_id):
        if amb["tipo"] == "exterior":
            continue
        pts = amb["poly"]
        for a, b in zip(pts, pts[1:] + pts[:1]):
            for c, d in _restar(a, b, cortes + hechos):
                hechos.append((c, d))
                out.append({"de": c, "a": d, "tipo": "ladrillo"})
    for m in especiales:
        out.append({"de": m["de"], "a": m["a"], "tipo": m["tipo"], "id": m.get("id"), "alto": m.get("alto")})
    return out


def escalera(casa):
    """Geometría de la escalera por piso, calculada desde huella/contrahuella/tramos.

    Convención (escalera en U): el primer tramo sube hacia el eje A, el descanso queda contra
    la pared del eje A y el segundo tramo vuelve hacia el eje C. El descanso cuenta como una
    contrahuella; el último escalón del segundo tramo es el piso de llegada.
    Devuelve una lista (una entrada por piso) con peldaños y descanso como cajas
    {x0, y0, x1, y1, z} (z = altura de la pisada, absoluta).
    """
    est = casa["estructura"]
    esc = est["escalera"]
    cota = {n["id"]: n["cota"] for n in casa["niveles"]}
    m = est["seccion_columna"] / 2
    ancho, hu, ch = esc["ancho_tramo"], esc["huella"], esc["contrahuella"]
    xl = est["ejes_x"]["2"] + m
    xr = est["ejes_x"]["3"] - m
    y_desc0 = est["ejes_y"]["A"] + est["espesor_muro_ext"] / 2
    y_desc1 = y_desc0 + esc["descanso_fondo"]

    def franja(lado):
        return (xl, xl + ancho) if lado == "2" else (xr - ancho, xr)

    out = []
    for piso in esc["pisos"]:
        base = cota[piso["desde"]]
        t1, t2 = piso["tramos"]
        n1, n2 = t1["escalones"], t2["escalones"]
        peldanos = []
        x0, x1 = franja(t1["lado"])
        inicio = y_desc1 + n1 * hu
        for i in range(n1):
            peldanos.append({"x0": x0, "x1": x1, "y0": inicio - (i + 1) * hu, "y1": inicio - i * hu,
                             "z": base + (i + 1) * ch, "n": i + 1})
        z_desc = base + (n1 + 1) * ch
        descanso = {"x0": xl, "x1": xr, "y0": y_desc0, "y1": y_desc1, "z": z_desc}
        x0, x1 = franja(t2["lado"])
        for j in range(n2 - 1):
            peldanos.append({"x0": x0, "x1": x1, "y0": y_desc1 + j * hu, "y1": y_desc1 + (j + 1) * hu,
                             "z": z_desc + (j + 1) * ch, "n": n1 + 2 + j})
        llegada = y_desc1 + (n2 - 1) * hu
        out.append({
            "desde": piso["desde"], "hasta": piso["hasta"], "base": base,
            "peldanos": peldanos, "descanso": descanso,
            "inicio_y": inicio, "llegada_y": llegada,
            "altura_total": (n1 + n2 + 1) * ch, "contrahuellas": n1 + n2 + 1,
        })
    return out


def alto_bajo_escalera(casa, nivel_id, de, a):
    """Altura libre (desde el piso del nivel) bajo la escalera que sube desde ese nivel, para un
    muro de `de` a `a`. None si el muro no pasa por debajo de la escalera."""
    est = casa["estructura"]
    t = est["espesor_muro_int"] / 2
    ch = est["escalera"]["contrahuella"]
    x0, x1 = sorted([de[0], a[0]])
    y0, y1 = sorted([de[1], a[1]])
    if abs(y1 - y0) < 0.01:      # muro horizontal: grosor en y
        y0, y1 = y0 - t, y1 + t
    else:                        # muro vertical: grosor en x
        x0, x1 = x0 - t, x1 + t
    minimo = None
    for e in escalera(casa):
        if e["desde"] != nivel_id:
            continue
        for p in e["peldanos"] + [e["descanso"]]:
            if min(x1, p["x1"]) - max(x0, p["x0"]) > 0.01 and min(y1, p["y1"]) - max(y0, p["y0"]) > 0.01:
                bajo = p["z"] - (ch if "n" in p else 0) - GARGANTA - e["base"]
                minimo = bajo if minimo is None else min(minimo, bajo)
    return minimo


def tramos_bajo_escalera(casa, nivel_id, de, a):
    """Divide un muro en partes según los peldaños que pasan encima.
    Devuelve [(de, a, alto | None)]; alto None = altura completa."""
    horizontal = abs(de[1] - a[1]) < 0.01
    k = 0 if horizontal else 1
    lo, hi = sorted([de[k], a[k]])
    cortes = {lo, hi}
    for e in escalera(casa):
        if e["desde"] != nivel_id:
            continue
        for p in e["peldanos"] + [e["descanso"]]:
            for v in ((p["x0"], p["x1"]) if horizontal else (p["y0"], p["y1"])):
                if lo < v < hi:
                    cortes.add(v)
    cortes = sorted(cortes)
    out = []
    for u, v in zip(cortes, cortes[1:]):
        if v - u < 0.01:
            continue
        p0 = [u, de[1]] if horizontal else [de[0], u]
        p1 = [v, de[1]] if horizontal else [de[0], v]
        alto = alto_bajo_escalera(casa, nivel_id, p0, p1)
        if out and out[-1][2] == alto:          # une partes contiguas de igual altura
            out[-1] = (out[-1][0], p1, alto)
        else:
            out.append((p0, p1, alto))
    return out


# Altura (m) y color 3D por tipo de mueble
MUEBLES = {
    "sofa": (0.80, 0x90a4ae), "sillon": (0.80, 0x90a4ae), "mesa": (0.75, 0xbcaaa4), "silla": (0.45, 0x8d6e63),
    "taburete": (0.70, 0x8d6e63), "cama": (0.55, 0xeceff1), "escritorio": (0.75, 0xbcaaa4), "estante": (2.00, 0xd7ccc8),
    "closet": (2.10, 0xd7ccc8), "meson": (0.90, 0xe0e0e0), "refrigerador": (1.80, 0xf5f5f5), "cocina": (0.92, 0x424242),
    "lavaplatos": (0.91, 0xb0bec5), "inodoro": (0.40, 0xffffff), "lavamanos": (0.85, 0xffffff), "ducha": (0.05, 0xb3e5fc),
    "lavadora": (0.85, 0xffffff), "lavadero": (0.85, 0xcfd8dc), "alfombra": (0.01, 0xd8c3a5),
}


def muebles(casa, nivel_id):
    out = []
    for m in (casa.get("muebles") or {}).get(nivel_id) or []:
        alto, color = MUEBLES.get(m["tipo"], (0.75, 0xcccccc))
        out.append({**m, "alto": m.get("alto", alto), "color": color})
    return out
