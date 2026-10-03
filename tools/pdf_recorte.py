"""Recorta vistas del PDF del arquitecto a PNG de alta resolución.

Uso:
  python tools/pdf_recorte.py                 # todas las vistas
  python tools/pdf_recorte.py fundaciones     # una vista
  python tools/pdf_recorte.py --dpi 300 planta_1

Sirve para que los agentes "lean" una vista con detalle sin cargar la lámina entera.
Las coordenadas son puntos PDF de la lámina única (3117 x 1275).
"""
import argparse

import fitz

from casa import RAIZ

PDF = RAIZ / "planos-arqui" / "PLANO DE const. 06-03.pdf"
DESTINO = RAIZ / "fuentes" / "pdf-vistas"

VISTAS = {
    "lamina_completa": (0, 0, 3117, 1275),
    "elevacion_lateral": (150, 60, 760, 520),
    "elevacion_frontal": (760, 60, 1150, 520),
    "elevacion_posterior": (1150, 60, 1560, 520),
    "corte_a": (1560, 150, 1830, 500),
    "corte_b": (1830, 150, 2440, 500),
    "planta_baja": (150, 510, 1220, 830),
    "fundaciones": (1220, 500, 1960, 860),
    "perspectiva": (1960, 500, 2380, 820),
    "planta_1": (130, 830, 730, 1090),
    "planta_altillo": (700, 830, 1300, 1100),
    "planta_cubierta": (1300, 860, 1900, 1100),
    "caratula": (2420, 260, 3000, 1100),
}


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("vistas", nargs="*", help=f"una o más de: {', '.join(VISTAS)}")
    ap.add_argument("--dpi", type=int, default=200)
    args = ap.parse_args()
    DESTINO.mkdir(parents=True, exist_ok=True)
    pagina = fitz.open(PDF)[0]
    for nombre in args.vistas or VISTAS:
        dpi = 60 if nombre == "lamina_completa" and not args.vistas else args.dpi
        f = DESTINO / f"{nombre}.png"
        pagina.get_pixmap(dpi=dpi, clip=fitz.Rect(*VISTAS[nombre])).save(f)
        print("→", f.relative_to(RAIZ))


if __name__ == "__main__":
    main()
