"""Exporta las plantas a salida/casa.dxf (abre en Vectorworks, AutoCAD, LibreCAD).

Cada nivel se dibuja desplazado hacia abajo. Unidades: metros. El eje y se
invierte (en CAD y crece hacia arriba).
"""
import ezdxf

from casa import SALIDA, ambientes, area, caja, cargar, centroide, columnas, escalera, huella_casa

CAPAS = {"EJES": 1, "COLUMNAS": 1, "AMBIENTES": 7, "EXTERIOR": 3, "ESCALERA": 30, "TEXTOS": 8, "LOSA": 9}


def main():
    casa = cargar()
    doc = ezdxf.new("R2010", setup=True)
    doc.units = ezdxf.units.M
    for nombre, color in CAPAS.items():
        doc.layers.add(nombre, color=color)
    msp = doc.modelspace()
    hx0, hy0, hx1, hy1 = huella_casa(casa)
    est = casa["estructura"]
    s = est["seccion_columna"] / 2
    paso = (hy1 - hy0) + 6

    for i, nivel in enumerate(casa["niveles"]):
        dy = -i * paso

        def P(x, y):
            return (x, -y + dy)

        msp.add_lwpolyline([P(hx0, hy0), P(hx1, hy0), P(hx1, hy1), P(hx0, hy1)], close=True, dxfattribs={"layer": "LOSA"})
        for nombre, x in est["ejes_x"].items():
            msp.add_line(P(x, hy0 - 1.5), P(x, hy1 + 0.5), dxfattribs={"layer": "EJES", "linetype": "DASHDOT"})
            msp.add_text(nombre, height=0.35, dxfattribs={"layer": "EJES"}).set_placement(P(x, hy0 - 1.8), align=ezdxf.enums.TextEntityAlignment.MIDDLE_CENTER)
        for nombre, y in est["ejes_y"].items():
            msp.add_line(P(hx0 - 1.5, y), P(hx1 + 0.5, y), dxfattribs={"layer": "EJES", "linetype": "DASHDOT"})
            msp.add_text(nombre, height=0.35, dxfattribs={"layer": "EJES"}).set_placement(P(hx0 - 1.8, y), align=ezdxf.enums.TextEntityAlignment.MIDDLE_CENTER)
        for c in columnas(casa):
            msp.add_lwpolyline([P(c["x"] - s, c["y"] - s), P(c["x"] + s, c["y"] - s), P(c["x"] + s, c["y"] + s), P(c["x"] - s, c["y"] + s)],
                               close=True, dxfattribs={"layer": "COLUMNAS"})
        for e in escalera(casa):
            if e["desde"] != nivel["id"]:
                continue
            for b in e["peldanos"] + [e["descanso"]]:
                msp.add_lwpolyline([P(b["x0"], b["y0"]), P(b["x1"], b["y0"]), P(b["x1"], b["y1"]), P(b["x0"], b["y1"])],
                                   close=True, dxfattribs={"layer": "ESCALERA"})
        for a in ambientes(casa, nivel["id"]):
            capa = "EXTERIOR" if a["tipo"] == "exterior" else "AMBIENTES"
            msp.add_lwpolyline([P(x, y) for x, y in a["poly"]], close=True, dxfattribs={"layer": capa})
            cx, cy = centroide(a["poly"])
            x0, y0, x1, y1 = caja(a["poly"])
            for k, t in enumerate([a["nombre"].upper(), f"{x1 - x0:.2f} x {y1 - y0:.2f}", f"{area(a['poly']):.1f} m2"]):
                msp.add_text(t, height=0.18 if k == 0 else 0.14, dxfattribs={"layer": "TEXTOS"}).set_placement(
                    P(cx, cy + k * 0.3), align=ezdxf.enums.TextEntityAlignment.MIDDLE_CENTER)
        msp.add_text(f"{nivel['nombre'].upper()}  NPT +{nivel['cota']:.2f}", height=0.45, dxfattribs={"layer": "TEXTOS"}).set_placement(
            P(hx0, hy1 + 1.5))

    SALIDA.mkdir(exist_ok=True)
    f = SALIDA / "casa.dxf"
    doc.saveas(f)
    print("→", f.relative_to(SALIDA.parent))


if __name__ == "__main__":
    main()
