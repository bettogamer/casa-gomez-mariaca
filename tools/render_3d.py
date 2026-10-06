"""Genera salida/visor-3d.html (three.js) desde el modelo. Uso: python tools/render_3d.py

El HTML lleva los datos embebidos, así que se abre con doble clic (file://).
"""
import json

from casa import COLORES_TIPO, SALIDA, aberturas, tramos_bajo_escalera, ambientes, area, cargar, columnas, escalera, huella_casa, muebles, muro_soga, muros, seccion_muro

PLANTILLA = r"""<!doctype html>
<html lang="es">
<head>
<meta charset="utf-8">
<meta name="viewport" content="width=device-width, initial-scale=1">
<title>Casa — Visor 3D</title>
<style>
  html, body { margin: 0; height: 100%; overflow: hidden; background: #e9eef2; font: 13px/1.4 -apple-system, Helvetica, Arial, sans-serif; }
  #panel { position: absolute; top: 12px; left: 12px; background: #fffffff0; border-radius: 10px; padding: 12px 14px;
           box-shadow: 0 2px 12px #0002; max-width: 250px; }
  #panel h1 { font-size: 15px; margin: 0 0 8px; }
  #panel label { display: block; margin: 3px 0; cursor: pointer; }
  #panel .grupo { margin-top: 10px; padding-top: 8px; border-top: 1px solid #ddd; }
  #panel .mini { color: #666; font-size: 11px; margin-top: 8px; }
  .modo button { border: 1px solid #bbb; background: #f6f6f6; padding: 4px 8px; border-radius: 6px; cursor: pointer; margin: 2px 2px 2px 0; }
  .modo button.on { background: #1565c0; color: #fff; border-color: #1565c0; }
  #info { position: absolute; bottom: 12px; left: 12px; background: #fffffff0; padding: 6px 10px; border-radius: 8px; font-size: 12px; }
</style>
</head>
<body>
<div id="panel">
  <h1>Casa — Visor 3D</h1>
  <div class="modo">
    <button data-modo="obra">Obra actual</button>
    <button data-modo="proyecto" class="on">Proyecto</button>
  </div>
  <div class="grupo" id="niveles"></div>
  <div class="grupo">
    <label><input type="checkbox" id="corte" checked> Muros cortados a 1.2 m</label>
    <label><input type="checkbox" id="muebles" checked> Muebles</label>
    <label><input type="checkbox" id="etiquetas" checked> Nombres de ambientes</label>
    <label><input type="checkbox" id="lote" checked> Lote</label>
    <label><input type="checkbox" id="techos"> Techos y tanque</label>
    <label><input type="checkbox" id="fachada"> Fachada con materiales</label>
  </div>
  <div class="grupo"><b>Vistas</b><br><select id="vista" style="width:100%;margin-top:4px"><option value="">— elegir un ambiente —</option></select>
    <button id="vista-general" style="margin-top:6px">Vista general</button>
    <button id="vista-techos" style="margin-top:6px">Vista con techos</button>
    <button id="vista-calle" style="margin-top:6px">Vista desde la calle (fachada)</button>
    <button id="vista-retiro" style="margin-top:6px">Vista desde el retiro norte</button></div>
  <div class="grupo"><b>Sol</b> (Cochabamba)<br><select id="sol" style="width:100%;margin-top:4px">
    <option value="12,17">Tarde de verano (enero, 17 h)</option>
    <option value="6,17">Tarde de invierno (julio, 17 h)</option>
    <option value="12,12">Mediodía de verano</option>
    <option value="6,12">Mediodía de invierno</option>
    <option value="12,9">Mañana de verano (9 h)</option>
  </select></div>
  <div class="mini">Arrastrar: girar · Rueda: zoom · Clic derecho: mover<br>Rojo = columnas construidas</div>
</div>
<div id="info">Generado desde modelo/casa.yaml</div>
<script src="https://cdnjs.cloudflare.com/ajax/libs/three.js/r128/three.min.js"></script>
<script src="https://cdn.jsdelivr.net/npm/three@0.128.0/examples/js/controls/OrbitControls.js"></script>
<script>
const D = __DATOS__;

const escena = new THREE.Scene();
escena.background = new THREE.Color(0xe9eef2);
const camara = new THREE.PerspectiveCamera(45, innerWidth / innerHeight, 0.1, 500);
const render = new THREE.WebGLRenderer({ antialias: true });
render.setPixelRatio(devicePixelRatio);
render.setSize(innerWidth, innerHeight);
render.shadowMap.enabled = true;
document.body.appendChild(render.domElement);

const cx = (D.huella[0] + D.huella[2]) / 2, cz = (D.huella[1] + D.huella[3]) / 2;
camara.position.set(cx - 14, 16, cz + 20);
const ctl = new THREE.OrbitControls(camara, render.domElement);
ctl.target.set(cx, 2.5, cz);
ctl.update();

escena.add(new THREE.HemisphereLight(0xffffff, 0x888877, 0.75));
const sol = new THREE.DirectionalLight(0xffffff, 0.6);
sol.position.set(cx - 15, 30, cz - 20);
sol.castShadow = true;
sol.shadow.mapSize.set(2048, 2048);
Object.assign(sol.shadow.camera, { left: -30, right: 30, top: 30, bottom: -30 });
escena.add(sol);

function caja(x0, y0, z0, x1, y1, z1, color, opts = {}) {
  const g = new THREE.BoxGeometry(Math.abs(x1 - x0), Math.abs(y1 - y0), Math.abs(z1 - z0));
  const m = new THREE.MeshLambertMaterial({ color, transparent: !!opts.op, opacity: opts.op || 1 });
  const b = new THREE.Mesh(g, m);
  b.position.set((x0 + x1) / 2, (y0 + y1) / 2, (z0 + z1) / 2);
  b.castShadow = b.receiveShadow = true;
  return b;
}

function segmento(p, q, y0, y1, grosor, color) {
  // muro recto de p a q (planta), entre las alturas y0 e y1
  const L = Math.hypot(q[0] - p[0], q[1] - p[1]);
  const b = new THREE.Mesh(new THREE.BoxGeometry(L + grosor, y1 - y0, grosor), new THREE.MeshLambertMaterial({ color }));
  b.position.set((p[0] + q[0]) / 2, (y0 + y1) / 2, (p[1] + q[1]) / 2);
  b.rotation.y = -Math.atan2(q[1] - p[1], q[0] - p[0]);
  b.castShadow = b.receiveShadow = true;
  return b;
}

// Piezas que cambian de color con "Fachada con materiales": FCH[categoría] = [mallas]
const FCH = {};
function tag(mesh, cat) {
  (FCH[cat] = FCH[cat] || []).push(mesh);
  mesh.userData.colorBase = mesh.material.color.getHex();
  mesh.userData.opBase = mesh.material.opacity;
  return mesh;
}

function etiqueta(texto, x, y, z) {
  const c = document.createElement("canvas");
  c.width = 512; c.height = 96;
  const k = c.getContext("2d");
  k.font = "bold 40px Helvetica, Arial";
  k.textAlign = "center";
  k.fillStyle = "#222";
  k.fillText(texto, 256, 60);
  const s = new THREE.Sprite(new THREE.SpriteMaterial({ map: new THREE.CanvasTexture(c), depthTest: false }));
  s.position.set(x, y, z);
  s.scale.set(3.2, 0.6, 1);
  return s;
}

// Grupos para encender/apagar
const G = { lote: new THREE.Group(), obra: new THREE.Group(), etiquetas: new THREE.Group(), niveles: {} };
escena.add(G.lote, G.obra, G.etiquetas);

// Lote
const L = D.lote;
const suelo = caja(L[0], -0.05, L[1], L[2], 0, L[3], 0xcfe3b8);
G.lote.add(suelo);

// Estructura construida
const E = D.estructura;
const h0 = D.huella;
// Losas con el hueco de la escalera que llega a ese nivel
const LOSAS = [], COLUMNAS = [];
let nivelVista = null;   // en una vista de ambiente: solo se rotula ese nivel
D.losas.forEach(l => {
  const forma = new THREE.Shape([[h0[0], h0[1]], [h0[2], h0[1]], [h0[2], h0[3]], [h0[0], h0[3]]].map(p => new THREE.Vector2(p[0], p[1])));
  if (l.hueco) {
    const [a, b, c, d] = l.hueco;
    forma.holes.push(new THREE.Path([[a, b], [a, d], [c, d], [c, b]].map(p => new THREE.Vector2(p[0], p[1]))));
  }
  const g = new THREE.ExtrudeGeometry(forma, { depth: E.losa, bevelEnabled: false });
  const m = tag(new THREE.Mesh(g, new THREE.MeshLambertMaterial({ color: 0xb9b9b4, transparent: true, opacity: 0.92 })), "losa");
  m.rotation.x = Math.PI / 2;      // (x, y) del plano -> (x, z) del 3D; la extrusión baja desde la cota
  m.position.y = l.cota;
  m.castShadow = m.receiveShadow = true;
  m.userData.cota = l.cota;
  LOSAS.push(m);
  G.obra.add(m);
});
D.columnas.forEach(c => {
  const s = E.seccion / 2;
  const col = tag(caja(c.x - s, 0, c.y - s, c.x + s, E.alto_columnas, c.y + s, 0xc62828), "columna");
  COLUMNAS.push(col);
  G.obra.add(col);
});
// Escalera (geometría calculada en tools/casa.py: cada peldaño es un bloque macizo hasta su pisada)
D.escalera.forEach(e => {
  e.peldanos.forEach(p => G.obra.add(caja(p.x0, Math.max(e.base, p.z - 0.45), p.y0, p.x1, p.z, p.y1, 0xa98b6a)));
  const d = e.descanso;
  G.obra.add(caja(d.x0, d.z - 0.15, d.y0, d.x1, d.z, d.y1, 0x8f7556));
});

// Ambientes por nivel
const cont = document.getElementById("niveles");
D.niveles.forEach(nv => {
  const grupo = new THREE.Group();
  const muros = [];
  nv.ambientes.forEach(a => {
    const forma = new THREE.Shape(a.poly.map(p => new THREE.Vector2(p[0], p[1])));
    const piso = new THREE.Mesh(new THREE.ShapeGeometry(forma), new THREE.MeshLambertMaterial({ color: a.color, side: THREE.DoubleSide }));
    piso.rotation.x = Math.PI / 2;
    piso.position.y = nv.cota + 0.01;
    piso.receiveShadow = true;
    grupo.add(piso);
    if (a.tipo === "exterior" && nv.cota > 1) {
      // baranda baja en exteriores elevados (balcones)
      const b = new THREE.LineLoop(new THREE.BufferGeometry().setFromPoints(a.poly.map(p => new THREE.Vector3(p[0], nv.cota + 1.0, p[1]))),
                                   new THREE.LineBasicMaterial({ color: 0x555555 }));
      grupo.add(b);
    }
    const s = etiqueta(a.nombre, a.c[0], nv.cota + 1.6, a.c[1]);
    s.userData.nivel = nv.id;
    G.etiquetas.add(s);
  });
  nv.muros.forEach(m => {
    if (m.tipo === "celosia_madera") {
      // listones verticales de 4 x 4 cm cada 10 cm
      const [x0, z0] = m.de, [x1, z1] = m.a;
      const L = Math.hypot(x1 - x0, z1 - z0), n = Math.floor(L / 0.10);
      for (let k = 0; k <= n; k++) {
        const x = x0 + (x1 - x0) * k / n, z = z0 + (z1 - z0) * k / n;
        const l = tag(caja(x - 0.02, nv.cota, z - 0.02, x + 0.02, nv.cota + nv.alto_muro, z + 0.02, 0xa0703f), "celosia");
        l.userData.alto = nv.alto_muro; l.userData.base = nv.cota;
        muros.push(l); grupo.add(l);
      }
      return;
    }
    // barandas y antepechos con su propio alto; bajo la escalera, hasta su cara inferior
    const alto = m.alto ? Math.min(m.alto, nv.alto_muro) : (m.tipo === "baranda" ? 1.1 : nv.alto_muro);
    const w = tag(segmento(m.de, m.a, nv.cota, nv.cota + alto, m.grosor, 0xf4f1ea),
                  m.tipo === "baranda" ? (alto <= 1.2 ? "baranda" : "antepecho") : "muro");
    w.userData.alto = alto; w.userData.base = nv.cota;
    muros.push(w); grupo.add(w);
  });
  // dinteles sobre puertas y ventanas; antepecho bajo ventanas (se ocultan con el corte a 1.2 m)
  const dinteles = [];
  nv.aberturas.forEach(ab => {
    if (ab.tipo === "vano") return;
    const d = tag(segmento(ab.de, ab.a, nv.cota + ab.alto, nv.cota + nv.alto_muro, ab.grosor, 0xe8e4da), "muro");
    dinteles.push(d); grupo.add(d);
    if (ab.tipo === "ventana") {
      const ap = tag(segmento(ab.de, ab.a, nv.cota, nv.cota + ab.antepecho, ab.grosor, 0xf4f1ea), "muro");
      ap.userData.alto = ab.antepecho; ap.userData.base = nv.cota;
      muros.push(ap); grupo.add(ap);
    }
  });
  grupo.userData.dinteles = dinteles;
  const gm = new THREE.Group();
  nv.muebles.forEach(m => {
    const [x0, z0, x1, z1] = m.rect;
    gm.add(caja(x0, nv.cota + 0.01, z0, x1, nv.cota + 0.01 + m.alto, z1, m.color));
  });
  grupo.add(gm);
  grupo.userData.muebles = gm;
  grupo.userData.muros = muros;
  G.niveles[nv.id] = grupo;
  escena.add(grupo);
  const lb = document.createElement("label");
  lb.innerHTML = `<input type="checkbox" checked data-nivel="${nv.id}"> ${nv.nombre} <span style="color:#888">(+${nv.cota.toFixed(2)})</span>`;
  cont.appendChild(lb);
});

// Techos (planta de techos del modelo): aguas inclinadas, antepechos, tanque, postes, canaletas, bajantes, semisombra
G.techos = new THREE.Group();
escena.add(G.techos);
if (D.techos) {
  const T = D.techos;
  T.aguas.forEach(ag => {
    const ts = ag.poly.map(p => p[0] * ag.dir[0] + p[1] * ag.dir[1]);
    const t0 = Math.min(...ts), t1 = Math.max(...ts);
    const h = p => ag.alta - ((p[0] * ag.dir[0] + p[1] * ag.dir[1] - t0) / ((t1 - t0) || 1)) * (ag.alta - ag.baja);
    const v = ag.poly.map(p => new THREE.Vector3(p[0], h(p), p[1]));
    const g = new THREE.BufferGeometry().setFromPoints([v[0], v[1], v[2], v[0], v[2], v[3]]);
    g.computeVertexNormals();
    const m = tag(new THREE.Mesh(g, new THREE.MeshLambertMaterial({ color: 0x90a4ae, side: THREE.DoubleSide })), "techo");
    m.castShadow = m.receiveShadow = true;
    G.techos.add(m);
    // ondas de la calamina: líneas en el sentido de la caída
    const perp = [-ag.dir[1], ag.dir[0]];
    const ps = ag.poly.map(p => p[0] * perp[0] + p[1] * perp[1]);
    const pts = [];
    for (let s = Math.min(...ps) + 0.25; s < Math.max(...ps); s += 0.25) {
      const a = [perp[0] * s + ag.dir[0] * t0, perp[1] * s + ag.dir[1] * t0];
      const b = [perp[0] * s + ag.dir[0] * t1, perp[1] * s + ag.dir[1] * t1];
      pts.push(new THREE.Vector3(a[0], h(a) + 0.01, a[1]), new THREE.Vector3(b[0], h(b) + 0.01, b[1]));
    }
    G.techos.add(new THREE.LineSegments(new THREE.BufferGeometry().setFromPoints(pts), new THREE.LineBasicMaterial({ color: 0x607d8b })));
  });
  T.antepechos.forEach(a => G.techos.add(tag(segmento(a.de, a.a, a.base, a.tope, 0.15, 0xf4f1ea), "antepecho")));
  if (T.tanque) {
    const [x0, z0, x1, z1] = T.tanque.rect, b = T.tanque.cota_base;
    G.techos.add(caja(x0, b - 0.20, z0, x1, b, z1, 0x9e9e9e));                       // base de hormigón
    G.techos.add(tag(caja(x0 + 0.05, b, z0 + 0.05, x1 - 0.05, b + T.tanque.alto, z1 - 0.05, 0xc1866b), "tanque"));  // forro de ladrillo
    G.techos.add(caja(x0, b + T.tanque.alto, z0, x1, b + T.tanque.alto + 0.08, z1, 0xbdbdbd));       // tapa
    const s = etiqueta("Tanque " + (T.tanque.capacidad || ""), (x0 + x1) / 2, b + T.tanque.alto + 0.6, (z0 + z1) / 2);
    G.techos.add(s);
  }
  T.postes.forEach(p => G.techos.add(tag(caja(p.pos[0] - 0.05, 6.60, p.pos[1] - 0.05, p.pos[0] + 0.05, p.tope, p.pos[1] + 0.05, 0x37474f), "poste")));
  T.canaletas.forEach(c => G.techos.add(tag(segmento(c.de, c.a, c.cota, c.cota + 0.12, 0.12, 0x1565c0), "canaleta")));
  T.bajantes.forEach(b => {
    const cil = tag(new THREE.Mesh(new THREE.CylinderGeometry(0.05, 0.05, b.tope, 12), new THREE.MeshLambertMaterial({ color: 0x1565c0 })), "canaleta");
    cil.position.set(b.pos[0], b.tope / 2, b.pos[1]);
    G.techos.add(cil);
  });
  T.semisombras.forEach(s => {
    const [x0, z0, x1, z1] = s.rect;
    G.techos.add(caja(x0, s.cota, z0, x1, s.cota + 0.02, z1, 0x2e7d32, { op: 0.45 }));
  });
}

// ── Fachada con materiales (opción elegida del modelo): colores, acentos, vidrios y puertas, sol ──
const F = D.fachada;
const hex = c => parseInt(c.slice(1), 16);
function textura(material, ancho, alto) {
  const c = document.createElement("canvas");
  c.width = Math.max(64, Math.round(ancho * 100)); c.height = Math.max(64, Math.round(alto * 100));
  const k = c.getContext("2d");
  const base = { madera: "#a8703f", piedra: "#9a948b", negro: "#2b2b2b", gris_oscuro: "#43464a",
                 blanco: "#f7f7f5", beige: "#d8c9b1", gris_claro: "#c9c6c0" }[material] || "#cccccc";
  k.fillStyle = base; k.fillRect(0, 0, c.width, c.height);
  if (material === "madera") {          // listones verticales de ~8 cm con vetas
    for (let x = 0; x < c.width; x += 8) {
      k.fillStyle = `hsl(28, 45%, ${30 + Math.random() * 14}%)`; k.fillRect(x, 0, 7, c.height);
      k.fillStyle = "#5a3a1e"; k.fillRect(x + 7, 0, 1, c.height);
    }
  } else if (material === "piedra") {   // piedra laja en hiladas irregulares
    for (let y = 0; y < c.height; y += 15) {
      let x = -Math.random() * 40;
      while (x < c.width) {
        const w = 25 + Math.random() * 45, l = 48 + Math.random() * 18;
        k.fillStyle = `hsl(35, ${6 + Math.random() * 8}%, ${l}%)`; k.fillRect(x, y, w - 2, 13);
        x += w;
      }
    }
  }
  const t = new THREE.CanvasTexture(c);
  return t;
}
const ACENTOS = new THREE.Group(), CARP = new THREE.Group();
escena.add(ACENTOS, CARP);
if (F) {
  // acentos: paño de material pegado a la cara del muro (vista, u, z, d como en los alzados)
  (F.acentos || []).forEach(a => {
    const [u0, u1] = a.u, [z0, z1] = a.z, w = u1 - u0, h = z1 - z0, um = (u0 + u1) / 2;
    const m = new THREE.Mesh(new THREE.PlaneGeometry(w, h), new THREE.MeshLambertMaterial({ map: textura(a.material, w, h) }));
    const sep = 0.012;
    if (a.vista === "oeste") { m.position.set(a.d - sep, (z0 + z1) / 2, um); m.rotation.y = -Math.PI / 2; }
    if (a.vista === "este")  { m.position.set(-a.d + sep, (z0 + z1) / 2, -um); m.rotation.y = Math.PI / 2; }
    if (a.vista === "norte") { m.position.set(-um, (z0 + z1) / 2, a.d - sep); m.rotation.y = Math.PI; }
    if (a.vista === "sur")   { m.position.set(um, (z0 + z1) / 2, -a.d + sep); }
    m.receiveShadow = true;
    ACENTOS.add(m);
  });
  // vidrios y puertas en las aberturas (en el plano medio del muro)
  D.niveles.forEach(nv => nv.aberturas.forEach(ab => {
    if (ab.tipo === "vano") return;
    const L = Math.hypot(ab.a[0] - ab.de[0], ab.a[1] - ab.de[1]);
    const mx = (ab.de[0] + ab.a[0]) / 2, mz = (ab.de[1] + ab.a[1]) / 2, rot = -Math.atan2(ab.a[1] - ab.de[1], ab.a[0] - ab.de[0]);
    const vidrio = ab.tipo === "ventana" || ab.tipo === "corrediza";
    const z0 = nv.cota + (ab.tipo === "ventana" ? ab.antepecho : 0), z1 = nv.cota + ab.alto;
    const mat = vidrio ? new THREE.MeshLambertMaterial({ color: 0x7fa7bf, transparent: true, opacity: 0.55 })
                       : new THREE.MeshLambertMaterial({ color: hex(F.paleta.puerta || "#a8703f") });
    const p = new THREE.Mesh(new THREE.BoxGeometry(L, z1 - z0, vidrio ? 0.02 : 0.05), mat);
    p.position.set(mx, (z0 + z1) / 2, mz); p.rotation.y = rot; p.castShadow = !vidrio;
    CARP.add(p);
    // marco
    const marco = new THREE.LineSegments(new THREE.EdgesGeometry(new THREE.BoxGeometry(L, z1 - z0, 0.06)),
                                         new THREE.LineBasicMaterial({ color: hex(F.paleta.marco || "#2b2b2b") }));
    marco.position.copy(p.position); marco.rotation.y = rot;
    CARP.add(marco);
  }));
}
function aplicarFachada() {
  const on = !!F && document.getElementById("fachada").checked;
  ACENTOS.visible = CARP.visible = on && modo === "proyecto";
  const pal = on ? { canaleta: F.paleta.marco, ...F.paleta } : {};
  Object.entries(FCH).forEach(([cat, ms]) => ms.forEach(m => {
    const c = pal[cat] ? hex(pal[cat]) : m.userData.colorBase;
    m.material.color.setHex(c);
    if (cat === "losa") m.material.opacity = on ? 1 : m.userData.opBase;
    if (cat === "baranda") {          // baranda de barrotes: se ve a través
      m.material.transparent = true;
      m.material.opacity = on ? 0.35 : m.userData.opBase;
      m.material.needsUpdate = true;
    }
  }));
  escena.background = new THREE.Color(on ? 0xbfd9ee : 0xe9eef2);
  sol.intensity = on ? 0.95 : 0.6;
}
// Sol de Cochabamba (lat −17.4°): mes y hora solar → posición de la luz (norte = −z, este = +x)
function ponerSol() {
  const [mes, hora] = document.getElementById("sol").value.split(",").map(Number);
  const N = [17, 47, 75, 105, 135, 162, 198, 228, 258, 288, 318, 344][mes - 1];
  const r = Math.PI / 180, lat = -17.4 * r;
  const dec = 23.44 * r * Math.sin(2 * Math.PI * (284 + N) / 365);
  const H = 15 * (hora - 12) * r;
  const alt = Math.asin(Math.sin(lat) * Math.sin(dec) + Math.cos(lat) * Math.cos(dec) * Math.cos(H));
  const az = Math.atan2(Math.sin(H), Math.cos(H) * Math.sin(lat) - Math.tan(dec) * Math.cos(lat)) + Math.PI;  // desde el norte, horario
  const dx = Math.sin(az) * Math.cos(alt), dy = Math.sin(alt), dn = Math.cos(az) * Math.cos(alt);
  sol.position.set(cx + dx * 40, dy * 40, cz - dn * 40);
  sol.target.position.set(cx, 0, cz);
  escena.add(sol.target);
}
document.getElementById("sol").addEventListener("change", ponerSol);
ponerSol();
function vistaFachada(pos, mira) {
  selVista.value = ""; nivelVista = null;
  cont.querySelectorAll("input").forEach(i => i.checked = true);
  ["techos", "fachada"].forEach(id => document.getElementById(id).checked = true);
  ["corte", "etiquetas", "muebles"].forEach(id => document.getElementById(id).checked = false);
  modo = "proyecto";
  document.querySelectorAll(".modo button").forEach(o => o.classList.toggle("on", o.dataset.modo === "proyecto"));
  actualizar();
  camara.position.set(...pos); ctl.target.set(...mira); ctl.update();
}
document.getElementById("vista-calle").addEventListener("click", () => vistaFachada([-17, 2.2, cz + 4], [0, 4.6, cz]));
document.getElementById("vista-retiro").addEventListener("click", () => vistaFachada([-9, 3.0, -9], [6, 4.5, 2]));

function alturaMuros() {
  const corte = document.getElementById("corte").checked;
  Object.values(G.niveles).forEach(g => g.userData.muros.forEach(m => {
    const h = corte ? Math.min(1.2, m.userData.alto) : m.userData.alto;
    m.scale.y = h / m.userData.alto;
    m.position.y = m.userData.base + h / 2;
  }));
  Object.values(G.niveles).forEach(g => g.userData.dinteles.forEach(d => d.visible = !corte));
}

let modo = "proyecto";
function actualizar() {
  const vis = {};
  cont.querySelectorAll("input").forEach(i => vis[i.dataset.nivel] = i.checked);
  Object.entries(G.niveles).forEach(([id, g]) => g.visible = modo === "proyecto" && vis[id]);
  G.etiquetas.visible = modo === "proyecto" && document.getElementById("etiquetas").checked;
  G.etiquetas.children.forEach(s => s.visible = vis[s.userData.nivel] && (nivelVista === null || s.userData.nivel === nivelVista));
  // losas y columnas: en "Proyecto" no se dibuja lo que está por encima del último nivel visible
  const visibles = D.niveles.filter(n => vis[n.id]);
  const tope = visibles.length ? Math.max(...visibles.map(n => n.cota)) : 0;
  LOSAS.forEach(m => m.visible = modo === "obra" || m.userData.cota <= tope + 0.01);
  const altoCol = modo === "obra" ? E.alto_columnas
    : Math.min(E.alto_columnas, tope + (document.getElementById("corte").checked ? 1.2 : 3.0));
  COLUMNAS.forEach(c => { c.scale.y = altoCol / E.alto_columnas; c.position.y = altoCol / 2; });
  G.lote.visible = document.getElementById("lote").checked;
  const conTecho = document.getElementById("techos").checked;
  G.techos.visible = modo === "proyecto" && conTecho && vis["altillo"] !== false;
  Object.values(G.niveles).forEach(g => g.userData.muebles.visible = document.getElementById("muebles").checked);
  alturaMuros();
  aplicarFachada();
  document.getElementById("info").textContent = modo === "obra"
    ? "Obra actual: columnas, losas y escalera (lo ya construido)"
    : "Proyecto: generado desde modelo/casa.yaml";
}
document.querySelectorAll("#panel input").forEach(i => i.addEventListener("change", actualizar));
document.querySelectorAll(".modo button").forEach(b => b.addEventListener("click", () => {
  modo = b.dataset.modo;
  document.querySelectorAll(".modo button").forEach(o => o.classList.toggle("on", o === b));
  actualizar();
}));
// Vistas por ambiente: muestra ese nivel y los de abajo, muros cortados, cámara en diagonal sobre el ambiente
const selVista = document.getElementById("vista");
const VISTAS = [];
D.niveles.forEach(nv => nv.ambientes.forEach(a => {
  if (!["dormitorio", "social", "bano", "cocina", "servicio", "exterior"].includes(a.tipo)) return;
  VISTAS.push({ nv, a });
  const o = document.createElement("option");
  o.value = VISTAS.length - 1;
  o.textContent = `${nv.nombre}: ${a.nombre}`;
  selVista.appendChild(o);
}));
function irAVista(k) {
  const { nv, a } = VISTAS[k];
  nivelVista = nv.id;
  modo = "proyecto";
  document.querySelectorAll(".modo button").forEach(o => o.classList.toggle("on", o.dataset.modo === "proyecto"));
  cont.querySelectorAll("input").forEach(i => {
    const otro = D.niveles.find(n => n.id === i.dataset.nivel);
    i.checked = otro.cota <= nv.cota + 0.01;
  });
  document.getElementById("corte").checked = true;
  document.getElementById("muebles").checked = true;
  document.getElementById("techos").checked = false;
  actualizar();
  const xs = a.poly.map(p => p[0]), zs = a.poly.map(p => p[1]);
  const x = (Math.min(...xs) + Math.max(...xs)) / 2, z = (Math.min(...zs) + Math.max(...zs)) / 2;
  const t = Math.max(Math.max(...xs) - Math.min(...xs), Math.max(...zs) - Math.min(...zs)) * 1.1 + 3.5;
  ctl.target.set(x, nv.cota + 0.3, z);
  camara.position.set(x - t * 0.20, nv.cota + t * 1.9, z + t * 0.55);
  ctl.update();
}
selVista.addEventListener("change", () => { if (selVista.value !== "") irAVista(+selVista.value); });
document.getElementById("vista-general").addEventListener("click", () => {
  selVista.value = "";
  nivelVista = null;
  cont.querySelectorAll("input").forEach(i => i.checked = true);
  actualizar();
  camara.position.set(cx - 14, 16, cz + 20); ctl.target.set(cx, 2.5, cz); ctl.update();
});
document.getElementById("vista-techos").addEventListener("click", () => {
  selVista.value = "";
  nivelVista = null;
  cont.querySelectorAll("input").forEach(i => i.checked = true);
  document.getElementById("techos").checked = true;
  document.getElementById("corte").checked = false;
  document.getElementById("etiquetas").checked = false;
  modo = "proyecto";
  document.querySelectorAll(".modo button").forEach(o => o.classList.toggle("on", o.dataset.modo === "proyecto"));
  actualizar();
  camara.position.set(cx - 17, 17, cz + 15); ctl.target.set(cx, 6, cz); ctl.update();
});
// Atajos por URL: #obra (solo lo construido), #retiro (cámara desde el retiro lateral, Lote 105), #pb (solo planta baja)
if (location.hash.includes("obra")) document.querySelector('[data-modo="obra"]').click();
if (location.hash.includes("retiro")) { camara.position.set(cx - 4, 7, cz - 13); ctl.target.set(cx - 3, 1.2, cz); ctl.update(); }
if (location.hash.includes("pb")) cont.querySelectorAll("input").forEach(i => i.checked = i.dataset.nivel === "pb");
actualizar();
if (location.hash.includes("techos")) document.getElementById("vista-techos").click();   // #techos
if (location.hash.includes("calle")) document.getElementById("vista-calle").click();     // #calle
if (location.hash.includes("foto")) { ["panel", "info"].forEach(id => document.getElementById(id).style.display = "none"); G.techos.children.forEach(o => { if (o.isSprite) o.visible = false; }); }  // #calle&foto: captura limpia
// #vista=Cuarto 1 → abre directamente la vista de ese ambiente (busca por nombre)
const mv = decodeURIComponent(location.hash).match(/vista=([^&]+)/);
if (mv) { const k = VISTAS.findIndex(v => (v.nv.nombre + ": " + v.a.nombre).toLowerCase().includes(mv[1].toLowerCase())); if (k >= 0) { selVista.value = k; irAVista(k); } }

addEventListener("resize", () => {
  camara.aspect = innerWidth / innerHeight;
  camara.updateProjectionMatrix();
  render.setSize(innerWidth, innerHeight);
});
(function bucle() { requestAnimationFrame(bucle); render.render(escena, camara); })();
</script>
</body>
</html>
"""



