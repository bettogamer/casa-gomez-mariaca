# Estado del proyecto — leer al empezar una sesión

_Última actualización: 2026-10-16_

## Hecho
- **Estructura construida modelada y cerrada:** 15 columnas 25×25 (ejes 4.40 · 2.65 · 4.15 · 5.70 /
  2.68 · 3.99, según `planos-arqui/IMG_8278.png`), 2 losas (+3.40 y +6.60; el altillo aún sin
  techo), alturas de 3.00 m libres (3.20 piso a piso), escalera en U rehecha en obra
  (PB→P1: 10 + descanso + 6; P1→altillo: 6 + descanso + 10; 17 × 18.8 cm, huella 28 cm).
- **Planta baja aprobada (v4) y amoblada:** terraza, acceso, ingreso con celosía, living,
  depósito bajo la grada (puerta al retiro), hall, baño (1.65 libres), estudio/invitados,
  comedor para 6, pasillo, lavado, almacén, cocina amplia en **L + isla**.
- **Orientación** (deducida, falta confirmar): frente oeste, retiro lateral (Lote 105) norte,
  vecino (Lote 103) sur, patio este. Muebles acomodados por el sol.
- **Planta baja cerrada (salvo terminaciones):** ductos de aire (campana → patio en cajón; extractor del
  lavado → retiro, con cielo falso ~2.70 en lavado, baño y arranque del pasillo; secadora de condensación
  sin ducto); paso al patio por la corrediza del comedor; puerta de entrada pivotante de 1.05 con vidrio fijo al lado (2026-10-05, propuesto); cajonera bajo la
  grada; pasillo de 0.90 aceptado. Ver `docs/revision-pb.md`.
- **Instalaciones PB (esquema preliminar):** eléctrico con 7 circuitos y cuadro de cargas;
  agua (SEMAPA → cisterna enterrada existente + bomba → tanque elevado → gravedad), **calefón a gas natural de toda la casa
  en la terraza del altillo, junto a la columna A2** (2026-10-05; gas sube a la vista por la fachada norte; agua
  caliente baja por fuera del muro norte junto a A2; sin termotanques en la suite ni en el altillo; tanque a +10.50), desagüe por el retiro norte con CI y desgrasadora, gas natural por el retiro
  norte. Horno eléctrico; sin secadora.

- **Primer piso aprobado (completo):** suite principal al frente (dormitorio con TV en el muro oeste, logia
  sobre el volado de 1 m, lavamanos abierto, inodoro y ducha propios, vestidor en U); hall en la llegada de la
  escalera; blancos al norte y estar al sur (sala de TV de 9.9 m², sin ventana, abierta al hall y al pasillo de 1.05);
  dos cuartos de 18 m² con baño privado pegado al eje 4, ropero empotrado y escritorio junto al ropero (Cuarto 1 con
  tocador y banco ventana). Ver `docs/revision-p1.md` y la entrada del 2026-10-04 en `docs/decisiones.md`.

- **Instalaciones P1 (esquema preliminar):** eléctrico con subtablero en el hall junto a la columna B2 y 4 circuitos (C8–C11), agua
  desde el núcleo técnico, 3 bajantes, extractores del Baño 2 y de los lavamanos de la suite; agua caliente de la suite desde el calefón de PB (sin termotanque, 2026-10-05). Sin gas.

- **Altillo reordenado (2026-10-06, opción B):** baño apilado sobre el Baño 1 del P1 (nada húmedo sobre dormitorios);
  cocina en U y comedor junto a la escalera, estar al este, dormitorio de 15.4 m². Ver `docs/decisiones.md`.
- **Altillo aprobado (versión anterior, reemplazada en la distribución interior):** departamento temporal (estar-comedor-cocina, baño, dormitorio de 18 m²) con la escalera
  adentro, terraza adelante, franja de 2 m al sur con lavandería; techo de calamina oculto; tanque sobre la
  columna A3. Instalaciones (esquema): C13–C16, anafe eléctrico; agua caliente del calefón de la terraza; presurizadora solo si el calefón no enciende.

