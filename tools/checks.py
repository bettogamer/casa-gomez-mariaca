"""Verificaciones automáticas del modelo. Uso: python tools/checks.py

Los mínimos de tamaño son REFERENCIALES (práctica usual), no la normativa
municipal de Cochabamba: esa la confirma el arquitecto.
"""
import sys

from casa import GARGANTA, aberturas, ambientes, area, caja, cargar, columnas, dentro, dist_borde, escalera, huella_casa, muebles, muros

# (área mínima m², lado mínimo m) — referencial
MINIMOS = {
    "dormitorio": (9.0, 2.70),
    "bano": (2.5, 1.20),
    "cocina": (5.0, 1.80),
    "social": (9.0, 2.70),
}
PASO = 0.05  # resolución para detectar solapes (m)
ALTURA_PASO = 2.00


def solape(pa, pb):
    ax0, ay0, ax1, ay1 = caja(pa)
    bx0, by0, bx1, by1 = caja(pb)
    x0, y0, x1, y1 = max(ax0, bx0), max(ay0, by0), min(ax1, bx1), min(ay1, by1)
    if x1 <= x0 or y1 <= y0:
        return 0.0
    n = 0
    y = y0 + PASO / 2
    while y < y1:
        x = x0 + PASO / 2
        while x < x1:
            if dentro(pa, x, y) and dentro(pb, x, y):
                n += 1
            x += PASO
        y += PASO
    return n * PASO * PASO


def verificar(casa):
    """Devuelve lista de (nivel, severidad, mensaje). severidad: error | aviso | info"""
    res = []
    cols = columnas(casa)
    sec = casa["estructura"]["seccion_columna"]

    # Escalera — regla de Blondel: 2 contrahuellas + 1 huella ≈ 0.60–0.65 m
    esc = casa["estructura"]["escalera"]
    blondel = 2 * esc["contrahuella"] + esc["huella"]
    sev = "info" if 0.60 <= blondel <= 0.65 else "aviso"
    res.append(("estructura", sev, f"Escalera: 2×{esc['contrahuella']:.3f} + {esc['huella']:.2f} = {blondel:.3f} m (cómodo: 0.60–0.65)"))
    alturas = {n["id"]: n["altura"] for n in casa["niveles"]}
    for e in escalera(casa):
        dif = e["altura_total"] - alturas[e["desde"]]
        sev = "info" if abs(dif) <= 0.02 else "error"
        res.append(("estructura", sev, f"Escalera {e['desde']}→{e['hasta']}: {e['contrahuellas']} × {esc['contrahuella']:.3f} = {e['altura_total']:.3f} m (piso a piso {alturas[e['desde']]:.2f})"))
    # Altura de paso: de cada pisada de una escalera a la parte de abajo de la escalera de arriba
    tramos = escalera(casa)
    for baja, alta in zip(tramos, tramos[1:]):
        minimo, donde = None, None
        for p in baja["peldanos"] + [baja["descanso"]]:
            for q in alta["peldanos"] + [alta["descanso"]]:
                if min(p["x1"], q["x1"]) - max(p["x0"], q["x0"]) > 0.01 and min(p["y1"], q["y1"]) - max(p["y0"], q["y0"]) > 0.01:
                    libre = (q["z"] - esc["contrahuella"] - GARGANTA) - p["z"]
                    if minimo is None or libre < minimo:
                        minimo, donde = libre, p.get("n", "descanso")
        if minimo is not None:
            sev = "info" if minimo >= ALTURA_PASO else "aviso"
            res.append(("estructura", sev, f"Altura de paso bajo la escalera {alta['desde']}→{alta['hasta']}: mínimo {minimo:.2f} m (escalón {donde}; recomendable ≥ {ALTURA_PASO:.2f})"))
    if esc["contrahuella"] > 0.18:
        res.append(("estructura", "aviso", f"Contrahuella {esc['contrahuella']*100:.1f} cm > 18 cm: escalera algo empinada (ya construida, solo informativo)"))

    for nivel in casa["niveles"]:
        nid = nivel["id"]
        ambs = ambientes(casa, nid)
        if not ambs:
            res.append((nid, "aviso", "Sin ambientes cargados (pendiente)"))
            continue

        for i, a in enumerate(ambs):
            for b in ambs[i + 1:]:
                s = solape(a["poly"], b["poly"])
                if s > 0.05:
                    res.append((nid, "error", f"'{a['nombre']}' y '{b['nombre']}' se superponen {s:.2f} m²"))

        for c in cols:
            for a in ambs:
                if a["tipo"] == "exterior":
                    continue
                if dentro(a["poly"], c["x"], c["y"]) and dist_borde(a["poly"], c["x"], c["y"]) > sec:
                    res.append((nid, "aviso", f"Columna {c['id']} queda en medio de '{a['nombre']}' (no se puede quitar)"))

        for a in ambs:
            m = MINIMOS.get(a["tipo"])
            if not m:
                continue
            x0, y0, x1, y1 = caja(a["poly"])
            ar, lado = area(a["poly"]), min(x1 - x0, y1 - y0)
            if ar < m[0]:
                res.append((nid, "aviso", f"'{a['nombre']}' mide {ar:.1f} m² (< {m[0]} m² referencial)"))
            if lado < m[1]:
                res.append((nid, "aviso", f"'{a['nombre']}' tiene un lado de {lado:.2f} m (< {m[1]} m referencial)"))

        res += verificar_obra(casa, nid)

    return res


