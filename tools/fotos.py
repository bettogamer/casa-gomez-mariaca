"""Procesa las fotos nuevas dejadas en `entrada/`.

Uso: python tools/fotos.py

Por cada foto (HEIC, JPG, PNG) en entrada/:
  - guarda el original en fuentes/fotos/originales/AAAA-MM-DD_nombre.ext
  - genera una copia JPEG de 1600 px (lado mayor) en fuentes/fotos/AAAA-MM-DD_nombre.jpg,
    que es la que leen los agentes (las fotos de 12 MP son demasiado pesadas)
Usa `sips` de macOS, que convierte HEIC sin dependencias extra.
"""
import shutil
import subprocess
from datetime import datetime

from casa import RAIZ

ENTRADA = RAIZ / "entrada"
FOTOS = RAIZ / "fuentes" / "fotos"
EXT = {".heic", ".jpg", ".jpeg", ".png"}


def main():
    (FOTOS / "originales").mkdir(parents=True, exist_ok=True)
    nuevas = sorted(p for p in ENTRADA.iterdir() if p.suffix.lower() in EXT)
    if not nuevas:
        print("No hay fotos en entrada/")
        return
    for p in nuevas:
        fecha = datetime.fromtimestamp(p.stat().st_mtime).strftime("%Y-%m-%d")
        base = f"{fecha}_{p.stem.replace(' ', '-')}"
        original = FOTOS / "originales" / f"{base}{p.suffix.lower()}"
        jpg = FOTOS / f"{base}.jpg"
        subprocess.run(["sips", "-s", "format", "jpeg", "-s", "formatOptions", "85", "-Z", "1600", str(p), "--out", str(jpg)],
                       check=True, capture_output=True)
        shutil.move(str(p), original)
        print(f"→ {jpg.relative_to(RAIZ)}")


if __name__ == "__main__":
    main()