- **Normativa y techos (2026-10-04):** OM 4100/10 revisada (`docs/normativa.md`); planta de techos (`salida/planta-techos.svg`):
  calamina, departamento oculto tras antepecho, terraza con techo sobre fierro; muro ciego sur de ~1.80 y semisombra
  sobre la lavandería. Montante eléctrico en la columna B2.

## Próximo paso
_Última sesión: 2026-10-06._

**Hecho en la sesión del 2026-10-05/06** (detalle en `docs/decisiones.md`):
- Amoblamiento definitivo de PB, P1 y altillo con puntos eléctricos a mano (`instalaciones.<nivel>.electrico.puntos`);
  generador eléctrico nuevo; ronda de huecos de instalaciones (tierra, débiles, detectores, llaves, canillas,
  ventilaciones, rejillas de gas).
- Muros: ladrillo de 6 huecos; living de cabeza, resto de soga al ras exterior de las columnas.
- Living sin corrediza (TV al oeste, ventana norte de 3.00); logia con muro bajo + celosía al norte.
- Calefón de toda la casa en la terraza del altillo junto a A2 (sin termotanques); tanque a +10.50; caños PPR.
- Agua: SEMAPA → cisterna enterrada (nueva, junto a la puerta peatonal) → bomba → tanque. Reserva para paneles solares.
- Llegada del altillo según la obra (hueco extra sobre el tramo de 10; muro propuesto sobre el eje B).
- Fachada: alzados en `make build`, opción **C** elegida (blanco, piedra, madera, gris); 3D con materiales y sol.
- **Frente aprobado:** autos en fila al norte con portón corredizo de 3.20, puerta peatonal al sur, camino recto,
  pasto al medio, cisterna junto a la puerta, muro alto con corona anti-gatos.

**Siguiente (en este orden):**
1. ~~Frente: revisores~~ hecho 2026-10-06 (después ajustado, ver punto 2):
   tope de ruedas, corona solo hacia afuera en el portón, puerta peatonal con bisagras al norte. Antes de construir: probar la
   entrada de retro con los autos y las mediciones de `verificar_en_obra`.
2. ~~`interiorista` en el frente~~ hecho 2026-10-06 y ajustado por el dueño: gas en el pilar sur y a la vista por el muro
   sur y la fachada norte, cisterna bajo el camino (pegada al muro sur nuevo: ingeniero), bomba al sur de la puerta, luces,
   toma, canilla y cargador en el muro norte (sin poste), 7 apliques en el retiro norte, circuito C27, sirena arriba.
2b. Fachadas norte y este (2026-10-06): ventanas del P1 y del altillo alineadas con las de PB (PB sin cambios) y muebles
   acomodados. **Cuaderno de obra** (2026-10-09): `salida/cuaderno-obra.pdf` con `make cuaderno`, uno solo para albañil, plomero, gas
   y electricista: paso a paso, lista "para el dueño: cómo revisar", planos con una sola instalación por hoja (luces y teclas /
   enchufes y tablero / agua / desagüe y lluvia / gas y ventilación) con leyenda completa, tablas para contar puntos por
   ambiente, enchufes especiales, circuitos, llaves de paso y hoja de medidas. Los muros que esperan al ingeniero, en rojo.
   Revisado para imprimir (2026-10-12): notas cortas de obra (`obra:`) en cada puerta y ventana, columna "Entre" (qué ambientes une), ejes A·B·C en la planta baja, puntos de agua y luz ubicados por ambiente (sin "ØNone" ni "otros").
3. Llevar al muro de la calle la acometida eléctrica y el colector (hoy arrancan junto a la casa; el gas ya llega al
   medidor), con cámara final del colector a ≥1 m del muro y un pase bajo la viga del riel.
4. Después: patio del fondo (parrilla móvil a carbón), terminaciones (pisos, azulejos), carpintería y rejas.
   Fachada: dibujar las subidas de gas y agua caliente de la fachada norte y cómo taparlas.

