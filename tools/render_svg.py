"""Genera las plantas en SVG desde el modelo. Uso: python tools/render_svg.py"""
import math
from html import escape

from casa import (COLORES_TIPO, SALIDA, aberturas, ambientes, area, caja, cargar, centroide, columnas, dentro, escalera,
                  huella_casa, muros, referencia)

ESC = 50  # px por metro
MARGEN = 2.2  # m alrededor del dibujo (ejes, cotas)


class Lienzo:
    def __init__(self, x0, y0, x1, y1):
        self.x0, self.y0 = x0 - MARGEN, y0 - MARGEN
        self.w = (x1 - x0 + 2 * MARGEN) * ESC
        self.h = (y1 - y0 + 2 * MARGEN + 0.8) * ESC
        self.partes = []

    def p(self, x, y):
        return (x - self.x0) * ESC, (y - self.y0) * ESC

    def add(self, s):
        self.partes.append(s)

    def linea(self, x0, y0, x1, y1, estilo):
        a, b = self.p(x0, y0)
        c, d = self.p(x1, y1)
        self.add(f'<line x1="{a:.1f}" y1="{b:.1f}" x2="{c:.1f}" y2="{d:.1f}" {estilo}/>')

    def poly(self, pts, estilo):
        s = " ".join("%.1f,%.1f" % self.p(x, y) for x, y in pts)
        self.add(f'<polygon points="{s}" {estilo}/>')

    def texto(self, x, y, t, tam=11, estilo=""):
        a, b = self.p(x, y)
        self.add(f'<text x="{a:.1f}" y="{b:.1f}" font-size="{tam}" text-anchor="middle" {estilo}>{escape(str(t))}</text>')

    def svg(self, titulo):
        cab = (
            f'<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 {self.w:.0f} {self.h:.0f}" '
            f'font-family="Helvetica, Arial, sans-serif">\n<title>{escape(titulo)}</title>\n'
            f'<rect width="100%" height="100%" fill="#fff"/>\n'
        )
        return cab + "\n".join(self.partes) + "\n</svg>\n"


def dibujar_ejes(L, casa, x0, y0, x1, y1):
    est = casa["estructura"]
    roja = 'stroke="#d33" stroke-width="1" stroke-dasharray="8 4 2 4"'
    for nombre, x in est["ejes_x"].items():
        L.linea(x, y0 - 1.3, x, y1 + 0.6, roja)
        bx, by = L.p(x, y0 - 1.6)
        L.add(f'<circle cx="{bx:.1f}" cy="{by:.1f}" r="13" fill="#fff" stroke="#333"/>')
        L.texto(x, y0 - 1.6 + 0.11, nombre, 13, 'font-weight="bold"')
    for nombre, y in est["ejes_y"].items():
        L.linea(x0 - 1.3, y, x1 + 0.6, y, roja)
        bx, by = L.p(x0 - 1.6, y)
        L.add(f'<circle cx="{bx:.1f}" cy="{by:.1f}" r="13" fill="#fff" stroke="#333"/>')
        L.texto(x0 - 1.6, y + 0.11, nombre, 13, 'font-weight="bold"')
    # Cadena de cotas entre ejes
    xs = sorted(est["ejes_x"].values())
    yc = y0 - 0.85
    cota = 'stroke="#555" stroke-width="0.8"'
    L.linea(xs[0], yc, xs[-1], yc, cota)
    for x in xs:
        L.linea(x - 0.08, yc + 0.08, x + 0.08, yc - 0.08, 'stroke="#555" stroke-width="1.5"')
    for a, b in zip(xs, xs[1:]):
        L.texto((a + b) / 2, yc - 0.1, f"{b - a:.2f}", 10, 'fill="#555"')
    L.texto((xs[0] + xs[-1]) / 2, yc - 0.45, f"{xs[-1] - xs[0]:.2f} entre ejes extremos", 9, 'fill="#999"')


