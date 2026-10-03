"""Genera salida/visor-3d.html (three.js) desde el modelo. Uso: python tools/render_3d.py

El HTML lleva los datos embebidos, así que se abre con doble clic (file://).
"""
import json

from casa import COLORES_TIPO, SALIDA, ambientes, area, cargar, columnas, huella_casa

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
    <label><input type="checkbox" id="etiquetas" checked> Nombres de ambientes</label>
    <label><input type="checkbox" id="lote" checked> Lote</label>
  </div>
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
D.losas.forEach(cota => G.obra.add(caja(h0[0], cota - E.losa, h0[1], h0[2], cota, h0[3], 0xb9b9b4, { op: 0.92 })));
D.columnas.forEach(c => {
  const s = E.seccion / 2;
  G.obra.add(caja(c.x - s, 0, c.y - s, c.x + s, E.alto_columnas, c.y + s, 0xc62828));
});
// Escalera: tramo 1 por la derecha subiendo hacia el eje A, descanso junto al eje A, tramo 2 de vuelta.
const esc = E.escalera;
for (let piso = 0; piso < esc.pisos.length; piso++) {
  const base = esc.pisos[piso];
  const n = esc.peldanos / 2, ch = esc.contrahuella, hu = esc.huella;
  const [x0, y0, x1, y1] = esc.rect, a = esc.ancho;
  const yl = y0 + a, yi = yl + n * hu;
  for (let i = 0; i < n; i++) {
    const zt = yi - (i + 1) * hu;
    G.obra.add(caja(x1 - a, base, zt, x1, base + (i + 1) * ch, zt + hu, 0xa98b6a));
    const zt2 = yl + i * hu;
    G.obra.add(caja(x0, base, zt2, x0 + a, base + (n + i + 1) * ch, zt2 + hu, 0xa98b6a));
  }
  G.obra.add(caja(x0, base + n * ch - 0.15, y0, x1, base + n * ch, yl, 0xa98b6a));
}

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
    if (a.tipo !== "exterior") {
      for (let i = 0; i < a.poly.length; i++) {
        const [px, pz] = a.poly[i], [qx, qz] = a.poly[(i + 1) % a.poly.length];
        const t = E.muro / 2;
        const m = caja(Math.min(px, qx) - t, nv.cota, Math.min(pz, qz) - t, Math.max(px, qx) + t, nv.cota + nv.alto_muro,
                       Math.max(pz, qz) + t, a.propuesto ? 0x90caf9 : 0xf4f1ea);
        m.userData.alto = nv.alto_muro;
        m.userData.base = nv.cota;
        muros.push(m);
        grupo.add(m);
      }
    } else {
      // baranda baja
      const b = new THREE.LineLoop(new THREE.BufferGeometry().setFromPoints(a.poly.map(p => new THREE.Vector3(p[0], nv.cota + 1.0, p[1]))),
                                   new THREE.LineBasicMaterial({ color: 0x555555 }));
      grupo.add(b);
    }
    const s = etiqueta(a.nombre, a.c[0], nv.cota + 1.6, a.c[1]);
    s.userData.nivel = nv.id;
    G.etiquetas.add(s);
  });
  grupo.userData.muros = muros;
  G.niveles[nv.id] = grupo;
  escena.add(grupo);
  const lb = document.createElement("label");
  lb.innerHTML = `<input type="checkbox" checked data-nivel="${nv.id}"> ${nv.nombre} <span style="color:#888">(+${nv.cota.toFixed(2)})</span>`;
  cont.appendChild(lb);
});

function alturaMuros() {
  const corte = document.getElementById("corte").checked;
  Object.values(G.niveles).forEach(g => g.userData.muros.forEach(m => {
    const h = corte ? Math.min(1.2, m.userData.alto) : m.userData.alto;
    m.scale.y = h / m.userData.alto;
    m.position.y = m.userData.base + h / 2;
  }));
}

let modo = "proyecto";
function actualizar() {
  const vis = {};
  cont.querySelectorAll("input").forEach(i => vis[i.dataset.nivel] = i.checked);
  Object.entries(G.niveles).forEach(([id, g]) => g.visible = modo === "proyecto" && vis[id]);
  G.etiquetas.visible = modo === "proyecto" && document.getElementById("etiquetas").checked;
  G.etiquetas.children.forEach(s => s.visible = vis[s.userData.nivel]);
  G.lote.visible = document.getElementById("lote").checked;
  alturaMuros();
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
actualizar();

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


def datos(casa):
    est = casa["estructura"]
    lt = casa["lote"]
    esc = est["escalera"]
    niveles_por_id = {n["id"]: n for n in casa["niveles"]}
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
        niveles.append({"id": n["id"], "nombre": n["nombre"], "cota": n["cota"],
                        "alto_muro": n["altura"] - est["espesor_losa"], "ambientes": ambs})
    # losas construidas: contrapiso PB + cada nivel superior
    losas = [n["cota"] for n in casa["niveles"]]
    return {
        "huella": list(huella_casa(casa)),
        "lote": [lt["origen_x"], lt["origen_y"], lt["origen_x"] + lt["largo"], lt["origen_y"] + lt["ancho"]],
        "losas": losas,
        "columnas": columnas(casa),
        "estructura": {
            "seccion": est["seccion_columna"], "losa": est["espesor_losa"], "muro": est["espesor_muro_int"],
            "alto_columnas": max(losas),
            "escalera": {
                "rect": esc["rect"], "ancho": esc["ancho_tramo"], "peldanos": esc["peldanos_por_piso"],
                "huella": esc["huella"], "contrahuella": esc["contrahuella"],
                "pisos": [niveles_por_id[i]["cota"] - niveles_por_id[i]["altura"] for i in esc["sube_a"]],
            },
        },
        "niveles": niveles,
    }


def main():
    SALIDA.mkdir(exist_ok=True)
    html = PLANTILLA.replace("__DATOS__", json.dumps(datos(cargar()), ensure_ascii=False))
    f = SALIDA / "visor-3d.html"
    f.write_text(html, encoding="utf-8")
    print("→", f.relative_to(SALIDA.parent))


if __name__ == "__main__":
    main()
