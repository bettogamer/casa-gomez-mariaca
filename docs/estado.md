# Estado del proyecto — leer al empezar una sesión

_Última actualización: 2026-10-06_

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

- **Altillo aprobado:** departamento temporal (estar-comedor-cocina, baño, dormitorio de 18 m²) con la escalera
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
1. Frente: `revisor-estructural` (muro alto de 2.50, viga del riel del portón, excavación de la cisterna junto al
   Lote 103, colector y gas bajo los autos) y `revisor-habitabilidad` (norma: altura del muro, art. 49 cisterna,
   art. 53 b árbol en la acera, rebaje del cordón, niveles).
2. `interiorista` en el frente: luces del camino y del estacionamiento con sensor, toma con tapa y canilla para lavar
   autos, cámara mirando al portón (las luces que hoy pone el generador en el centro de los exteriores son provisorias).
3. Llevar al muro de la calle la acometida eléctrica, el gas y el colector (hoy arrancan junto a la casa), con cámara
   final del colector junto al muro.
4. Después: patio del fondo (parrilla móvil a carbón), terminaciones (pisos, azulejos), carpintería y rejas.
   Fachada: dibujar las subidas de gas y agua caliente de la fachada norte y cómo taparlas.

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
