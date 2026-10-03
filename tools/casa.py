"""Carga del modelo `modelo/casa.yaml` y geometría básica compartida por las herramientas."""
from pathlib import Path

import yaml

RAIZ = Path(__file__).resolve().parent.parent
MODELO = RAIZ / "modelo" / "casa.yaml"
SALIDA = RAIZ / "salida"

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
    for nivel in casa["niveles"]:
        for amb in casa["ambientes"].get(nivel["id"]) or []:
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
