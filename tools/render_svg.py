"""Genera las plantas en SVG desde el modelo. Uso: python tools/render_svg.py"""
import math
from html import escape

from casa import (COLORES_TIPO, SALIDA, aberturas, ambientes, area, caja, cargar, centroide, columnas, dentro, escalera,
                  huella_casa, muebles, muros, referencia)

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
        ancla = "" if "text-anchor" in estilo else 'text-anchor="middle" '
        self.add(f'<text x="{a:.1f}" y="{b:.1f}" font-size="{tam}" {ancla}{estilo}>{escape(str(t))}</text>')

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


def dibujar_columnas(L, casa, nivel_id=None):
    """Columnas construidas en rojo. En un nivel que está por encima de donde terminan las columnas, solo se
    dibujan las que se propone prolongar (contorno naranja punteado)."""
    est = casa["estructura"]
    s = est["seccion_columna"] / 2
    prolongar = (est.get("prolongar_columnas") or {}).get(nivel_id)
    for c in columnas(casa):
        cuadro = [[c["x"] - s, c["y"] - s], [c["x"] + s, c["y"] - s], [c["x"] + s, c["y"] + s], [c["x"] - s, c["y"] + s]]
        if prolongar is None:
            L.poly(cuadro, 'fill="#c62828" stroke="#600" stroke-width="1"')
        elif c["id"] in prolongar:
            L.poly(cuadro, 'fill="#ffe0b2" stroke="#e65100" stroke-width="1.5" stroke-dasharray="3 2"')


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
        elif ab["tipo"] == "puerta_corrediza":
            # hoja que se esconde dentro del muro (línea punteada = bolsillo)
            hx, hy = ab.get("corre_hacia", [x1 + dx, y1 + dy])
            L.linea(x0, y0, x1, y1, 'stroke="#fff" stroke-width="4"')
            L.linea(x0, y0, x1, y1, 'stroke="#222" stroke-width="2"')
            L.linea(x1, y1, hx, hy, 'stroke="#fff" stroke-width="2" stroke-dasharray="3 2"')
            nx, ny = -dy / largo, dx / largo
            L.texto((x0 + x1) / 2 + nx * 0.25, (y0 + y1) / 2 + ny * 0.25 + 0.05, f"corr. {largo:.2f}", 7, 'fill="#444"')
        elif ab["tipo"] == "corrediza":
            # dos hojas de vidrio desplazadas
            nx, ny = -dy / largo * 0.04, dx / largo * 0.04
            L.linea(x0, y0, x1, y1, 'stroke="#fff" stroke-width="7"')
            L.linea(x0 + nx, y0 + ny, x0 + dx * 0.55 + nx, y0 + dy * 0.55 + ny, 'stroke="#222" stroke-width="2"')
            L.linea(x0 + dx * 0.45 - nx, y0 + dy * 0.45 - ny, x1 - nx, y1 - ny, 'stroke="#222" stroke-width="2"')
            hx0, hy0, hx1, hy1 = huella_casa(casa)
            ox, oy = nx / 0.04, ny / 0.04
            if ((hx0 + hx1) / 2 - x0) * ox + ((hy0 + hy1) / 2 - y0) * oy > 0:
                ox, oy = -ox, -oy
            L.texto((x0 + x1) / 2 + ox * 0.55, (y0 + y1) / 2 + oy * 0.55 + 0.05, f"corrediza {largo:.2f}", 8, 'fill="#2a6f97"')
        elif ab["tipo"] == "ventana":
            L.linea(x0, y0, x1, y1, 'stroke="#222" stroke-width="7"')
            L.linea(x0, y0, x1, y1, 'stroke="#bfe3f5" stroke-width="4"')
            nx, ny = -dy / largo, dx / largo
            hx0, hy0, hx1, hy1 = huella_casa(casa)
            cx, cy = (hx0 + hx1) / 2, (hy0 + hy1) / 2
            if (cx - x0) * nx + (cy - y0) * ny > 0:
                nx, ny = -nx, -ny
            L.texto((x0 + x1) / 2 + nx * 0.3, (y0 + y1) / 2 + ny * 0.3 + 0.05, f"V {largo:.2f}", 8, 'fill="#2a6f97"')
        elif ab["tipo"] == "puerta":
            # hoja perpendicular hacia el ambiente al que abre + arco de giro
            nx, ny = -dy / largo, dx / largo
            destino = ambs.get(ab.get("abre_hacia"))
            if destino:
                cx, cy = centroide(destino["poly"])
            else:  # "afuera": alejarse del centro de la casa
                hx0, hy0, hx1, hy1 = huella_casa(casa)
                cx, cy = 2 * x0 - (hx0 + hx1) / 2, 2 * y0 - (hy0 + hy1) / 2
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
            # medida dentro del giro de la hoja, lejos de los rótulos del ambiente vecino
            L.texto(x0 + (dx * 0.6 + nx * largo * 0.35), y0 + (dy * 0.6 + ny * largo * 0.35) + 0.05, f"{largo:.2f}", 7, 'fill="#444"')