def dibujar_escalera(L, casa, nivel_id):
    """Dibuja la escalera que sube desde este nivel (sólida, numerada) y la que llega desde
    el nivel de abajo (solo contorno punteado: es el hueco en la losa)."""
    linea = 'stroke="#8a6a45" stroke-width="0.8"'
    for e in escalera(casa):
        if e["hasta"] == nivel_id:
            for p in e["peldanos"][-4:]:
                L.poly([[p["x0"], p["y0"]], [p["x1"], p["y0"]], [p["x1"], p["y1"]], [p["x0"], p["y1"]]],
                       'fill="none" stroke="#8a6a45" stroke-width="0.8" stroke-dasharray="3 3"')
        if e["desde"] != nivel_id:
            continue
        d = e["descanso"]
        L.poly([[d["x0"], d["y0"]], [d["x1"], d["y0"]], [d["x1"], d["y1"]], [d["x0"], d["y1"]]],
               f'fill="#d9bf9c" {linea}')
        L.texto((d["x0"] + d["x1"]) / 2, (d["y0"] + d["y1"]) / 2 + 0.05, f"descanso +{d['z']:.2f}", 8, 'fill="#6b4f2f"')
        for p in e["peldanos"]:
            L.poly([[p["x0"], p["y0"]], [p["x1"], p["y0"]], [p["x1"], p["y1"]], [p["x0"], p["y1"]]],
                   f'fill="#e8d3b9" {linea}')
            L.texto((p["x0"] + p["x1"]) / 2, (p["y0"] + p["y1"]) / 2 + 0.06, p["n"], 7, 'fill="#6b4f2f"')
        primero = e["peldanos"][0]
        cx = (primero["x0"] + primero["x1"]) / 2
        L.texto(cx, e["inicio_y"] + 0.3, "▲ SUBE", 9, 'font-weight="bold" fill="#6b4f2f"')
        L.texto(cx, e["inicio_y"] + 0.6, f"{e['contrahuellas']} × {casa['estructura']['escalera']['contrahuella'] * 100:.1f} cm", 8, 'fill="#6b4f2f"')


def dibujar_columnas(L, casa):
    s = casa["estructura"]["seccion_columna"] / 2
    for c in columnas(casa):
        L.poly([[c["x"] - s, c["y"] - s], [c["x"] + s, c["y"] - s], [c["x"] + s, c["y"] + s], [c["x"] - s, c["y"] + s]],
               'fill="#c62828" stroke="#600" stroke-width="1"')


def dibujar_ambientes(L, ambs):
    """Solo el relleno; los muros se dibujan aparte según su tipo."""
    for a in ambs:
        ext = a["tipo"] == "exterior"
        estilo = f'fill="{COLORES_TIPO.get(a["tipo"], "#eee")}" ' + ('stroke="#555" stroke-width="1.2" stroke-dasharray="6 3"' if ext else 'stroke="none"')
        if a.get("estado") == "propuesto":
            estilo += ' fill-opacity="0.85"'
        L.poly(a["poly"], estilo)


def dibujar_referencia(L, refs, nuevos):
    """Ambientes del plano de referencia en gris punteado (debajo del diseño nuevo)."""
    for a in refs:
        L.poly(a["poly"], 'fill="none" stroke="#b5b5b5" stroke-width="1" stroke-dasharray="4 3"')
    for a in refs:
        cx, cy = centroide(a["poly"])
        if any(dentro(n["poly"], cx, cy) for n in nuevos):
            continue
        L.texto(cx, cy, a["nombre"].lower(), 9, 'fill="#aaa" font-style="italic"')


def dibujar_muros(L, casa, nivel_id):
    est = casa["estructura"]
    xs, ys = est["ejes_x"].values(), est["ejes_y"].values()
    borde_x, borde_y = (min(xs), max(xs)), (min(ys), max(ys))
    for m in muros(casa, nivel_id):
        (x0, y0), (x1, y1) = m["de"], m["a"]
        if m["tipo"] == "ladrillo":
            perimetral = (abs(x0 - x1) < 0.01 and any(abs(x0 - b) < 0.01 for b in borde_x)) or \
                         (abs(y0 - y1) < 0.01 and any(abs(y0 - b) < 0.01 for b in borde_y))
            ancho = est["espesor_muro_ext" if perimetral else "espesor_muro_int"] * ESC
            L.linea(x0, y0, x1, y1, f'stroke="#222" stroke-width="{ancho:.1f}" stroke-linecap="square"')
        elif m["tipo"] == "celosia_madera":
            L.linea(x0, y0, x1, y1, 'stroke="#c49a6c" stroke-width="5"')
            dx, dy = x1 - x0, y1 - y0
            largo = (dx * dx + dy * dy) ** 0.5
            nx, ny = -dy / largo * 0.07, dx / largo * 0.07
            n = int(largo / 0.12)
            for k in range(n + 1):
                px, py = x0 + dx * k / n, y0 + dy * k / n
                L.linea(px - nx, py - ny, px + nx, py + ny, 'stroke="#7a5230" stroke-width="1.5"')
            L.texto((x0 + x1) / 2 + nx * 4, (y0 + y1) / 2 + ny * 4 + 0.05, "celosía de madera", 8, 'fill="#7a5230" font-style="italic"')
        else:
            L.linea(x0, y0, x1, y1, 'stroke="#555" stroke-width="3"')