# Junto a una columna, un pedazo de ladrillo de menos de esto no sostiene el marco: la abertura va AL RAS de la
# columna (pedido del maestro, 2026-10-16). Entre esto y un ladrillo entero (0.25) se decide caso por caso.
RAS_COLUMNA = 0.15


def verificar_obra(casa, nid):
    """Aberturas a pocos cm de una columna y muebles metidos dentro de un muro (con el muro en su lugar real)."""
    res = []
    m = casa["estructura"]["seccion_columna"] / 2
    for ab in aberturas(casa, nid):
        if ab.get("en_cerco") or ab["tipo"] in ("porton", "vano"):
            continue
        (x0, y0), (x1, y1) = ab["de"], ab["a"]
        hor = abs(y0 - y1) < 0.01
        lo, hi = (min(x0, x1), max(x0, x1)) if hor else (min(y0, y1), max(y0, y1))
        for col in columnas(casa):
            cl, cv = (col["x"], col["y"]) if hor else (col["y"], col["x"])
            if abs(cv - (y0 if hor else x0)) > m:
                continue
            for gap in (lo - (cl + m), (cl - m) - hi):
                if 0.005 < gap < RAS_COLUMNA:
                    res.append((nid, "aviso", f"'{ab['id']}' queda a {gap * 100:.1f} cm de la columna {col['id']}: "
                                              "ponerla al ras de la columna (el marco no agarra en ese pedazo)"))
    paredes = []
    for mu in muros(casa, nid):
        if mu["tipo"] != "ladrillo":
            continue
        (x0, y0), (x1, y1) = mu["de"], mu["a"]
        g = mu["grosor"] / 2
        x0, x1, y0, y1 = x0 + mu["dx"], x1 + mu["dx"], y0 + mu["dy"], y1 + mu["dy"]
        if abs(x0 - x1) < 0.01:
            paredes.append((x0 - g, min(y0, y1), x0 + g, max(y0, y1)))
        else:
            paredes.append((min(x0, x1), y0 - g, max(x0, x1), y0 + g))
    for mb in muebles(casa, nid):
        a = mb.get("rect")
        if not a:
            continue
        for w in paredes:
            ox, oy = min(a[2], w[2]) - max(a[0], w[0]), min(a[3], w[3]) - max(a[1], w[1])
            if ox > 0.01 and oy > 0.01:
                res.append((nid, "aviso", f"Mueble '{mb.get('nombre', mb['tipo'])}' se mete {min(ox, oy) * 100:.0f} cm en un muro"))
                break
    return res


def resumen_areas(casa):
    hx0, hy0, hx1, hy1 = huella_casa(casa)
    huella = (hx1 - hx0) * (hy1 - hy0)
    lote = casa["lote"]["largo"] * casa["lote"]["ancho"]
    filas = []
    for nivel in casa["niveles"]:
        ambs = ambientes(casa, nivel["id"])
        util = sum(area(a["poly"]) for a in ambs if a["tipo"] != "exterior")
        ext = sum(area(a["poly"]) for a in ambs if a["tipo"] == "exterior")
        filas.append((nivel["nombre"], util, ext))
    return {"huella": huella, "lote": lote, "fos": huella / lote, "niveles": filas}


def main():
    casa = cargar()
    res = verificar(casa)
    simb = {"error": "✗", "aviso": "!", "info": "·"}
    for nivel, sev, msg in res:
        print(f"{simb[sev]} [{nivel}] {msg}")
    r = resumen_areas(casa)
    print(f"\nLote {r['lote']:.1f} m² · huella casa {r['huella']:.1f} m² · ocupación {r['fos']*100:.0f}%")
    for nombre, util, ext in r["niveles"]:
        print(f"  {nombre}: {util:.1f} m² interiores + {ext:.1f} m² exteriores")
    errores = sum(1 for _, s, _ in res if s == "error")
    print(f"\n{errores} errores, {sum(1 for _, s, _ in res if s == 'aviso')} avisos")
    return 1 if errores else 0


if __name__ == "__main__":
    sys.exit(main())
