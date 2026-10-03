# Casa

Proyecto para revisar y modificar los planos de la casa en construcción.

## Cómo funciona
La casa vive en un archivo de texto, [`modelo/casa.yaml`](modelo/casa.yaml): columnas,
niveles y cada ambiente con sus medidas. Desde ahí se generan automáticamente:

| Archivo | Qué es |
|---|---|
| `salida/index.html` | **Tablero**: plantas, áreas, avisos y pendientes |
| `salida/visor-3d.html` | **Maqueta 3D** para girar. Botón "Obra actual" = lo construido |
| `salida/planta-*.svg` | Plantas por nivel con ejes, columnas y medidas |
| `salida/emplazamiento.svg` | La casa dentro del lote |
| `salida/casa.dxf` | Para el arquitecto (Vectorworks/AutoCAD) |

No necesitas editar el YAML: me mandas fotos o me dices "quiero agrandar el estudio" y
yo actualizo el modelo y regenero todo.

## Uso
```sh
make setup   # una sola vez
make abrir   # genera y abre el tablero
make 3d      # genera y abre la maqueta 3D
```

## Fotos
Deja las fotos (de los planos o de la obra con medidas) en `entrada/` o pégalas en el chat.
Consejos: foto de frente y perpendicular al papel, buena luz, una vista por foto, que se lean
las cotas.

## Carpetas
- `planos-arqui/` — originales del arquitecto (PDF y fotos). No se modifican.
- `modelo/` — el modelo de la casa.
- `fuentes/` — fotos procesadas y recortes del PDF.
- `docs/` — decisiones y comparación de versiones del plano.
- `tools/` — los scripts que generan todo.