def dibujar_aberturas(L, casa, nivel_id):
    ambs = {a["id"]: a for a in ambientes(casa, nivel_id)}
    for ab in aberturas(casa, nivel_id):
        (x0, y0), (x1, y1) = ab["de"], ab["a"]
        dx, dy = x1 - x0, y1 - y0
        largo = (dx * dx + dy * dy) ** 0.5
        if ab["tipo"] == "vano":
            L.linea(x0, y0, x1, y1, 'stroke="#999" stroke-width="1" stroke-dasharray="2 4"')
        elif ab["tipo"] == "ventana":
            L.linea(x0, y0, x1, y1, 'stroke="#222" stroke-width="7"')
            L.linea(x0, y0, x1, y1, 'stroke="#bfe3f5" stroke-width="4"')
        elif ab["tipo"] == "puerta":
            # hoja perpendicular hacia el ambiente al que abre + arco de giro
            nx, ny = -dy / largo, dx / largo
            destino = ambs.get(ab.get("abre_hacia"))
            if destino:
                cx, cy = centroide(destino["poly"])
                if (cx - x0) * nx + (cy - y0) * ny < 0:
                    nx, ny = -nx, -ny
            hx, hy = x0 + nx * largo, y0 + ny * largo
            L.linea(x0, y0, hx, hy, 'stroke="#222" stroke-width="2"')
            pts = []
            for k in range(13):
                t = k / 12 * 3.14159265 / 2
                ux, uy = dx / largo, dy / largo
                pts.append(L.p(x0 + largo * (nx * math.cos(t) + ux * math.sin(t)),
                               y0 + largo * (ny * math.cos(t) + uy * math.sin(t))))
            L.add('<polyline points="%s" fill="none" stroke="#555" stroke-width="1" stroke-dasharray="3 2"/>'
                  % " ".join("%.1f,%.1f" % p for p in pts))
            L.texto((x0 + x1) / 2 - nx * 0.35, (y0 + y1) / 2 - ny * 0.35 + 0.05, f"{largo:.2f}", 8, 'fill="#444"')


def rotular_ambientes(L, ambs):
    for a in ambs:
        cx, cy = centroide(a["poly"])
        x0, y0, x1, y1 = caja(a["poly"])
        aprox = "≈ " if a.get("estado") == "aproximado" else ""
        prop = 'fill="#1565c0"' if a.get("estado") == "propuesto" else 'fill="#222"'
        L.texto(cx, cy - 0.12, a["nombre"].upper(), 10, f'font-weight="bold" {prop}')
        L.texto(cx, cy + 0.18, f"{aprox}{x1 - x0:.2f} × {y1 - y0:.2f}", 9, 'fill="#444"')
        L.texto(cx, cy + 0.44, f"{area(a['poly']):.1f} m²", 9, 'fill="#666"')


def leyenda(L, x, y, titulo, subt):
    L.add(f'<text x="{L.p(x, y)[0]:.1f}" y="{L.p(x, y)[1]:.1f}" font-size="18" font-weight="bold">{escape(titulo)}</text>')
    L.add(f'<text x="{L.p(x, y + 0.4)[0]:.1f}" y="{L.p(x, y + 0.4)[1]:.1f}" font-size="10" fill="#666">{escape(subt)}</text>')
    # barra de escala de 5 m
    bx, by = L.p(x + 12, y)
    L.add(f'<rect x="{bx:.1f}" y="{by - 6:.1f}" width="{5 * ESC}" height="6" fill="none" stroke="#333"/>')
    L.add(f'<rect x="{bx:.1f}" y="{by - 6:.1f}" width="{ESC}" height="6" fill="#333"/>')
    L.add(f'<rect x="{bx + 2 * ESC:.1f}" y="{by - 6:.1f}" width="{ESC}" height="6" fill="#333"/>')
    L.add(f'<rect x="{bx + 4 * ESC:.1f}" y="{by - 6:.1f}" width="{ESC}" height="6" fill="#333"/>')
    L.add(f'<text x="{bx + 5 * ESC + 6:.1f}" y="{by:.1f}" font-size="10">5 m</text>')