def _sobre_muro(casa, nivel_id, ab):
    """Extremos y grosor de una abertura sobre el eje real de su muro (perimetrales de soga corridos)."""
    g, dx, dy = seccion_muro(casa, nivel_id, ab["de"], ab["a"])
    return {"de": [ab["de"][0] + dx, ab["de"][1] + dy], "a": [ab["a"][0] + dx, ab["a"][1] + dy], "grosor": g}

def datos(casa):
    est = casa["estructura"]
    lt = casa["lote"]
    esc = est["escalera"]
    orden = {n["id"]: k for k, n in enumerate(casa["niveles"])}
    niveles = []
    for n in casa["niveles"]:
        ambs = []
        for a in ambientes(casa, n["id"]):
            xs = [p[0] for p in a["poly"]]
            ys = [p[1] for p in a["poly"]]
            ambs.append({
                "nombre": a["nombre"], "tipo": a["tipo"], "poly": a["poly"],
                "color": COLORES_TIPO.get(a["tipo"], "#eeeeee"),
                "c": [(min(xs) + max(xs)) / 2, (min(ys) + max(ys)) / 2],
                "area": round(area(a["poly"]), 2),
                "propuesto": a.get("estado") == "propuesto",
            })
        lista_muros = []
        for m in muros(casa, n["id"]):
            if m["tipo"] != "ladrillo":
                grosor = seccion_muro(casa, n["id"], m["de"], m["a"])[0]
                lista_muros.append({"de": m["de"], "a": m["a"], "tipo": m["tipo"], "grosor": grosor, "alto": m.get("alto")})
                continue
            dx, dy = m["dx"], m["dy"]
            for d, a, alto in tramos_bajo_escalera(casa, n["id"], m["de"], m["a"]):
                lista_muros.append({"de": [d[0] + dx, d[1] + dy], "a": [a[0] + dx, a[1] + dy], "tipo": "ladrillo",
                                    "grosor": m["grosor"], "alto": alto})
        niveles.append({"id": n["id"], "nombre": n["nombre"], "cota": n["cota"],
                        "muros": lista_muros,
                        "muebles": [{"rect": m["rect"], "alto": m["alto"], "color": m["color"]} for m in muebles(casa, n["id"])],
                        "aberturas": [{**_sobre_muro(casa, n["id"], ab), "tipo": ab["tipo"], "alto": ab.get("alto", 2.10),
                                       "antepecho": ab.get("antepecho", 1.0)}
                                      for ab in aberturas(casa, n["id"])],
                        "alto_muro": n["altura"] - est["espesor_losa"], "ambientes": ambs})
    # losas: contrapiso PB + cada nivel superior, con hueco sobre la escalera que llega
    huecos = {}
    for e in escalera(casa):
        cajas = e["peldanos"] + [e["descanso"]]
        huecos[e["hasta"]] = [min(b["x0"] for b in cajas), min(b["y0"] for b in cajas),
                              max(b["x1"] for b in cajas), max(b["y1"] for b in cajas)]
    losas = [{"cota": n["cota"], "hueco": huecos.get(n["id"])} for n in casa["niveles"]]
    return {
        "huella": list(huella_casa(casa)),
        "lote": [lt["origen_x"], lt["origen_y"], lt["origen_x"] + lt["largo"], lt["origen_y"] + lt["ancho"]],
        "losas": losas,
        "columnas": columnas(casa),
        "estructura": {
            "seccion": est["seccion_columna"], "losa": est["espesor_losa"], "muro": muro_soga(casa),
            "alto_columnas": max(l["cota"] for l in losas),
        },
        "escalera": escalera(casa),
        "niveles": niveles,
        "techos": datos_techos(casa),
        "fachada": _fachada_elegida(casa),
    }