def dibujar_muebles(L, casa, nivel_id):
    def rect(x0, y0, x1, y1, estilo):
        L.poly([[x0, y0], [x1, y0], [x1, y1], [x0, y1]], estilo)

    def elipse(cx, cy, rx, ry, estilo):
        a, b = L.p(cx, cy)
        L.add(f'<ellipse cx="{a:.1f}" cy="{b:.1f}" rx="{rx * ESC:.1f}" ry="{ry * ESC:.1f}" {estilo}/>')

    madera = 'stroke="#6d4c41" stroke-width="0.8"'
    gris = 'stroke="#616161" stroke-width="0.8"'
    for m in muebles(casa, nivel_id):
        x0, y0, x1, y1 = m["rect"]
        w, h = x1 - x0, y1 - y0
        cx, cy = (x0 + x1) / 2, (y0 + y1) / 2
        t = m["tipo"]
        if t == "alfombra":
            rect(x0, y0, x1, y1, 'fill="#efe3cf" stroke="#c8b393" stroke-width="0.6" stroke-dasharray="3 2"')
        elif t in ("sofa", "sillon"):
            rect(x0, y0, x1, y1, 'fill="#cfd8dc" stroke="#546e7a" stroke-width="0.8" rx="3"')
            k = 0.15
            rect(x0 + k, y0 + k, x1 - k, y1 - k, 'fill="#eceff1" stroke="#90a4ae" stroke-width="0.5"')
        elif t in ("mesa", "escritorio"):
            rect(x0, y0, x1, y1, f'fill="#fff" {madera}')
        elif t in ("silla", "taburete"):
            rect(x0, y0, x1, y1, f'fill="#d7ccc8" {madera}')
        elif t in ("estante", "closet"):
            rect(x0, y0, x1, y1, f'fill="#eeeeee" {gris}')
            if t == "closet":
                L.linea(x0, y0, x1, y1, 'stroke="#9e9e9e" stroke-width="0.6"')
                L.linea(x0, y1, x1, y0, 'stroke="#9e9e9e" stroke-width="0.6"')
            else:
                n = max(1, int(max(w, h) / 0.30))
                for k in range(1, n):
                    if w >= h:
                        L.linea(x0 + w * k / n, y0, x0 + w * k / n, y1, 'stroke="#bdbdbd" stroke-width="0.5"')
                    else:
                        L.linea(x0, y0 + h * k / n, x1, y0 + h * k / n, 'stroke="#bdbdbd" stroke-width="0.5"')
        elif t == "meson":
            rect(x0, y0, x1, y1, f'fill="#e0e0e0" {gris}')
        elif t == "cocina":
            rect(x0, y0, x1, y1, 'fill="#9e9e9e" stroke="#424242" stroke-width="0.8"')
            for fx in (0.28, 0.72):
                for fy in (0.28, 0.72):
                    elipse(x0 + w * fx, y0 + h * fy, min(w, h) * 0.15, min(w, h) * 0.15, 'fill="none" stroke="#212121" stroke-width="0.8"')
        elif t == "lavaplatos":
            rect(x0, y0, x1, y1, 'fill="#cfd8dc" stroke="#546e7a" stroke-width="0.8" rx="3"')
        elif t == "refrigerador":
            rect(x0, y0, x1, y1, 'fill="#fff" stroke="#424242" stroke-width="1"')
            L.texto(cx, cy + 0.06, "R", 9, 'fill="#424242" font-weight="bold"')
        elif t == "inodoro":
            # tanque contra el muro (extremo mayor del eje largo), taza ovalada
            if w >= h:
                rect(x1 - 0.18, y0, x1, y1, 'fill="#fff" stroke="#424242" stroke-width="0.8"')
                elipse(x0 + (w - 0.18) / 2, cy, (w - 0.18) / 2, h / 2 * 0.9, 'fill="#fff" stroke="#424242" stroke-width="0.8"')
            else:
                rect(x0, y1 - 0.18, x1, y1, 'fill="#fff" stroke="#424242" stroke-width="0.8"')
                elipse(cx, y0 + (h - 0.18) / 2, w / 2 * 0.9, (h - 0.18) / 2, 'fill="#fff" stroke="#424242" stroke-width="0.8"')
        elif t == "lavamanos":
            rect(x0, y0, x1, y1, 'fill="#fff" stroke="#424242" stroke-width="0.8"')
            elipse(cx, cy, w * 0.35, h * 0.35, 'fill="none" stroke="#424242" stroke-width="0.8"')
        elif t == "ducha":
            rect(x0, y0, x1, y1, 'fill="#e1f5fe" stroke="#0277bd" stroke-width="0.8"')
            L.linea(x0, y0, x1, y1, 'stroke="#4fc3f7" stroke-width="0.6"')
            L.linea(x0, y1, x1, y0, 'stroke="#4fc3f7" stroke-width="0.6"')
        elif t == "lavadora":
            rect(x0, y0, x1, y1, 'fill="#fff" stroke="#424242" stroke-width="0.8"')
            elipse(cx, cy, min(w, h) * 0.33, min(w, h) * 0.33, 'fill="none" stroke="#424242" stroke-width="0.8"')
        elif t == "lavadero":
            rect(x0, y0, x1, y1, 'fill="#eceff1" stroke="#424242" stroke-width="0.8"')
            rect(x0 + 0.07, y0 + 0.07, x1 - 0.07, y1 - 0.07, 'fill="#cfd8dc" stroke="#78909c" stroke-width="0.5"')
        elif t == "cama":
            rect(x0, y0, x1, y1, 'fill="#fff" stroke="#546e7a" stroke-width="0.8"')
        else:
            rect(x0, y0, x1, y1, f'fill="#f5f5f5" {gris}')
        if m.get("nombre") and t not in ("refrigerador",):
            L.texto(cx, cy + 0.05, m["nombre"], 6, 'fill="#555"')