def planta(casa, nivel):
    ambs = ambientes(casa, nivel["id"])
    refs = referencia(casa, nivel["id"])
    hx0, hy0, hx1, hy1 = huella_casa(casa)
    pts = [p for a in ambs + refs for p in a["poly"]] + [[hx0, hy0], [hx1, hy1]]
    x0, y0 = min(p[0] for p in pts), min(p[1] for p in pts)
    x1, y1 = max(p[0] for p in pts), max(p[1] for p in pts)
    L = Lienzo(x0, y0, x1, y1)
    # contorno de la losa
    L.poly([[hx0, hy0], [hx1, hy0], [hx1, hy1], [hx0, hy1]], 'fill="#fafafa" stroke="#bbb" stroke-width="1"')
    dibujar_referencia(L, refs, ambs)
    dibujar_ambientes(L, ambs)
    dibujar_escalera(L, casa, nivel["id"])
    dibujar_ejes(L, casa, x0, y0, x1, y1)
    dibujar_muros(L, casa, nivel["id"])
    dibujar_aberturas(L, casa, nivel["id"])
    dibujar_columnas(L, casa)
    rotular_ambientes(L, ambs)
    if not ambs and not refs:
        L.texto((hx0 + hx1) / 2, (hy0 + hy1) / 2, "Planta pendiente — falta foto/plano de este nivel", 14, 'fill="#999"')
    leyenda(L, x0 - 1.5, y1 + 1.6, f"{nivel['nombre'].upper()}  (NPT +{nivel['cota']:.2f})",
            "color = diseño nuevo · gris punteado = plano de referencia · rojo = columnas construidas · medidas a eje de muro")
    return L.svg(nivel["nombre"])


def emplazamiento(casa):
    lt = casa["lote"]
    lx0, ly0 = lt["origen_x"], lt["origen_y"]
    lx1, ly1 = lx0 + lt["largo"], ly0 + lt["ancho"]
    L = Lienzo(lx0, ly0, lx1, ly1)
    L.poly([[lx0, ly0], [lx1, ly0], [lx1, ly1], [lx0, ly1]], 'fill="#f3f7ee" stroke="#333" stroke-width="2" stroke-dasharray="12 4 2 4"')
    dibujar_referencia(L, referencia(casa, "pb"), ambientes(casa, "pb"))
    dibujar_ambientes(L, ambientes(casa, "pb"))
    dibujar_escalera(L, casa, "pb")
    dibujar_muros(L, casa, "pb")
    dibujar_aberturas(L, casa, "pb")
    dibujar_columnas(L, casa)
    rotular_ambientes(L, ambientes(casa, "pb"))
    col = lt["colindantes"]
    L.texto((lx0 + lx1) / 2, ly0 - 0.3, f"{col['arriba']} — {lt['largo']:.2f} m", 11)
    L.texto((lx0 + lx1) / 2, ly1 + 0.55, col["abajo"], 11)
    L.texto(lx0 - 0.4, (ly0 + ly1) / 2, col["frente"], 11, f'transform="rotate(-90 {L.p(lx0 - 0.4, (ly0 + ly1) / 2)[0]:.1f} {L.p(lx0 - 0.4, (ly0 + ly1) / 2)[1]:.1f})"')
    L.texto(lx1 + 0.6, (ly0 + ly1) / 2, col["fondo"], 11, f'transform="rotate(90 {L.p(lx1 + 0.6, (ly0 + ly1) / 2)[0]:.1f} {L.p(lx1 + 0.6, (ly0 + ly1) / 2)[1]:.1f})"')
    hx0, hy0, hx1, hy1 = huella_casa(casa)
    L.texto((hx1 + lx1) / 2, (ly0 + ly1) / 2, f"retiro {lx1 - hx1:.2f} m", 10, 'fill="#555"')
    L.texto((lx0 + hx0) / 2, (ly0 + ly1) / 2, f"patio delantero ≈ {hx0 - lx0 - 2.5:.1f} m + terraza", 10, 'fill="#555"')
    leyenda(L, lx0, ly1 + 1.6, "EMPLAZAMIENTO EN EL LOTE", f"Lote {lt['largo']} × {lt['ancho']} m")
    return L.svg("Emplazamiento")


def main():
    SALIDA.mkdir(exist_ok=True)
    casa = cargar()
    archivos = []
    for nivel in casa["niveles"]:
        f = SALIDA / f"planta-{nivel['id']}.svg"
        f.write_text(planta(casa, nivel), encoding="utf-8")
        archivos.append(f)
    f = SALIDA / "emplazamiento.svg"
    f.write_text(emplazamiento(casa), encoding="utf-8")
    archivos.append(f)
    for f in archivos:
        print("→", f.relative_to(SALIDA.parent))


if __name__ == "__main__":
    main()
