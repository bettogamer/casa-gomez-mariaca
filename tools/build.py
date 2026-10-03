"""Genera todo salida/ desde el modelo. Uso: python tools/build.py"""
import sys
from datetime import datetime
from html import escape

import checks
import export_dxf
import render_3d
import render_svg
from casa import SALIDA, ambientes, area, cargar


def tablero(casa, res, resumen):
    simb = {"error": ("✗", "#c62828"), "aviso": ("!", "#b26a00"), "info": ("·", "#555")}
    avisos = "".join(
        f'<li style="color:{simb[s][1]}"><b>{simb[s][0]}</b> <span class="niv">{escape(n)}</span> {escape(m)}</li>' for n, s, m in res
    )
    filas = ""
    for nivel in casa["niveles"]:
        for a in ambientes(casa, nivel["id"]):
            filas += (f"<tr><td>{escape(nivel['nombre'])}</td><td>{escape(a['nombre'])}</td><td>{a['tipo']}</td>"
                      f"<td class=n>{area(a['poly']):.1f}</td><td>{a.get('estado', '')}</td></tr>")
    tot = "".join(f"<li>{escape(n)}: <b>{u:.1f} m²</b> interiores + {e:.1f} m² exteriores</li>" for n, u, e in resumen["niveles"])
    plantas = "".join(
        f'<section><h2>{escape(n["nombre"])}</h2>{(SALIDA / ("planta-" + n["id"] + ".svg")).read_text(encoding="utf-8")}</section>'
        for n in casa["niveles"]
    )
    empl = (SALIDA / "emplazamiento.svg").read_text(encoding="utf-8")
    pend = "".join(f"<li>{escape(v)}</li>" for v in casa.get("verificar_en_obra", []))
    return f"""<!doctype html>
<html lang="es"><head><meta charset="utf-8"><meta name="viewport" content="width=device-width, initial-scale=1">
<title>Casa — Tablero</title>
<style>
 body {{ margin: 0; font: 14px/1.5 -apple-system, Helvetica, Arial, sans-serif; background: #f4f5f7; color: #222; }}
 main {{ max-width: 1300px; margin: 0 auto; padding: 16px; }}
 h1 {{ margin: 8px 0 4px; }} h2 {{ margin: 0 0 8px; font-size: 17px; }}
 section {{ background: #fff; border-radius: 10px; padding: 14px; margin: 14px 0; box-shadow: 0 1px 4px #0001; overflow-x: auto; }}
 svg {{ width: 100%; height: auto; min-width: 700px; }}
 .grid {{ display: grid; grid-template-columns: repeat(auto-fit, minmax(320px, 1fr)); gap: 14px; }}
 .grid section {{ margin: 0; }}
 ul {{ margin: 0; padding-left: 18px; }} .niv {{ color: #888; font-size: 12px; }}
 table {{ border-collapse: collapse; width: 100%; font-size: 13px; }} td, th {{ border-bottom: 1px solid #eee; padding: 3px 6px; text-align: left; }}
 td.n {{ text-align: right; }} a.btn {{ display: inline-block; background: #1565c0; color: #fff; padding: 8px 14px; border-radius: 8px; text-decoration: none; }}
</style></head><body><main>
<h1>Casa — Tablero del proyecto</h1>
<p style="color:#666">Generado {datetime.now():%Y-%m-%d %H:%M} desde <code>modelo/casa.yaml</code> · <a class="btn" href="visor-3d.html">Abrir visor 3D</a></p>
<div class="grid">
 <section><h2>Resumen</h2><ul><li>Lote: {resumen['lote']:.1f} m²</li><li>Huella de la casa: {resumen['huella']:.1f} m² (ocupa {resumen['fos'] * 100:.0f}% del lote)</li>{tot}</ul></section>
 <section><h2>Verificaciones</h2><ul>{avisos}</ul></section>
 <section><h2>Verificar en obra</h2><ul>{pend}</ul></section>
</div>
{plantas}
<section><h2>Emplazamiento</h2>{empl}</section>
<section><h2>Ambientes</h2><table><tr><th>Nivel</th><th>Ambiente</th><th>Tipo</th><th>m²</th><th>Estado</th></tr>{filas}</table></section>
</main></body></html>
"""


def main():
    casa = cargar()
    res = checks.verificar(casa)
    render_svg.main()
    render_3d.main()
    export_dxf.main()
    f = SALIDA / "index.html"
    f.write_text(tablero(casa, res, checks.resumen_areas(casa)), encoding="utf-8")
    print("→", f.relative_to(SALIDA.parent))
    errores = [m for _, s, m in res if s == "error"]
    print(f"\n{len(errores)} errores, {sum(1 for _, s, _ in res if s == 'aviso')} avisos")
    for m in errores:
        print("  ✗", m)
    return 1 if errores else 0


if __name__ == "__main__":
    sys.exit(main())
