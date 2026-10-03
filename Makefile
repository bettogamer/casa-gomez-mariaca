PY := .venv/bin/python

.PHONY: setup build check fotos pdf abrir 3d

setup:            ## crea el entorno Python
	python3 -m venv .venv && $(PY) -m pip install -q -r requirements.txt

build:            ## genera planos, visor 3D, DXF y tablero en salida/
	$(PY) tools/build.py

check:            ## solo verificaciones
	$(PY) tools/checks.py

fotos:            ## procesa fotos nuevas de entrada/
	$(PY) tools/fotos.py

pdf:              ## recorta las vistas del PDF del arquitecto
	$(PY) tools/pdf_recorte.py

abrir: build      ## genera y abre el tablero
	open salida/index.html

3d: build         ## genera y abre el visor 3D
	open salida/visor-3d.html