## Página web de la obra (2026-10-16)
`make sitio` arma `salida/sitio/` con las hojas del cuaderno por oficio → piso → hoja, más fachadas, plantas y 3D
(adaptado al celular). `make ver-sitio` la abre en http://localhost:8000; `make publicar` la sube a Vercel (una vez:
`npm i -g vercel` y `vercel login`). **Después de cada cambio al modelo: `make publicar`** para que los trabajadores vean
lo último. Pendiente: medir en obra la ventana de la escalera (encadenado, viga, si el muro ya está) y decidir.

## Obra: el albañil empezó por el altillo (2026-10-16)
Tiene el **cuaderno v1** impreso. Se hizo el **cuaderno v2.0** (`make cuaderno`: completo + `salida/cuaderno-obra-v2.0-hojas-nuevas.pdf`
para imprimir ya). Cambios (detalle en `docs/decisiones.md`, rama `feat/altillo-obra-v2`): muros sobre columnas al ras de una
cara, aberturas al ras de las columnas, puertas del altillo más anchas, corrediza del altillo al estar, plano del albañil con
las medidas dibujadas y aberturas de frente con alturas.
Después (mismo día): corrediza frente al estar, piletas al oeste, ventana en la llegada (V7), hojas del techo y **techo del
departamento cayendo al NORTE** (pedido del maestro, los tres revisores de acuerdo; bajante BP3 en A5 y pozo de lluvia en el patio).
Y: solo el muro oeste de PB de cabeza; hoja de la BODEGA bajo la escalera; luces con símbolo por tipo (techo / aplique /
LED / baja de afuera). Recortes de luces propuestos, esperando al dueño.
**Pendiente con el dueño:** (a) ¿puertas de PB y P1 también más anchas? (b) puerta de entrada y ranura del living a 17.5 cm
de su columna; (c) calefón solar o a gas; (d) pulir el plano del albañil del P1 (zona de la suite, rótulos apretados)
antes de imprimir esas hojas.

## Revisión del arquitecto (2026-10-07)
Primera revisión completa de la casa: 26 puntos en `docs/revision-arquitecto.md` (6 urgentes de PB). Se trabajan
uno por vez con el dueño, empezando por los urgentes.

**Avance (el dueño trabaja en varias sesiones: al cerrar cada punto, actualizar esta lista):**
- Hechos: 1–6 (urgentes de PB), 7, 8 y 24 (fachada norte LISA: caños adentro en ductos junto a A2, A3 y A4, porque el
  retiro es de 2.00 justo; gas enterrado a la cocina y al calefón por el cajón gris del frente + antepechos de la terraza),
  22 (fachada oeste) y la ranura vertical del living. Todo el 2026-10-08.
- Hecho: `interiorista` por los caños adentro (muebles, llaves generales del P1 y del altillo, caños del altillo fuera del
  ducto de A4), 2026-10-08.
- Hecho: punto 9 (barandas de la escalera: fierro negro con barrotes y pasamanos de madera), 2026-10-08.
- Hecho: punto 10 (niveles de PB propuestos, en `niveles_piso` y en la planta baja; falta medir en obra), 2026-10-08.
- **Sigue:** **punto 11** (cielo falso según cuánto cuelgan las vigas) y los medios.

## Pendientes abiertos
- Ingeniero (P1, 2026-10-04): muro del vestidor x=5.85 sobre losa, muro del Baño 2 en y=3.88, viga del eje 3 en el
  techo del estar, pase de la bajante del Baño 2. Tabiques livianos = ladrillo de 6 huecos (no drywall).
- ¿Por dónde llegan los tubos del TD de PB (ingreso) a la columna B2?
- Confirmar orientación: ¿al mediodía el sol entra por el retiro (Lote 105)?
- Medir en obra: fondo del descanso, distancia de la columna B2 al primer escalón, espesor
  de losa, sección real de columnas.
- Con arquitecto/instaladores: ubicación del tanque elevado y de la bajada (se define con el altillo),
  estado de la cisterna vieja (prueba de llenado). Medir cuánto cuelgan las vigas (altura del cielo falso).
- Para el final, toda la casa junta: terminaciones (pisos, azulejos), carpintería y rejas, fachada,
  exteriores (portón, cerco, parrilla, tendedero) y medidores en el muro de la calle.
