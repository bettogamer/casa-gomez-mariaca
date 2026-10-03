"""Genera las plantas en SVG desde el modelo. Uso: python tools/render_svg.py"""
from html import escape

from casa import COLORES_TIPO, SALIDA, ambientes, area, caja, cargar, centroide, columnas, huella_casa

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


def dibujar_escalera(L, casa):
    esc = casa["estructura"]["escalera"]
    x0, y0, x1, y1 = esc["rect"]
    L.poly([[x0, y0], [x1, y0], [x1, y1], [x0, y1]], 'fill="#e8d3b9" stroke="#8a6a45" stroke-width="1"')
    # dos tramos de ancho_tramo, peldaños a lo largo de y; descanso junto al eje A
    t = esc["ancho_tramo"]
    n = esc["peldanos_por_piso"] // 2
    L.linea(x0, y0 + t, x1, y0 + t, 'stroke="#8a6a45" stroke-width="1"')
    L.texto((x0 + x1) / 2, y0 + t / 2 + 0.05, "descanso", 8, 'fill="#8a6a45"')
    for k in range(n + 1):
        y = y0 + t + k * esc["huella"]
        L.linea(x0, y, x0 + t, y, 'stroke="#8a6a45" stroke-width="0.7"')
        L.linea(x1 - t, y, x1, y, 'stroke="#8a6a45" stroke-width="0.7"')
    L.texto((x0 + x1) / 2, y1 - 0.25, "ESCALERA (construida)", 9, 'fill="#6b4f2f"')


def dibujar_columnas(L, casa):
    s = casa["estructura"]["seccion_columna"] / 2
    for c in columnas(casa):
        L.poly([[c["x"] - s, c["y"] - s], [c["x"] + s, c["y"] - s], [c["x"] + s, c["y"] + s], [c["x"] - s, c["y"] + s]],
               'fill="#c62828" stroke="#600" stroke-width="1"')


def dibujar_ambientes(L, ambs):
    for a in ambs:
        ext = a["tipo"] == "exterior"
        estilo = (f'fill="{COLORES_TIPO.get(a["tipo"], "#eee")}" stroke="#222" '
                  + ('stroke-width="1.5" stroke-dasharray="6 3"' if ext else 'stroke-width="5" stroke-linejoin="miter"'))
        if a.get("estado") == "propuesto":
            estilo += ' fill-opacity="0.85"'
        L.poly(a["poly"], estilo)


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
    hx0, hy0, hx1, hy1 = huella_casa(casa)
    pts = [p for a in ambs for p in a["poly"]] + [[hx0, hy0], [hx1, hy1]]
    x0, y0 = min(p[0] for p in pts), min(p[1] for p in pts)
    x1, y1 = max(p[0] for p in pts), max(p[1] for p in pts)
    L = Lienzo(x0, y0, x1, y1)
    # contorno de la losa
    L.poly([[hx0, hy0], [hx1, hy0], [hx1, hy1], [hx0, hy1]], 'fill="#fafafa" stroke="#bbb" stroke-width="1"')
    dibujar_ambientes(L, ambs)
    dibujar_escalera(L, casa)
    dibujar_ejes(L, casa, x0, y0, x1, y1)
    dibujar_columnas(L, casa)
    rotular_ambientes(L, ambs)
    if not ambs:
        L.texto((hx0 + hx1) / 2, (hy0 + hy1) / 2, "Planta pendiente — falta foto/plano de este nivel", 14, 'fill="#999"')
    leyenda(L, x0 - 1.5, y1 + 1.6, f"{nivel['nombre'].upper()}  (NPT +{nivel['cota']:.2f})",
            "≈ medida aproximada (digitalizada de foto) · rojo: columnas construidas · azul: propuesto")
    return L.svg(nivel["nombre"])


def emplazamiento(casa):
    lt = casa["lote"]
    lx0, ly0 = lt["origen_x"], lt["origen_y"]
    lx1, ly1 = lx0 + lt["largo"], ly0 + lt["ancho"]
    L = Lienzo(lx0, ly0, lx1, ly1)
    L.poly([[lx0, ly0], [lx1, ly0], [lx1, ly1], [lx0, ly1]], 'fill="#f3f7ee" stroke="#333" stroke-width="2" stroke-dasharray="12 4 2 4"')
    dibujar_ambientes(L, ambientes(casa, "pb"))
    dibujar_escalera(L, casa)
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