def rotular_ambientes(L, ambs):
    def con_halo(x, y, t, tam, estilo):
        # primero un trazo blanco (halo) y encima el texto: legible sobre los muebles en cualquier visor
        negrita = 'font-weight="bold" ' if "bold" in estilo else ""
        L.texto(x, y, t, tam, negrita + 'fill="#fff" stroke="#fff" stroke-width="3" stroke-linejoin="round"')
        L.texto(x, y, t, tam, estilo)

    for a in ambs:
        cx, cy = a.get("etiqueta") or centroide(a["poly"])
        x0, y0, x1, y1 = caja(a["poly"])
        aprox = "≈ " if a.get("estado") == "aproximado" else ""
        prop = 'fill="#1565c0"' if a.get("estado") == "propuesto" else 'fill="#222"'
        con_halo(cx, cy - 0.12, a["nombre"].upper(), 10, f'font-weight="bold" {prop}')
        con_halo(cx, cy + 0.18, f"{aprox}{x1 - x0:.2f} × {y1 - y0:.2f}", 9, 'fill="#444"')
        con_halo(cx, cy + 0.44, f"{area(a['poly']):.1f} m²", 9, 'fill="#666"')


def flecha_norte(L, casa, x, y):
    ori = casa["lote"].get("orientacion")
    if not ori:
        return
    nx, ny = ori["norte_en_planta"]
    cx, cy = L.p(x, y)
    r = 0.55 * ESC
    tip = (cx + nx * r, cy + ny * r)
    izq = (cx - ny * r * 0.35 - nx * r * 0.5, cy + nx * r * 0.35 - ny * r * 0.5)
    der = (cx + ny * r * 0.35 - nx * r * 0.5, cy - nx * r * 0.35 - ny * r * 0.5)
    L.add(f'<circle cx="{cx:.1f}" cy="{cy:.1f}" r="{r:.1f}" fill="#fff" stroke="#333"/>')
    L.add('<polygon points="%.1f,%.1f %.1f,%.1f %.1f,%.1f" fill="#333"/>' % (tip + izq + der))
    L.add(f'<text x="{tip[0] + nx * 12:.1f}" y="{tip[1] + ny * 12 + 4:.1f}" font-size="12" font-weight="bold" text-anchor="middle">N</text>')
    L.add(f'<text x="{cx:.1f}" y="{cy + r + 14:.1f}" font-size="8" text-anchor="middle" fill="#666">frente: {ori["frente"]}</text>')


