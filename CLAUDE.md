# Casa — proyecto de arquitectura

Rediseño de una vivienda unifamiliar **en construcción** en Cochabamba. Ya están hechas
las columnas, las losas y la escalera; el resto (muros, distribución, acabados) se puede
modificar. El dueño no es arquitecto: trabaja con fotos y lenguaje simple. Todo en español.

**Al empezar una sesión, leer `docs/estado.md`** (qué está hecho y qué sigue).

## Fuente de verdad
- `modelo/casa.yaml` es el modelo de la casa. Todo cambio de diseño se hace AHÍ.
- Dentro del modelo: `ambientes` / `muros` / `aberturas` = **diseño nuevo**, que se define
  pieza por pieza con el usuario (desde 2026-10-03). `referencia` = el juego impreso, solo
  para consulta (se dibuja en gris). No copiar de `referencia` a `ambientes` sin que el
  usuario lo pida.
- Ritmo: un tema por vez, confirmar con el usuario antes de pasar al siguiente.
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
- `arquitecto` — ojo de arquitecto: composición de fachadas, orden de las plantas, zonas húmedas,
  detalles y encuentros (solo lectura).
- `interiorista` — muebles + luces, enchufes, interruptores y puntos de agua de cada ambiente
  (deja el amoblamiento definitivo para el electricista y el plomero). Solo toca `muebles`, `luces_extra` y `electrico.puntos`.

## Forma de trabajo (desde 2026-10-07)
La casa ya está completa: casi todo lo que llega son "¿y si...?" del dueño. Gastar agentes solo donde aportan.
Clasificar cada pedido en uno de tres tamaños:

1. **"¿Y si...?" (curiosidad o pregunta):** responde la sesión principal leyendo el modelo; a lo sumo un croquis
   rápido. **Sin agentes, sin tocar el modelo.** Si al dueño le gusta, pasa a 2 o 3.
2. **Cambio chico** (mover una puerta o ventana, una medida, una nota, un punto eléctrico o de agua): lo hace la
   sesión principal directo en el modelo, `make build`, y verifica ella misma lo básico (aberturas AL RAS de la columna
   si quedan a menos de 15 cm, ≥12.5 cm o pegadas junto a muros, choques con muebles, puntos, caños y hojas de puertas). **Sin agentes.** Solo
   `revisor-estructural` si toca columnas, vigas, losas o cimientos.
3. **Cambio grande** (redistribuir un ambiente o un piso, fachada, instalaciones), en dos fases:
   - **Fase A — borrador:** `disenador` hace 1–2 opciones SOLO con muros, puertas y ventanas (sin muebles, puntos ni
     notas largas), renderizadas a imagen para comparar. **Sin revisores.** El dueño elige.
   - **Fase B — detalle de la opción elegida:** UNA revisión, en paralelo y solo con el revisor que corresponde
     (`revisor-estructural` si toca estructura; `arquitecto` si toca fachada u orden de un piso;
     `revisor-habitabilidad` si cambian tamaños, luz o circulación), con preguntas concretas y respuesta ≤15 líneas.
     Los ajustes que pidió el revisor se aplican **sin volver a revisar**. `interiorista` entra **una sola vez al
     final**, con la distribución cerrada.

Reglas para ahorrar:
- Para ajustes, retomar al mismo agente (SendMessage) en vez de crear uno nuevo.
- Juntar cambios chicos y guardarlos juntos (una rama, un commit).
- Pedir a los agentes informes cortos; no repetir revisiones de lo que no cambió.
- Revisiones completas de la casa (`arquitecto` entero) solo cuando el dueño las pida.
- No hay agente ingeniero: cálculos y firmas los hace el ingeniero real; las preguntas se juntan en
  `docs/preguntas-ingeniero.md` y sus respuestas se pasan al modelo.
- Escribir al dueño en español simple, sin palabras en inglés.

## Instalaciones
`tools/instalaciones.py` genera los planos eléctrico y sanitario/gas desde ambientes, aberturas y
muebles; en `instalaciones` del modelo van tablero, calefón, troncales, cámaras, gas, seguridad y los
puntos eléctricos puestos a mano (`electrico.puntos`, reemplazan a los generados de su familia en su ambiente). Son
**esquemas preliminares** (NB 777, normas de agua y YPFB los define el profesional).

## Comandos
`make setup` · `make build` · `make check` · `make fotos` · `make pdf` · `make abrir` · `make 3d` · `make cuaderno` (PDF de obra) · `make sitio` / `make publicar` (página web de la obra en Vercel)

## Git
- Identidad local: `Betto <betto.gamer@icloud.com>`. Nunca `git push`.
- Se trabaja en `dev`; cambios en ramas `feat/<tema>` → `dev`. Nunca commitear en `main`.
- Sin trailers de atribución de IA en los commits.
