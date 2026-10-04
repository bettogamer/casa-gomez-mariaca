# Viguetas de las losas — lectura del plano del proveedor

Fuente: `planos-arqui/PLANO ViGETAS.pdf`, de **Viguetas Pretensadas T.S.D.**, fechado el 24 de agosto de 2026
(maestro: Juan; reclamos: Arq. Giovana Ayala). Es la planilla de pedido de una losa; **las dos losas (+3.40 y +6.60) se armaron igual** (confirmado por el
usuario 2026-10-04). Plano generado: `salida/planta-losa-p1.svg` y `salida/planta-losa-altillo.svg`.

> Lectura nuestra del dibujo. Las direcciones, cantidades y largos son los del pedido. Lo que se armó en obra lo confirma
> el maestro o el ingeniero.

## Qué dice
- **Losa alivianada** con viguetas pretensadas y complemento de plastoformo, no losa maciza: 70 tiras de plastoformo de
  12 cm y 4 plastoformos anchos de 50 cm. El espesor total no figura.
- Viguetas **reforzadas, de 5 alambres dobles**. Se usaron 32 puntales de 3.20 m.
- Pedido por paño, del fondo hacia el frente:

| Paño (ejes) | Franja A–B (norte, 2.68) | Franja B–C (sur, 3.99) |
|---|---|---|
| 4–5 (5.70, fondo) | 11 viguetas de 2.85, van de A a B | 11 viguetas de 4.05, van de B a C |
| 3–4 (4.15) | **5 viguetas de 4.20, van de eje 3 a eje 4** (giradas) | 7 viguetas de 4.05, van de B a C |
| 2–3 (2.65) | **hueco de la escalera** | 4 viguetas de 4.05, van de B a C |
| 1–2 (4.40) | 8 viguetas de 2.85, van de A a B | 7 viguetas de 4.05, de B a C (más una franja marcada en amarillo, probablemente maciza) |
| volado del frente | 2 viguetas de 2.85 | 2 viguetas de 4.05 |

- Las líneas rojas del dibujo, a lo largo de cada franja, cruzan las viguetas por el medio. Parecen **nervios
  transversales** de refuerzo, pero el dibujo no lo dice.
- Coincide con el modelo: la franja angosta es A–B (2.68) y la ancha B–C (3.99), con 5 paños, el hueco de la escalera
  entre los ejes 2 y 3 y el volado al frente.

## Por qué importa para el diseño
En casi toda la casa **las viguetas van de norte a sur**, cruzando el ancho. Un muro nuevo sobre la losa se comporta
distinto según cómo quede respecto de las viguetas:
- **Muro que cruza las viguetas** (este–oeste): reparte el peso entre varias viguetas. Es lo más favorable.
- **Muro paralelo a las viguetas** (norte–sur): carga una sola vigueta, o el plastoformo entre dos. Es lo más
  desfavorable y lo tiene que revisar el ingeniero.

Muros sobre losa sin muro debajo:

| Muro | Piso | Dirección | Viguetas en ese paño | Situación |
|---|---|---|---|---|
| Vestidor, x=5.85 (2.47 m) | P1 | norte–sur | paño 2–3 B–C, norte–sur | ⚠️ **paralelo** |
| Baño 2, oeste x=9.40 (y 3.88–6.67) | P1 | norte–sur | paño 3–4 B–C, norte–sur | ⚠️ **paralelo** |
| Baño 1 / blancos, x=9.40 (y 0–2.68) | P1 | norte–sur | paño 3–4 A–B, **este–oeste** | ✅ cruza |
| Baño 2, norte y=3.88 | P1 | este–oeste | paño 3–4 B–C, norte–sur | ✅ cruza |
| Entre cuartos, y=3.335 | P1 | este–oeste | paño 4–5 B–C, norte–sur | ✅ cruza (a mitad de la luz) |
| Vestíbulo, x=12.50 (1.5 m) | P1 | norte–sur | paño 4–5, norte–sur | ⚠️ paralelo, corto |
| Baño/hall – dormitorio, x=13.00 | altillo | norte–sur | paño 4–5, norte–sur | ⚠️ **paralelo** (ya estaba marcado) |
| Hall, y=2.40 | altillo | este–oeste | paño 4–5 A–B y B–C | ✅ cruza |
| Muro sur del departamento, y=4.67 | altillo | este–oeste | franja B–C, norte–sur | ✅ cruza (a ~2/3 de la luz) |
| Muro ciego sur, y=6.67 | altillo | este–oeste | sobre la viga del eje C | ✅ |

Para los muros paralelos, las opciones son: ladrillo de 6 huecos solo si el ingeniero lo acepta, refuerzo, o reemplazar
el muro por un ropero o mueble de piso a techo. En el vestidor, ese plan B ya estaba anotado.

## Pases por la losa (bajantes, ductos, tubos)
- **Las viguetas pretensadas no se cortan.** Los pases van por el plastoformo, entre viguetas.
- Hay que ubicar cada pase contra la vigueta más cercana antes de perforar: bajante del Baño 2, ducto del tanque,
  bajantes de la suite y del altillo.