def dibujar_proyecciones(L, casa, nivel_id):
    """Lo que está por encima del plano de corte (aleros, tanque sobre el techo): contorno punteado."""
    for e in (casa.get("proyecciones") or {}).get(nivel_id) or []:
        x0, y0, x1, y1 = e["rect"]
        L.poly([[x0, y0], [x1, y0], [x1, y1], [x0, y1]], 'fill="none" stroke="#555" stroke-width="1.2" stroke-dasharray="8 4"')
        L.texto((x0 + x1) / 2, (y0 + y1) / 2 + 0.05, e["nombre"], 7, 'fill="#555" font-style="italic"')


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
    dibujar_muebles(L, casa, nivel["id"])
    dibujar_proyecciones(L, casa, nivel["id"])
    dibujar_ejes(L, casa, x0, y0, x1, y1)
    dibujar_muros(L, casa, nivel["id"])
    dibujar_aberturas(L, casa, nivel["id"])
    dibujar_columnas(L, casa, nivel["id"])
    rotular_ambientes(L, ambs)
    if not ambs and not refs:
        L.texto((hx0 + hx1) / 2, (hy0 + hy1) / 2, "Planta pendiente — falta foto/plano de este nivel", 14, 'fill="#999"')
    flecha_norte(L, casa, x1 + 1.2, y1 + 1.4)
    leyenda(L, x0 - 1.5, y1 + 1.6, f"{nivel['nombre'].upper()}  (NPT +{nivel['cota']:.2f})",
            "color = diseño nuevo · gris punteado = plano de referencia · rojo = columnas construidas · medidas a eje de muro")
    return L.svg(nivel["nombre"])


def _flecha(L, a, b, estilo, punta=0.18):
    """Línea de a hacia b con punta de flecha en b."""
    L.linea(a[0], a[1], b[0], b[1], estilo)
    dx, dy = b[0] - a[0], b[1] - a[1]
    n = math.hypot(dx, dy) or 1
    ux, uy = dx / n, dy / n
    p1 = (b[0] - ux * punta - uy * punta * 0.5, b[1] - uy * punta + ux * punta * 0.5)
    p2 = (b[0] - ux * punta + uy * punta * 0.5, b[1] - uy * punta - ux * punta * 0.5)
    color = estilo.split('stroke="')[1].split('"')[0]
    L.poly([b, p1, p2], f'fill="{color}"')


CAIDA = {"sur": (0, 1), "norte": (0, -1), "este": (1, 0), "oeste": (-1, 0)}


