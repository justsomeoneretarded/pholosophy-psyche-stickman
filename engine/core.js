// Core helpers: maths, easing, IK, seeded noise, timeline.
'use strict';
const STAGE_W = 1920, STAGE_H = 1080, GROUND = 880;
const clamp = (v, a, b) => Math.max(a, Math.min(b, v));
const lerp = (a, b, t) => a + (b - a) * t;
const smooth = x => { x = clamp(x, 0, 1); return x * x * (3 - 2 * x); };
const easeOut = x => 1 - Math.pow(1 - clamp(x, 0, 1), 3);
const easeIn = x => Math.pow(clamp(x, 0, 1), 3);
const easeInOut = x => { x = clamp(x, 0, 1); return x < .5 ? 4 * x * x * x : 1 - Math.pow(-2 * x + 2, 3) / 2; };
const backOut = x => { x = clamp(x, 0, 1); const c = 1.7; return 1 + (c + 1) * Math.pow(x - 1, 3) + c * Math.pow(x - 1, 2); };
const pct = x => x / 100 * STAGE_W;

function hash(n) { const s = Math.sin(n * 127.1 + 311.7) * 43758.5453; return s - Math.floor(s); }
function strHash(s) { let h = 7; for (const c of String(s)) h = (h * 31 + c.charCodeAt(0)) % 100003; return h; }
function rng(seed) { let s = seed >>> 0 || 1; return () => { s = (s * 1664525 + 1013904223) >>> 0; return s / 4294967296; }; }
function noise1(t, seed = 0) { const i = Math.floor(t), f = t - i; return lerp(hash(i + seed * 57), hash(i + 1 + seed * 57), smooth(f)) * 2 - 1; }

// Two-bone IK: from root (ax,ay) toward target (tx,ty); bend = +1/-1 chooses the elbow side.
function ik(ax, ay, tx, ty, l1, l2, bend) {
  let dx = tx - ax, dy = ty - ay, d = Math.hypot(dx, dy);
  const maxd = l1 + l2 - 0.01;
  if (d > maxd) { tx = ax + dx / d * maxd; ty = ay + dy / d * maxd; dx = tx - ax; dy = ty - ay; d = maxd; }
  d = Math.max(d, Math.abs(l1 - l2) + 0.01);
  const a = Math.atan2(dy, dx);
  const cosA = clamp((l1 * l1 + d * d - l2 * l2) / (2 * l1 * d), -1, 1);
  const ang = a + bend * Math.acos(cosA);
  return [ax + Math.cos(ang) * l1, ay + Math.sin(ang) * l1, tx, ty];
}

// Timeline over shots.
class Timeline {
  constructor(film) {
    this.film = film; let t = 0;
    this.shots = film.shots.map((s, i) => { const o = { ...s, index: i, start: t }; t += s.dur; o.end = t; return o; });
    this.duration = t;
  }
  at(t) {
    t = clamp(t, 0, this.duration - 1e-6);
    let lo = 0, hi = this.shots.length - 1;
    while (lo < hi) { const m = (lo + hi + 1) >> 1; if (this.shots[m].start <= t) lo = m; else hi = m - 1; }
    return this.shots[lo];
  }
}

// Colours used across the film.
const C = {
  bg: '#0c0c0f', bg2: '#141519', line: '#4b4f58', lineDim: '#30333a', lineLit: '#8a8478',
  cream: '#ebe5d3', creamShade: '#cfc8b4', ink: '#121214', warm: '#f4c586', warmHot: '#ffd9a0',
  cold: '#6f8fb8', red: '#ff3434', redGlow: 'rgba(255,40,40,0.9)', text: '#f1efe8', blue: '#3d7bf5'
};
