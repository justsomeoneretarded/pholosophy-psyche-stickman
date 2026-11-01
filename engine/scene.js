// Composable scenes: shot.set = "scene" with shot.scene = {base, backdrop, ground, wall, light, elements: [...]}.
// The writer builds any place (a hospital room, a classroom, a beach at dusk, a church, a train platform, a graveyard,
// a living room with a TV, a bar, a stage, a symbolic void with one word on the wall...) from these pieces.
'use strict';

const WALLS = {
  dark: ['#121318', '#0d0e12'], blue: ['#121826', '#0c111b'], green: ['#121a16', '#0c120f'], brown: ['#19140f', '#110e0b'],
  grey: ['#1a1b1f', '#121316'], red: ['#1c1112', '#130b0c'], purple: ['#18121f', '#100c16'], cream: ['#2a2720', '#1d1b16'],
  white: ['#2f3034', '#222327'], teal: ['#10191b', '#0b1213'], black: ['#08080a', '#050506']
};
const GROUNDS = {
  floor: ['#0a0a0d', '#3c3f47'], wood: ['#17120e', '#4a3c2e'], tile: ['#121417', '#3a3f47'], carpet: ['#14101a', '#3a3046'],
  road: ['#0b0b0e', '#3c3f47'], pavement: ['#121316', '#3f424a'], grass: ['#0c130e', '#2f4a36'], sand: ['#2b241a', '#6a5a40'],
  snow: ['#c8ccd4', '#e8ecf2'], water: ['#0a1420', '#2a4a6a'], dirt: ['#17120d', '#3e3226'], stage: ['#1a1410', '#5a4632']
};
const SCENE_ELEMENTS = {};
const el = (name, seat, draw, desk) => { SCENE_ELEMENTS[name] = { seat, draw, desk }; };
const H = (v) => GROUND - v;
function label(ctx, text, x, y, size, color, glow) {
  if (!text) return;
  ctx.font = `${size}px ${FONT_HAND}`; ctx.fillStyle = color; ctx.textAlign = 'center'; ctx.textBaseline = 'middle';
  if (glow) { ctx.shadowColor = color; ctx.shadowBlur = 16; }
  ctx.fillText(String(text).slice(0, 26), x, y); ctx.shadowBlur = 0;
}
const tint = (c, d = '#3d4048') => (typeof c === 'string' && /^#[0-9a-f]{6}$/i.test(c)) ? c : (NAMED[c] || d);
const NAMED = { red: '#b33a3a', blue: '#3b5f9a', green: '#3f7a52', yellow: '#c9a43a', orange: '#c7702e', purple: '#6a4a8a', pink: '#c26a8e',
  white: '#d9d6cc', black: '#1a1a1e', grey: '#5a5e68', brown: '#6a4a32', teal: '#2f7a7a', gold: '#c9a43a', navy: '#24365a', cream: '#d9cfb4' };

// ---------- interior ----------
el('window', 0, (c, e, env, t, x) => windowFrame(c, x - (e.w ? pct(e.w) / 2 : 130), e.y ?? 210, e.w ? pct(e.w) : 260, 240, env, t));
el('door', 0, (c, e, env, t, x) => door(c, x - 75, e.open ?? env.door ?? 0, 150, 380));
el('bed', 58, (c, e, env, t, x) => bed(c, x - pct(e.w || 15), x + pct(e.w || 15)));
el('hospital_bed', 58, (c, e, env, t, x) => {
  bed(c, x - pct(13), x + pct(13));
  line(c, [x - pct(13), H(110), x + pct(10), H(110)], '#6a6e78', 4);
  rr(c, x + pct(16), H(330), 110, 80, 6, '#14161a', '#4a4e57');
  line(c, [x + pct(16) + 10, H(290), x + pct(16) + 30, H(290), x + pct(16) + 40, H(310), x + pct(16) + 52, H(270), x + pct(16) + 64, H(290), x + pct(16) + 100, H(290)], '#3ddc84', 3);
  line(c, [x + pct(16) + 55, H(250), x + pct(16) + 55, GROUND], '#4a4e57', 4);
});
el('sofa', 64, (c, e, env, t, x) => {
  const w = pct(e.w || 12), col = tint(e.color, '#2e3446');
  rr(c, x - w, H(170), w * 2, 110, 18, col, '#4a5060'); rr(c, x - w - 30, H(120), 50, 120, 14, col, '#4a5060'); rr(c, x + w - 20, H(120), 50, 120, 14, col, '#4a5060');
  rr(c, x - w + 10, H(80), w * 2 - 20, 40, 10, col, '#4a5060');
}, null);
el('armchair', 64, (c, e, env, t, x) => {
  const col = tint(e.color, '#3a2e2a');
  rr(c, x - 85, H(200), 170, 140, 22, col, '#5a4a40'); rr(c, x - 105, H(120), 40, 120, 14, col, '#5a4a40'); rr(c, x + 65, H(120), 40, 120, 14, col, '#5a4a40');
});
el('chair', 62, (c, e, env, t, x) => { rr(c, x - 60, H(250), 120, 190, 14, '#1b1c22', '#3d4048'); line(c, [x - 50, H(60), x - 50, GROUND], '#3d4048', 5); line(c, [x + 50, H(60), x + 50, GROUND], '#3d4048', 5); });
el('stool', 62, (c, e, env, t, x) => { rr(c, x - 40, H(66), 80, 14, 6, '#2e2620', '#6a5440'); fillRect(c, x - 5, H(52), 10, 52, '#221c17'); });
el('table', 0, (c, e, env, t, x) => {
  const w = pct(e.w || 9); rr(c, x - w, H(108), w * 2, 18, 6, '#3a2f25', '#7a6248'); fillRect(c, x - 10, H(90), 20, 90, '#2a221b', '#4a3e32', 2);
  if (e.lamp) { line(c, [x, 0, x, H(420)], '#3d4048', 3); c.fillStyle = '#4a3d30'; c.beginPath(); c.moveTo(x - 40, H(380)); c.lineTo(x + 40, H(380)); c.lineTo(x + 16, H(420)); c.lineTo(x - 16, H(420)); c.fill(); pool(c, x, H(370), 460, WARM, .32, .8); }
}, 108);
el('desk', 0, (c, e, env, t, x) => {
  const w = pct(e.w || 10); rr(c, x - w, H(118), w * 2, 18, 4, '#3a3027', '#6a5844'); fillRect(c, x - w + 14, H(100), 30, 100, '#1a1714', '#4a3e32', 2); fillRect(c, x + w - 44, H(100), 30, 100, '#1a1714', '#4a3e32', 2);
  if (e.laptop !== false) { rr(c, x + 20, H(220), 150, 100, 6, '#26282f', '#5a5e68'); if (e.on !== false) pool(c, x + 95, H(200), 300, COLD, .16); }
  if (e.lamp) lamp(c, x - w + 40, H(118), 1, t);
}, 118);
el('counter', 0, (c, e, env, t, x) => {
  const w = pct(e.w || 18); fillRect(c, x - w, H(230), w * 2, 230, '#2a221b', '#6a5440', 3); fillRect(c, x - w - 10, H(244), w * 2 + 20, 16, '#3a2f25', '#7a6248', 2);
  if (e.bottles) for (let i = 0; i < 7; i++) { const bx = x - w + 40 + i * (w * 2 - 80) / 6; rr(c, bx - 9, H(330), 18, 70, 5, ['#2f6e4a', '#7a3a2a', '#9a8a4a', '#3a4a7a'][i % 4], '#111'); }
  label(c, e.label, x, H(300), 34, '#ffcf8a', true);
});
el('shelf', 0, (c, e, env, t, x) => { for (const y of [300, 420]) { fillRect(c, x - 130, y, 260, 10, '#24262c', '#3d4048'); } ITEMS.books(c, x - 40, 300); ITEMS.plant(c, x + 60, 420); });
el('bookshelf', 0, (c, e, env, t, x) => {
  fillRect(c, x - 130, H(520), 260, 520, '#1a1612', '#4a3e32', 3);
  const r = rng(Math.round(x)); for (let s = 0; s < 4; s++) { const y = H(520) + 30 + s * 125; fillRect(c, x - 120, y + 100, 240, 8, '#3a2f25');
    for (let bx = x - 115; bx < x + 110;) { const bw = 14 + r() * 16, bh = 60 + r() * 38; fillRect(c, bx, y + 100 - bh, bw, bh, ['#5a6e8a', '#8a5a4a', '#6a7a5a', '#7a6a8a', '#8a7a4a'][Math.floor(r() * 5)]); bx += bw + 2; } }
});
el('floor_lamp', 0, (c, e, env, t, x) => { line(c, [x, GROUND, x, H(420)], '#54575f', 5); c.fillStyle = '#4a3d30'; c.beginPath(); c.moveTo(x - 50, H(420)); c.lineTo(x + 50, H(420)); c.lineTo(x + 30, H(490)); c.lineTo(x - 30, H(490)); c.fill(); if (e.on !== false) { pool(c, x, H(400), 420, WARM, .35, .9); pool(c, x, GROUND, 300, WARM, .2, .25); } });
el('ceiling_lamp', 0, (c, e, env, t, x) => { line(c, [x, -50, x, 220], '#3d4048', 3); rr(c, x - 45, 220, 90, 30, 10, '#3a3d45'); if (e.on !== false) { pool(c, x, 260, 520, e.color === 'cold' ? COLD : WARM, .35, .9); c.fillStyle = 'rgba(255,230,180,.06)'; c.beginPath(); c.moveTo(x - 40, 250); c.lineTo(x + 40, 250); c.lineTo(x + 360, GROUND); c.lineTo(x - 360, GROUND); c.fill(); } });
el('plant', 0, (c, e, env, t, x) => ITEMS.plant(c, x, GROUND));
el('tv', 0, (c, e, env, t, x) => {
  fillRect(c, x - 150, H(110), 300, 110, '#1a1612', '#4a3e32', 2); rr(c, x - 190, H(360), 380, 230, 8, '#0e0f12', '#4a4e57', 3);
  if (e.on !== false) { const f = .7 + .3 * noise1(t * 3, 4); c.fillStyle = `rgba(110,150,220,${.5 * f})`; c.fillRect(x - 178, H(348), 356, 206); pool(c, x, H(250), 620, COLD, .25 * f); label(c, e.label, x, H(250), 38, '#ffffff'); }
});
el('fridge', 0, (c, e, env, t, x) => { const open = e.open ?? env.fridge ?? 0; fillRect(c, x - 110, H(470), 220, 470, '#1c1d22', '#4a4e57', 3); if (open) { fillRect(c, x - 100, H(460), 200, 450, `rgba(235,240,250,${.95 * open})`); pool(c, x, H(240), 620, WHITE, .3 * open); } else line(c, [x + 84, H(400), x + 84, H(300)], '#6a6e78', 6); });
el('mirror', 0, (c, e, env, t, x) => { rr(c, x - 80, H(560), 160, 300, 70, '#1e2530', '#7d8696', 5); c.fillStyle = 'rgba(200,215,235,.08)'; c.beginPath(); c.moveTo(x - 40, H(520)); c.lineTo(x - 10, H(520)); c.lineTo(x - 50, H(320)); c.fill(); });
el('painting', 0, (c, e, env, t, x) => { rr(c, x - 110, 230, 220, 160, 4, tint(e.color, '#3a4a6a'), '#7a6248', 6); line(c, [x - 90, 360, x - 30, 300, x + 10, 340, x + 90, 270], '#d9cfb4', 3); });
el('photo_frame', 0, (c, e, env, t, x) => { rr(c, x - 60, 300, 120, 90, 4, '#d9cfb4', '#7a6248', 5); label(c, e.label, x, 345, 20, '#3a2f25'); });
el('wall_clock', 0, (c, e, env, t, x) => {
  c.fillStyle = '#e9e5da'; c.beginPath(); c.arc(x, 220, 52, 0, Math.PI * 2); c.fill(); c.strokeStyle = '#3d4048'; c.lineWidth = 5; c.stroke();
  const [hh, mm] = String(env.clock || '03:17').split(':').map(Number); const sp = e.spin ? t * 6 : 0;
  line(c, [x, 220, x + Math.sin((mm / 60) * 6.283 + sp) * 40, 220 - Math.cos((mm / 60) * 6.283 + sp) * 40], '#1a1a1e', 4);
  line(c, [x, 220, x + Math.sin(((hh % 12) / 12) * 6.283 + sp / 12) * 26, 220 - Math.cos(((hh % 12) / 12) * 6.283 + sp / 12) * 26], '#1a1a1e', 6);
});
el('poster', 0, (c, e, env, t, x) => { rr(c, x - 75, 240, 150, 200, 4, tint(e.color, '#16171c'), '#2e3037', 2); label(c, e.label, x, 340, 28, '#e9e1cf'); });
el('whiteboard', 0, (c, e, env, t, x) => { rr(c, x - 260, 200, 520, 280, 6, '#d9dcd8', '#6a6e78', 6); label(c, e.label, x, 330, 46, '#2f4a7a'); });
el('rug', 0, (c, e, env, t, x) => { c.fillStyle = tint(e.color, '#3a2a3a'); c.beginPath(); c.ellipse(x, GROUND + 40, pct(e.w || 18), 34, 0, 0, Math.PI * 2); c.fill(); });
el('candle', 0, (c, e, env, t, x) => { const y = e.on_table ? H(108) : GROUND; fillRect(c, x - 8, y - 40, 16, 40, '#e9e1cf'); const f = 1 + .15 * noise1(t * 9, 3); c.fillStyle = '#ffcf6a'; c.beginPath(); c.ellipse(x, y - 52, 6 * f, 12 * f, 0, 0, Math.PI * 2); c.fill(); pool(c, x, y - 52, 300, WARM, .4 * f); });
el('stairs', 0, (c, e, env, t, x) => { for (let i = 0; i < 6; i++) fillRect(c, x - 200 + i * 60, H(60 + i * 60), 400 - i * 60, 60, '#17181d', '#3d4048', 2); });
el('crib', 0, (c, e, env, t, x) => { fillRect(c, x - 110, H(190), 220, 120, '#1e1e24', '#6a6e78', 3); for (let i = 0; i < 9; i++) line(c, [x - 100 + i * 25, H(190), x - 100 + i * 25, H(70)], '#6a6e78', 3); line(c, [x - 110, H(70), x - 110, GROUND], '#6a6e78', 5); line(c, [x + 110, H(70), x + 110, GROUND], '#6a6e78', 5); });

// ---------- exterior ----------
el('building', 0, (c, e, env, t, x) => {
  const w = pct(e.w || 12), h = e.h || 560, top = H(h); fillRect(c, x - w, top, w * 2, h, '#101116', '#2e3037', 2);
  const r = rng(Math.round(x)); for (let yy = top + 30; yy < GROUND - 60; yy += 70) for (let xx = x - w + 24; xx < x + w - 40; xx += 60) if (r() < (env.time === 'night' ? .4 : .2)) fillRect(c, xx, yy, 30, 40, env.time === 'day' ? '#5d6b7d' : 'rgba(255,200,120,.6)');
});
el('house', 0, (c, e, env, t, x) => {
  fillRect(c, x - 200, H(300), 400, 300, '#15161a', '#3d4048', 3); c.fillStyle = '#1d1e23'; c.beginPath(); c.moveTo(x - 230, H(300)); c.lineTo(x, H(470)); c.lineTo(x + 230, H(300)); c.closePath(); c.fill(); c.strokeStyle = '#3d4048'; c.lineWidth = 3; c.stroke();
  fillRect(c, x - 40, H(170), 80, 170, '#0f1013', '#3d4048', 2); const lit = e.on !== false && env.time !== 'day';
  fillRect(c, x - 160, H(240), 90, 70, lit ? 'rgba(255,200,130,.7)' : '#2a2e36', '#3d4048', 2); fillRect(c, x + 70, H(240), 90, 70, lit ? 'rgba(255,200,130,.7)' : '#2a2e36', '#3d4048', 2);
  if (lit) pool(c, x, H(200), 420, WARM, .18);
});
el('shop', 0, (c, e, env, t, x) => {
  fillRect(c, x - 190, H(420), 380, 420, '#0c0d10', '#3d4048', 3); fillRect(c, x - 170, H(360), 220, 260, 'rgba(255,200,130,.5)', '#3d4048', 2); fillRect(c, x + 70, H(340), 90, 340, '#17181d', '#3d4048', 2);
  pool(c, x - 60, H(230), 360, WARM, .3); label(c, e.label || 'OPEN', x, H(395), 30, tint(e.color, '#ffcf8a'), true);
});
el('tree', 0, (c, e, env, t, x) => { const r = (e.size || 1) * 150; fillRect(c, x - 12, H(300), 24, 300, '#0d0f11'); c.fillStyle = env.time === 'day' ? '#1e3326' : '#0d1210'; const sw = noise1(t * .4, x) * 6; c.beginPath(); c.arc(x + sw, H(340), r, 0, 6.283); c.arc(x - r * .6 + sw, H(290), r * .7, 0, 6.283); c.arc(x + r * .6 + sw, H(300), r * .75, 0, 6.283); c.fill(); });
el('bare_tree', 0, (c, e, env, t, x) => { line(c, [x, GROUND, x, H(340)], '#1a1c20', 16); for (const [dx, dy] of [[-120, -440], [110, -470], [-60, -520], [70, -380]]) line(c, [x, H(300), x + dx, GROUND + dy], '#1a1c20', 6); });
el('streetlamp', 0, (c, e, env, t, x) => { streetLamp(c, x, 260, t, e.on === false ? 0 : 1); if (env.weather === 'rain') reflect(c, x); });
el('bench', 58, (c, e, env, t, x) => bench(c, x - pct(e.w || 9), x + pct(e.w || 9)));
el('fence', 0, (c, e, env, t, x) => { for (let xx = -40; xx < STAGE_W + 40; xx += 34) line(c, [xx, GROUND - 10, xx, GROUND - 120], '#22252b', 3); line(c, [-50, GROUND - 100, STAGE_W + 50, GROUND - 100], '#22252b', 3); });
el('car', 0, (c, e, env, t, x) => { const col = tint(e.color, '#2a3a5a'); rr(c, x - 220, H(140), 440, 90, 26, col, '#5a5e68'); rr(c, x - 130, H(220), 250, 90, 30, col, '#5a5e68'); fillRect(c, x - 110, H(205), 100, 60, '#2a3a4a'); fillRect(c, x + 10, H(205), 90, 60, '#2a3a4a');
  for (const wx of [x - 130, x + 130]) { c.fillStyle = '#0a0a0c'; c.beginPath(); c.arc(wx, H(50), 46, 0, 6.283); c.fill(); }
  if (env.time !== 'day') pool(c, x + 220, H(100), 260, WHITE, .3, .5); });
el('bus', 0, (c, e, env, t, x) => { rr(c, x - 420, H(380), 840, 340, 20, '#2f5f8a', '#a9c4f2', 3); for (let i = 0; i < 6; i++) fillRect(c, x - 390 + i * 130, H(340), 110, 120, env.time === 'day' ? '#9ab' : 'rgba(255,230,190,.6)', '#1a2a3a', 2);
  for (const wx of [x - 280, x + 280]) { c.fillStyle = '#0a0a0c'; c.beginPath(); c.arc(wx, H(40), 50, 0, 6.283); c.fill(); } label(c, e.label, x, H(195), 30, '#ffffff'); });
el('traffic_light', 0, (c, e, env, t, x) => { line(c, [x, GROUND, x, H(420)], '#3f424a', 8); rr(c, x - 28, H(560), 56, 150, 10, '#16171b', '#3d4048'); const s = e.state || 'red';
  [['red', '#ff3b30', 520], ['amber', '#ffb020', 485], ['green', '#3ddc84', 450]].forEach(([k, col, y]) => { c.fillStyle = s === k ? col : '#2a2c32'; c.beginPath(); c.arc(x, H(y), 16, 0, 6.283); c.fill(); if (s === k) pool(c, x, H(y), 120, { red: REDL, amber: WARM, green: 'rgba(80,230,140,A)' }[k], .35); }); });
el('sign', 0, (c, e, env, t, x) => { line(c, [x, GROUND, x, H(330)], '#3f424a', 8); rr(c, x - 110, H(400), 220, 80, 8, tint(e.color, '#2f6e4a'), '#d9d6cc', 3); label(c, e.label || 'EXIT', x, H(360), 30, '#ffffff'); });
el('moon', 0, (c, e, env, t, x) => { c.fillStyle = '#e9e5da'; c.beginPath(); c.arc(x, e.y ?? 160, 46, 0, 6.283); c.fill(); pool(c, x, e.y ?? 160, 260, WHITE, .2); });
el('sun', 0, (c, e, env, t, x) => { pool(c, x, e.y ?? GROUND - 200, 700, 'rgba(255,150,80,A)', .55, .7); c.fillStyle = '#ffb35a'; c.beginPath(); c.arc(x, e.y ?? GROUND - 200, 90, 0, 6.283); c.fill(); });
el('clouds', 0, (c, e, env, t, x) => { c.fillStyle = env.time === 'day' ? 'rgba(220,226,235,.5)' : 'rgba(90,96,110,.35)'; for (let i = 0; i < 4; i++) { const cx = ((x + i * 520 + t * 12) % (STAGE_W + 400)) - 200, cy = 120 + (i % 2) * 70; c.beginPath(); c.ellipse(cx, cy, 160, 40, 0, 0, 6.283); c.ellipse(cx + 80, cy - 20, 90, 36, 0, 0, 6.283); c.fill(); } });
el('gravestone', 0, (c, e, env, t, x) => { rr(c, x - 60, H(170), 120, 170, 50, '#2a2c32', '#5a5e68', 3); label(c, e.label, x, H(110), 22, '#b8bcc6'); });
el('flowers', 0, (c, e, env, t, x) => { for (let i = 0; i < 7; i++) { const fx = x - 60 + i * 20; line(c, [fx, GROUND, fx + noise1(t + i, 2) * 4, H(50 + (i % 3) * 14)], '#2f5a3a', 3); c.fillStyle = tint(e.color, ['#e07a8a', '#e9c94a', '#d9d6ff'][i % 3]); c.beginPath(); c.arc(fx, H(54 + (i % 3) * 14), 8, 0, 6.283); c.fill(); } });
el('campfire', 0, (c, e, env, t, x) => { for (let i = 0; i < 3; i++) line(c, [x - 50 + i * 10, GROUND, x + 50 - i * 10, H(24)], '#3a2a1e', 10); for (let i = 0; i < 4; i++) { const f = .7 + .3 * noise1(t * 6 + i, i); c.fillStyle = ['#ff7a2a', '#ffb02a', '#ffd76a', '#ff5a2a'][i]; c.beginPath(); c.ellipse(x + (i - 1.5) * 12, H(40 + 30 * f), 16 * f, 44 * f, 0, 0, 6.283); c.fill(); } pool(c, x, H(60), 600, WARM, .45); });
el('rock', 60, (c, e, env, t, x) => { c.fillStyle = '#25272c'; c.beginPath(); c.moveTo(x - 110, GROUND); c.lineTo(x - 90, H(50)); c.lineTo(x - 20, H(66)); c.lineTo(x + 70, H(58)); c.lineTo(x + 110, GROUND); c.fill(); });
el('swing', 64, (c, e, env, t, x) => { line(c, [x - 160, GROUND, x - 120, H(560), x + 120, H(560), x + 160, GROUND], '#3f424a', 8); line(c, [x - 50, H(560), x - 50, H(70)], '#6a6e78', 3); line(c, [x + 50, H(560), x + 50, H(70)], '#6a6e78', 3); rr(c, x - 60, H(72), 120, 12, 4, '#4a3c2e'); });
el('boat', 0, (c, e, env, t, x) => { const b = Math.sin(t * 1.4) * 6; c.fillStyle = '#3a2a1e'; c.beginPath(); c.moveTo(x - 200, H(70) + b); c.lineTo(x + 200, H(70) + b); c.lineTo(x + 150, GROUND + b); c.lineTo(x - 150, GROUND + b); c.fill(); });
el('ledge', 104, (c, e, env, t, x) => { fillRect(c, -50, H(104), STAGE_W + 100, 104, '#121317', '#4a4e57', 3); });

// ---------- symbolic ----------
el('spotlight', 0, (c, e, env, t, x) => { c.fillStyle = `rgba(255,240,215,${e.strong ? .12 : .07})`; c.beginPath(); c.moveTo(x - 40, -50); c.lineTo(x + 40, -50); c.lineTo(x + 300, GROUND); c.lineTo(x - 300, GROUND); c.fill(); pool(c, x, GROUND, 400, WHITE, .2, .18); });
el('word', 0, (c, e, env, t, x) => { const s = e.size || 110; c.font = `bold ${s}px ${FONT_UI}`; c.textAlign = 'center'; c.textBaseline = 'middle'; c.fillStyle = tint(e.color, '#2a2c33'); c.fillText(String(e.label || '').slice(0, 18).toUpperCase(), x, e.y ?? 320); });
el('light_door', 0, (c, e, env, t, x) => { pool(c, x, H(200), 700, WARM, .35); fillRect(c, x - 80, H(400), 160, 400, 'rgba(255,224,170,.95)'); c.fillStyle = 'rgba(255,214,160,.16)'; c.beginPath(); c.moveTo(x - 80, GROUND); c.lineTo(x + 80, GROUND); c.lineTo(x + 380, STAGE_H); c.lineTo(x - 380, STAGE_H); c.fill(); });
el('crowd', 0, (c, e, env, t, x) => { const n = e.count || 9, w = pct(e.w || 30), r = rng(Math.round(x));
  for (let i = 0; i < n; i++) { const cx = x - w + (i + .5) * (2 * w / n) + (r() - .5) * 20, s = .55 + r() * .15, by = GROUND - 30 + Math.sin(t * 2 + i) * 2;
    c.fillStyle = e.color ? tint(e.color) : '#2a2c33'; rr(c, cx - 34 * s, by - 230 * s, 68 * s, 150 * s, 30 * s, c.fillStyle); c.beginPath(); c.arc(cx, by - 268 * s, 44 * s, 0, 6.283); c.fill(); fillRect(c, cx - 22 * s, by - 90 * s, 14 * s, 90 * s, c.fillStyle); fillRect(c, cx + 8 * s, by - 90 * s, 14 * s, 90 * s, c.fillStyle); } });
el('screen_glow', 0, (c, e, env, t, x) => pool(c, x, H(260), 520, e.color === 'warm' ? WARM : COLD, .3 * (.8 + .2 * noise1(t * 4, 1))));

// ---------- backdrops ----------
function drawBackdrop(c, sc, env, t) {
  const b = sc.backdrop || 'none';
  if (b === 'city') { skyline(c, -60, STAGE_W + 60, GROUND - 40, 37, env, t, 420, .26); if (env.time === 'night') bokeh(c, 13, t, 200, 560, 18); }
  else if (b === 'hills') { c.fillStyle = env.time === 'day' ? '#2b3a32' : '#0e1311'; c.beginPath(); c.moveTo(-50, GROUND); for (let x = -50; x <= STAGE_W + 50; x += 30) c.lineTo(x, GROUND - 180 - 90 * Math.sin(x / 300)); c.lineTo(STAGE_W + 50, GROUND); c.fill(); }
  else if (b === 'mountains') { c.fillStyle = env.time === 'day' ? '#3a4656' : '#12161e'; c.beginPath(); c.moveTo(-50, GROUND); [[0, 520], [320, 260], [640, 470], [980, 200], [1320, 430], [1650, 280], [1970, 520]].forEach(([x, y]) => c.lineTo(x, y)); c.lineTo(STAGE_W + 50, GROUND); c.fill(); }
  else if (b === 'sea') { const g = c.createLinearGradient(0, GROUND - 260, 0, GROUND); g.addColorStop(0, env.time === 'day' ? '#4a6a8a' : '#0d1624'); g.addColorStop(1, env.time === 'day' ? '#2a4a6a' : '#08101a'); c.fillStyle = g; c.fillRect(-50, GROUND - 260, STAGE_W + 100, 260);
    for (let i = 0; i < 9; i++) line(c, [(i * 240 + t * 20) % 2100 - 100, GROUND - 230 + i * 26, (i * 240 + t * 20) % 2100 + 40, GROUND - 230 + i * 26], 'rgba(220,230,245,.18)', 2); }
  else if (b === 'forest') { for (let i = 0; i < 14; i++) { const x = i * 150 + 20, h = 380 + (i % 3) * 90; c.fillStyle = '#0b100d'; c.beginPath(); c.moveTo(x, GROUND - h); c.lineTo(x - 90, GROUND); c.lineTo(x + 90, GROUND); c.fill(); } }
  else if (b === 'desert') { c.fillStyle = '#3a2e20'; c.beginPath(); c.moveTo(-50, GROUND); for (let x = -50; x <= STAGE_W + 50; x += 40) c.lineTo(x, GROUND - 80 - 50 * Math.sin(x / 220)); c.lineTo(STAGE_W + 50, GROUND); c.fill(); }
  else if (b === 'stars') { const r = rng(5); for (let i = 0; i < 120; i++) { c.fillStyle = `rgba(230,235,245,${.3 + .5 * r()})`; c.fillRect(r() * STAGE_W, r() * (GROUND - 200), 2, 2); } }
}

const SCENE_CACHE = new Map();
function sceneSet(shot) {
  const sc = shot.scene || {};
  const key = JSON.stringify(sc);
  if (SCENE_CACHE.has(key)) return SCENE_CACHE.get(key);
  const els = (sc.elements || []).filter(e => SCENE_ELEMENTS[e.type]);
  const outdoor = ['outside', 'nature'].includes(sc.base);
  const spans = (type) => ({ bed: 15, sofa: 12, bench: 9, table: 9, desk: 10, ledge: 60 }[type] || 5);
  const set = {
    outdoor,
    seatFront: ['#2a2c32', '#5a5e68'],
    seat: x => { for (const e of els) { const d = SCENE_ELEMENTS[e.type]; if (d.seat && Math.abs(x - pct(e.x ?? 50)) < pct(e.w || spans(e.type))) return d.seat; } return 0; },
    desk: x => { for (const e of els) { const d = SCENE_ELEMENTS[e.type]; if (d.desk && Math.abs(x - pct(e.x ?? 50)) < pct(e.w || spans(e.type))) return d.desk; } return 0; },
    draw(c, env, t) {
      const base = sc.base || 'room';
      if (base === 'void' || base === 'stage') {
        c.fillStyle = base === 'stage' ? '#0b0806' : (WALLS[sc.wall] || WALLS.black)[1]; c.fillRect(-50, -50, STAGE_W + 100, STAGE_H + 100);
        if (base === 'stage') { for (const s of [-1, 1]) { c.fillStyle = '#4a1418'; c.beginPath(); c.moveTo(s < 0 ? -50 : STAGE_W + 50, -50); c.lineTo(s < 0 ? 260 : STAGE_W - 260, -50); c.quadraticCurveTo(s < 0 ? 200 : STAGE_W - 200, 500, s < 0 ? 120 : STAGE_W - 120, GROUND); c.lineTo(s < 0 ? -50 : STAGE_W + 50, GROUND); c.fill(); }
          fillRect(c, -50, GROUND, STAGE_W + 100, 300, GROUNDS.stage[0]); line(c, [-50, GROUND, STAGE_W + 50, GROUND], GROUNDS.stage[1], 3); }
        else { fillRect(c, -50, GROUND, STAGE_W + 100, 300, '#050506'); }
      } else if (outdoor) {
        sky(c, env, -50, -50, STAGE_W + 100, GROUND + 50);
        if (sc.backdrop === 'stars' || (env.time === 'night' && !sc.backdrop)) drawBackdrop(c, { backdrop: 'stars' }, env, t);
        drawBackdrop(c, sc, env, t);
        const g = GROUNDS[sc.ground] || GROUNDS[base === 'nature' ? 'grass' : 'road'];
        fillRect(c, -50, GROUND, STAGE_W + 100, 300, g[0]); line(c, [-50, GROUND, STAGE_W + 50, GROUND], g[1], 3);
        if (sc.ground === 'road') for (let x = 40; x < STAGE_W; x += 220) line(c, [x, GROUND + 140, x + 110, GROUND + 140], '#2e3036', 4);
      } else {
        const w = WALLS[sc.wall] || WALLS.dark; room(c, env, w[0], w[1]);
        const g = GROUNDS[sc.ground]; if (g) { fillRect(c, -50, GROUND, STAGE_W + 100, 300, g[0]); line(c, [-50, GROUND, STAGE_W + 50, GROUND], g[1], 2.6);
          if (sc.ground === 'wood') for (let i = 1; i < 5; i++) line(c, [-50, GROUND + i * 40, STAGE_W + 50, GROUND + i * 40], 'rgba(90,70,50,.25)', 2); }
      }
      const lt = sc.light; if (lt === 'warm') pool(c, pct(50), 300, 1100, WARM, .16); else if (lt === 'cold') pool(c, pct(50), 300, 1100, COLD, .16);
      else if (lt === 'red') pool(c, pct(50), 400, 1100, REDL, .14); else if (lt === 'bright') { c.fillStyle = 'rgba(200,205,215,.10)'; c.fillRect(-50, -50, STAGE_W + 100, STAGE_H + 100); }
      for (const e of els) { if (e.front) continue; const x = pct(e.x ?? 50); try { SCENE_ELEMENTS[e.type].draw(c, e, env, t, x); } catch (err) { /* a bad element never stops a film */ } }
      if (outdoor) weatherIn(c, env, t, -50, -50, STAGE_W + 100, STAGE_H + 100);
      if (lt === 'dim') { c.fillStyle = 'rgba(0,0,0,.35)'; c.fillRect(-50, -50, STAGE_W + 100, STAGE_H + 100); }
    },
    fg(c, env, t) { for (const e of els) if (e.front) { try { SCENE_ELEMENTS[e.type].draw(c, e, env, t, pct(e.x ?? 50)); } catch (err) { /* ignore */ } } }
  };
  SCENE_CACHE.set(key, set);
  return set;
}

// Every place a shot can be: a named set or a composed scene.
function setFor(shot) { return shot.set === 'scene' ? sceneSet(shot) : (SETS[shot.set] || SETS.void); }