def planta_techos(casa):
    """Planta de techos: aguas de calamina, pendientes, canaletas, bajantes pluviales y sumideros."""
    t = casa.get("techos") or {}
    hx0, hy0, hx1, hy1 = huella_casa(casa)
    ambs = ambientes(casa, "altillo")
    pts = [p for a in ambs for p in a["poly"]] + [[hx0, hy0], [hx1, hy1]]
    x0, y0 = min(p[0] for p in pts), min(p[1] for p in pts)
    x1, y1 = max(p[0] for p in pts), max(p[1] for p in pts)
    L = Lienzo(x0, y0, x1, y1)
    # losa del altillo y ambientes debajo (referencia tenue)
    L.poly([[hx0, hy0], [hx1, hy0], [hx1, hy1], [hx0, hy1]], 'fill="#f1f3f4" stroke="#bbb" stroke-width="1"')
    for a in ambs:
        L.poly(a["poly"], 'fill="none" stroke="#ccc" stroke-width="1" stroke-dasharray="4 3"')
    AZUL = "#1565c0"
    for ag in t.get("aguas", []):
        poly = ag["poly"]
        L.poly(poly, 'fill="#cfd8dc" fill-opacity="0.85" stroke="#455a64" stroke-width="1.5"')
        ax0, ay0 = min(p[0] for p in poly), min(p[1] for p in poly)
        ax1, ay1 = max(p[0] for p in poly), max(p[1] for p in poly)
        dx, dy = CAIDA[ag["cae_hacia"]]
        # ondas de la calamina: corren en el sentido de la caída
        if dy:
            x = ax0 + 0.25
            while x < ax1:
                L.linea(x, ay0, x, ay1, 'stroke="#90a4ae" stroke-width="0.6"')
                x += 0.25
        else:
            y = ay0 + 0.25
            while y < ay1:
                L.linea(ax0, y, ax1, y, 'stroke="#90a4ae" stroke-width="0.6"')
                y += 0.25
        cx, cy = (ax0 + ax1) / 2, (ay0 + ay1) / 2
        largo = 1.6
        _flecha(L, (cx - dx * largo / 2, cy - dy * largo / 2), (cx + dx * largo / 2, cy + dy * largo / 2),
                'stroke="#b71c1c" stroke-width="2.5"', 0.3)
        ty = cy - 1.0
        L.add(f'<rect x="{L.p(cx + 0.25, ty - 0.32)[0]:.1f}" y="{L.p(cx + 0.25, ty - 0.32)[1]:.1f}" width="{2.2 * ESC:.0f}" height="{0.62 * ESC:.0f}" fill="#fff" fill-opacity="0.85"/>')
        L.texto(cx + 0.35, ty - 0.08, f"{ag['nombre']}", 9, 'font-weight="bold" text-anchor="start"')
        L.texto(cx + 0.35, ty + 0.20, f"cae {ag['pendiente'] * 100:.0f}% al {ag['cae_hacia']}", 8, 'fill="#b71c1c" text-anchor="start"')
        if "cota_alta" in ag:
            L.texto(cx, ay0 + 0.35, f"borde alto ≈ +{ag['cota_alta']:.2f}", 7, 'fill="#37474f"')
            L.texto(cx, ay1 - 0.15, f"borde bajo ≈ +{ag['cota_baja']:.2f}", 7, 'fill="#37474f"')
    for m in t.get("antepechos", []):
        L.linea(*m["de"], *m["a"], 'stroke="#424242" stroke-width="6"')
    for m in t.get("cenefas", []):
        L.linea(*m["de"], *m["a"], 'stroke="#6d4c41" stroke-width="4"')
    # losa descubierta: pendientes hacia los sumideros
    for pl in t.get("pendientes_losa", []):
        _flecha(L, pl["de"], pl["a"], f'stroke="{AZUL}" stroke-width="1" stroke-dasharray="5 3"', 0.18)
        L.texto((pl["de"][0] + pl["a"][0]) / 2, (pl["de"][1] + pl["a"][1]) / 2 - 0.1, pl.get("texto", ""), 7, f'fill="{AZUL}"')
    for c in t.get("canaletas", []):
        L.linea(*c["de"], *c["a"], f'stroke="{AZUL}" stroke-width="4"')
        mx, my = (c["de"][0] + c["a"][0]) / 2, (c["de"][1] + c["a"][1]) / 2
        sx = 1 if c["a"][0] > c["de"][0] else -1
        _flecha(L, (mx - sx * 0.4, my + 0.28), (mx + sx * 0.4, my + 0.28), f'stroke="{AZUL}" stroke-width="1.2"', 0.15)
        L.texto(mx, my + 0.55, f"canaleta {c.get('pendiente', 0.005) * 100:.1f}%", 7, f'fill="{AZUL}"')
    for linea in t.get("conexiones", []):
        for a, b in zip(linea, linea[1:]):
            L.linea(*a, *b, f'stroke="{AZUL}" stroke-width="2" stroke-dasharray="4 2"')
    for sm in t.get("sumideros", []):
        x, y = sm["pos"]
        L.poly([[x - 0.12, y - 0.12], [x + 0.12, y - 0.12], [x + 0.12, y + 0.12], [x - 0.12, y + 0.12]], f'fill="#fff" stroke="{AZUL}" stroke-width="1.2"')
        L.linea(x - 0.12, y - 0.12, x + 0.12, y + 0.12, f'stroke="{AZUL}"')
        L.linea(x - 0.12, y + 0.12, x + 0.12, y - 0.12, f'stroke="{AZUL}"')
    for bp in t.get("bajantes", []):
        x, y = bp["pos"]
        cx_, cy_ = L.p(x, y)
        L.add(f'<circle cx="{cx_:.1f}" cy="{cy_:.1f}" r="7" fill="{AZUL}"/>')
        L.texto(x, y + 0.48, f"{bp['id']} ↓", 8, f'fill="{AZUL}" font-weight="bold"')
    for po in t.get("postes", []):
        x, y = po["pos"]
        L.poly([[x - 0.08, y - 0.08], [x + 0.08, y - 0.08], [x + 0.08, y + 0.08], [x - 0.08, y + 0.08]], 'fill="#212121"')
    dibujar_proyecciones(L, casa, "altillo")
    dibujar_ejes(L, casa, x0, y0, x1, y1)
    dibujar_columnas(L, casa, "altillo")
    L.texto(10.60, 6.45, "franja 2 m descubierta (retiro)", 8, 'fill="#777" font-style="italic"')
    L.texto(1.60, 6.45, "terraza descubierta", 8, 'fill="#777" font-style="italic"')
    # leyenda de símbolos
    lx, ly = x1 - 5.2, y1 + 2.45
    L.linea(lx, ly, lx + 0.5, ly, f'stroke="{AZUL}" stroke-width="4"'); L.texto(lx + 0.6, ly + 0.05, "canaleta", 7, 'text-anchor="start"')
    cx_, cy_ = L.p(lx + 2.0, ly)
    L.add(f'<circle cx="{cx_:.1f}" cy="{cy_:.1f}" r="5" fill="{AZUL}"/>'); L.texto(lx + 2.2, ly + 0.05, "bajante pluvial", 7, 'text-anchor="start"')
    L.linea(lx + 4.0, ly, lx + 4.5, ly, 'stroke="#424242" stroke-width="6"'); L.texto(lx + 4.6, ly + 0.05, "antepecho", 7, 'text-anchor="start"')
    L.linea(lx, ly + 0.4, lx + 0.5, ly + 0.4, 'stroke="#6d4c41" stroke-width="4"'); L.texto(lx + 0.6, ly + 0.45, "cenefa", 7, 'text-anchor="start"')
    L.poly([[lx + 1.92, ly + 0.32], [lx + 2.08, ly + 0.32], [lx + 2.08, ly + 0.48], [lx + 1.92, ly + 0.48]], 'fill="#212121"'); L.texto(lx + 2.2, ly + 0.45, "poste metálico", 7, 'text-anchor="start"')
    leyenda(L, x0 - 1.5, y1 + 1.6, "PLANTA DE TECHOS (esquema)",
            "calamina a un agua · flecha roja = caída del techo · azul = agua de lluvia · cotas aproximadas, las define el ingeniero")
    return L.svg("Planta de techos")


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
    if casa.get("techos"):
        f = SALIDA / "planta-techos.svg"
        f.write_text(planta_techos(casa), encoding="utf-8")
        archivos.append(f)
    f = SALIDA / "emplazamiento.svg"
    f.write_text(emplazamiento(casa), encoding="utf-8")
    archivos.append(f)
    for f in archivos:
        print("→", f.relative_to(SALIDA.parent))


if __name__ == "__main__":
    main()
