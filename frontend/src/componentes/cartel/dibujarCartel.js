// Carteles generados en canvas, portados del prototipo. Es JavaScript puro
// (sin React): recibe un <canvas> y un texto, y dibuja.

// Las tintas del prototipo: [fondo, color A, color B].
const PALETAS = [
  ['#2A1A4D', '#FF7AA8', '#FFB02E'],
  ['#0E2F3D', '#4DD8FF', '#C8F03C'],
  ['#4C1436', '#F4EFE6', '#FF7AA8'],
  ['#101B40', '#C8F03C', '#4DD8FF'],
  ['#3D1A10', '#FFB02E', '#FF7AA8'],
];

/** Convierte un texto en un número. El mismo texto siempre da el mismo número (FNV-1a). */
function numeroDeTexto(texto) {
  let h = 2166136261;
  for (let i = 0; i < texto.length; i++) {
    h ^= texto.charCodeAt(i);
    h = Math.imul(h, 16777619);
  }
  return h >>> 0;
}

/** Números "al azar" pero repetibles a partir de una semilla (mulberry32). */
function azar(semilla) {
  let a = semilla >>> 0;
  return function () {
    a = (a + 0x6d2b79f5) | 0;
    let t = Math.imul(a ^ (a >>> 15), 1 | a);
    t = (t + Math.imul(t ^ (t >>> 7), 61 | t)) ^ t;
    return ((t ^ (t >>> 14)) >>> 0) / 4294967296;
  };
}

const ESTILOS = {
  anillos(x, W, H, f, a, b) {
    const cx = W * 0.62, cy = H * 0.44, colores = [a, f, b, f];
    for (let i = 13; i >= 1; i--) {
      x.fillStyle = colores[i % 4];
      x.beginPath(); x.arc(cx, cy, i * W * 0.075, 0, Math.PI * 2); x.fill();
    }
    x.fillStyle = b; x.beginPath(); x.arc(W * 0.16, H * 0.84, W * 0.1, 0, Math.PI * 2); x.fill();
  },
  ondas(x, W, H, f, a, b) {
    const n = 9, alto = H / n;
    for (let i = -1; i <= n; i++) {
      x.fillStyle = i % 2 ? a : b;
      x.beginPath();
      for (let px = 0; px <= W; px += 6) {
        const y = i * alto + Math.sin((px / W) * Math.PI * 4 + i * 0.7) * alto * 0.55;
        if (px === 0) x.moveTo(px, y); else x.lineTo(px, y);
      }
      for (let qx = W; qx >= 0; qx -= 6) {
        x.lineTo(qx, i * alto + alto * 0.5 + Math.sin((qx / W) * Math.PI * 4 + i * 0.7) * alto * 0.55);
      }
      x.closePath(); x.fill();
    }
  },
  puntos(x, W, H, f, a, b) {
    x.fillStyle = b; x.beginPath(); x.arc(W * 0.36, H * 0.62, W * 0.4, 0, Math.PI * 2); x.fill();
    const paso = W / 13, fx = W * 0.78, fy = H * 0.22, max = W * 1.05;
    x.fillStyle = a;
    for (let i = 0; i <= 13; i++) {
      for (let j = 0; j <= 13; j++) {
        const px = i * paso, py = j * paso;
        const d = Math.hypot(px - fx, py - fy);
        const radio = paso * 0.5 * Math.max(0, 1 - d / max);
        if (radio > 0.6) { x.beginPath(); x.arc(px, py, radio, 0, Math.PI * 2); x.fill(); }
      }
    }
  },
  barras(x, W, H, f, a, b, aleatorio) {
    const n = 15, paso = W / n, medio = H * 0.56;
    for (let i = 0; i < n; i++) {
      const alto = (0.18 + aleatorio() * 0.8) * H * 0.48;
      x.fillStyle = a; x.fillRect(i * paso + paso * 0.18, medio - alto, paso * 0.64, alto);
      x.fillStyle = b; x.fillRect(i * paso + paso * 0.18, medio + H * 0.02, paso * 0.64, alto * 0.55);
    }
    x.fillStyle = f;
    for (let y = 0; y < H; y += H / 40) x.fillRect(0, y, W, H / 160);
  },
  rayos(x, W, H, f, a, b) {
    const cx = W * 0.5, cy = H * 0.98, n = 18, largo = W * 1.5;
    for (let i = 0; i < n; i += 2) {
      const t0 = Math.PI + (i / n) * Math.PI, t1 = Math.PI + ((i + 1) / n) * Math.PI;
      x.fillStyle = a; x.beginPath(); x.moveTo(cx, cy);
      x.lineTo(cx + Math.cos(t0) * largo, cy + Math.sin(t0) * largo);
      x.lineTo(cx + Math.cos(t1) * largo, cy + Math.sin(t1) * largo);
      x.closePath(); x.fill();
    }
    x.fillStyle = f; x.beginPath(); x.arc(cx, cy, W * 0.36, 0, Math.PI * 2); x.fill();
    x.fillStyle = b; x.beginPath(); x.arc(cx, cy, W * 0.29, 0, Math.PI * 2); x.fill();
  },
};
const NOMBRES_ESTILOS = Object.keys(ESTILOS);

/**
 * Dibuja el cartel de un artista. Del texto (su slug) salen el estilo y la paleta:
 * el mismo artista siempre tiene el mismo cartel en toda la app.
 */
export function dibujarCartel(lienzo, texto) {
  const x = lienzo?.getContext('2d');
  if (!x) return;
  const numero = numeroDeTexto(texto);
  const estilo = ESTILOS[NOMBRES_ESTILOS[numero % NOMBRES_ESTILOS.length]];
  const [fondo, a, b] = PALETAS[Math.floor(numero / NOMBRES_ESTILOS.length) % PALETAS.length];
  const { width: W, height: H } = lienzo;
  x.clearRect(0, 0, W, H);
  x.fillStyle = fondo;
  x.fillRect(0, 0, W, H);
  estilo(x, W, H, fondo, a, b, azar(numero));
}
