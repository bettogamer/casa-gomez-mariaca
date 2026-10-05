# Estado del proyecto — leer al empezar una sesión

_Última actualización: 2026-10-05_

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
  agua (pozo + bomba → tanque elevado → gravedad), calefón a gas natural en el **núcleo técnico
  del muro norte** (entre baño y estudio), desagüe por el retiro norte con CI y desgrasadora,
  gas natural por el retiro norte. Horno y secadora eléctricos.

- **Primer piso aprobado (completo):** suite principal al frente (dormitorio con TV en el muro oeste, logia
  sobre el volado de 1 m, lavamanos abierto, inodoro y ducha propios, vestidor en U); hall en la llegada de la
  escalera; blancos al norte y estar al sur (sala de TV de 9.9 m², sin ventana, abierta al hall y al pasillo de 1.05);
  dos cuartos de 18 m² con baño privado pegado al eje 4, ropero empotrado y escritorio junto al ropero (Cuarto 1 con
  tocador y banco ventana). Ver `docs/revision-p1.md` y la entrada del 2026-10-04 en `docs/decisiones.md`.

- **Instalaciones P1 (esquema preliminar):** eléctrico con subtablero en el hall junto a la columna B2 y 4 circuitos (C8–C11), agua
  desde el núcleo técnico, 3 bajantes, extractores del Baño 2 y de los lavamanos de la suite; termotanque eléctrico propio en la suite principal (C12). Sin gas.

- **Altillo aprobado:** departamento temporal (estar-comedor-cocina, baño, dormitorio de 18 m²) con la escalera
  adentro, terraza adelante, franja de 2 m al sur con lavandería; techo de calamina oculto; tanque sobre la
  columna A3. Instalaciones (esquema): C13–C17, anafe y termotanque eléctricos, presurizadora a definir.

- **Normativa y techos (2026-10-04):** OM 4100/10 revisada (`docs/normativa.md`); planta de techos (`salida/planta-techos.svg`):
  calamina, departamento oculto tras antepecho, terraza con techo sobre fierro; muro ciego sur de ~1.80 y semisombra
  sobre la lavandería. Montante eléctrico en la columna B2.

## Próximo paso
**Amoblamiento definitivo con el agente `interiorista`** (creado 2026-10-05), piso por piso empezando por PB:
muebles + luces, enchufes, interruptores y agua, para el electricista y el plomero. Ojo: `tools/instalaciones.py`
reparte los enchufes generales sin mirar camas, sofás ni roperos (solo closets) y no pone enchufes junto a la
cama ni conmutador: probablemente haya que mejorarlo.

Revisión del altillo (`revisor-estructural`, `revisor-habitabilidad`). Después, para toda la casa junta:
exteriores (portón, jardín, parrilla en la terraza de PB, tendedero), fachada, terminaciones, carpintería y rejas.

## Pendientes abiertos
- Ingeniero (P1, 2026-10-04): muro del vestidor x=5.85 sobre losa, muro del Baño 2 en y=3.88, viga del eje 3 en el
  techo del estar, pase de la bajante del Baño 2. Tabiques livianos = ladrillo de 6 huecos (no drywall).
- ¿Por dónde llegan los tubos del TD de PB (ingreso) a la columna B2?
- Confirmar orientación: ¿al mediodía el sol entra por el retiro (Lote 105)?
- Medir en obra: fondo del descanso, distancia de la columna B2 al primer escalón, espesor
  de losa, sección real de columnas.
- Con arquitecto/instaladores: ubicación del tanque elevado y de la bajada (se define con el altillo),
  distancias del pozo. Medir cuánto cuelgan las vigas (altura del cielo falso).
- Para el final, toda la casa junta: terminaciones (pisos, azulejos), carpintería y rejas, fachada,
  exteriores (portón, cerco, parrilla, tendedero) y medidores en el muro de la calle.
