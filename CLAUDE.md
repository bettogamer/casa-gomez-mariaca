# Casa — proyecto de arquitectura

Rediseño de una vivienda unifamiliar **en construcción** en Cochabamba. Ya están hechas
las columnas, las losas y la escalera; el resto (muros, distribución, acabados) se puede
modificar. El dueño no es arquitecto: trabaja con fotos y lenguaje simple. Todo en español.

## Fuente de verdad
- `modelo/casa.yaml` es el modelo de la casa. Todo cambio de diseño se hace AHÍ.
- `salida/` se genera con `make build` (plantas SVG, visor 3D, DXF, tablero). Nunca se
  edita a mano y no se versiona.
- `planos-arqui/` son los originales del arquitecto. Solo lectura.
- Hay DOS versiones del proyecto (PDF de 2020 vs juego impreso fotografiado).
  El modelo parte de las fotos. Ver `docs/versiones-del-plano.md`.

## Reglas
1. **La estructura construida no se toca.** La sección `estructura` del modelo solo cambia
   cuando el usuario confirma una medida tomada en obra. Cualquier propuesta que la afecte
   se marca y se manda al `revisor-estructural`.
2. **No inventar medidas.** Lo leído de foto va con `estado: aproximado`; lo propuesto con
   `estado: propuesto`. Si algo no se ve, se pregunta o se agrega a `verificar_en_obra`.
3. Después de cada cambio: `make build` y 0 errores. Mostrar al usuario qué cambió.
4. Cada decisión aceptada o descartada se anota en `docs/decisiones.md`.
5. No dar por buena normativa ni cálculo estructural: el arquitecto/ingeniero confirma.

## Flujo con fotos
1. El usuario deja fotos en `entrada/` (o las pega en el chat).
2. `make fotos` → JPEG reducido en `fuentes/fotos/` (los originales quedan en `originales/`).
3. Agente `lector-planos` digitaliza al modelo.
4. `make build` y comparar el SVG con la foto.

## Agentes (`.claude/agents/`)
- `lector-planos` — foto/PDF → modelo.
- `disenador` — propone y aplica cambios de distribución.
- `revisor-estructural` — contrasta cambios con lo construido (solo lectura).
- `revisor-habitabilidad` — luz, ventilación, circulación, normativa (solo lectura).

Flujo típico de un cambio: `disenador` → `revisor-estructural` + `revisor-habitabilidad`
→ el usuario decide → se registra en `docs/decisiones.md`.

## Comandos
`make setup` · `make build` · `make check` · `make fotos` · `make pdf` · `make abrir` · `make 3d`

## Git
- Identidad local: `Betto <betto.gamer@icloud.com>`. Nunca `git push`.
- Se trabaja en `dev`; cambios en ramas `feat/<tema>` → `dev`. Nunca commitear en `main`.
- Sin trailers de atribución de IA en los commits.