def _fachada_elegida(casa):
    fz = casa.get("fachada") or {}
    op = next((o for o in fz.get("opciones") or [] if o["id"] == fz.get("elegida")), None)
    return {"paleta": op.get("paleta") or {}, "acentos": op.get("acentos") or [], "nombre": op["nombre"]} if op else None


def datos_techos(casa):
    """Techos para el 3D: aguas inclinadas, antepechos, tanque, postes, canaletas, bajantes y semisombras."""
    t = casa.get("techos")
    if not t:
        return None
    caida = {"sur": (0, 1), "norte": (0, -1), "este": (1, 0), "oeste": (-1, 0)}
    aguas = []
    for ag in t["aguas"]:
        aguas.append({"poly": ag["poly"], "dir": caida[ag["cae_hacia"]], "alta": ag["cota_alta"], "baja": ag["cota_baja"]})

    def agua_en(x, y):
        for ag in aguas:
            xs, ys = [p[0] for p in ag["poly"]], [p[1] for p in ag["poly"]]
            if min(xs) - 0.01 <= x <= max(xs) + 0.01 and min(ys) - 0.01 <= y <= max(ys) + 0.01:
                return ag
        return None

    def altura(ag, x, y):
        d = ag["dir"]
        ts = [p[0] * d[0] + p[1] * d[1] for p in ag["poly"]]
        k = (x * d[0] + y * d[1] - min(ts)) / ((max(ts) - min(ts)) or 1)
        return ag["alta"] - k * (ag["alta"] - ag["baja"])

    postes = []
    for po in t.get("postes", []):
        ag = agua_en(*po["pos"])
        postes.append({"pos": po["pos"], "tope": altura(ag, *po["pos"]) - 0.05 if ag else 9.0})
    canaletas = []
    for c in t.get("canaletas", []):
        ag = agua_en(*c["de"]) or agua_en(*c["a"])
        canaletas.append({"de": c["de"], "a": c["a"], "cota": (ag["baja"] if ag else 9.0) - 0.12})
    bajantes = [{"pos": b["pos"], "tope": min(a["baja"] for a in aguas)} for b in t.get("bajantes", [])]
    return {
        "aguas": aguas,
        "antepechos": [{"de": m["de"], "a": m["a"], "base": m["cota_base"], "tope": m["cota_tope"]}
                       for m in t.get("antepechos", []) if "cota_tope" in m],
        "tanque": t.get("tanque"),
        "postes": postes,
        "canaletas": canaletas,
        "bajantes": bajantes,
        "semisombras": [{"rect": s["rect"], "cota": 8.40} for s in t.get("semisombras", [])],
    }


def main():
    SALIDA.mkdir(exist_ok=True)
    html = PLANTILLA.replace("__DATOS__", json.dumps(datos(cargar()), ensure_ascii=False))
    f = SALIDA / "visor-3d.html"
    f.write_text(html, encoding="utf-8")
    print("→", f.relative_to(SALIDA.parent))


if __name__ == "__main__":
    main()
