// Sets: dark line-art rooms and streets with pools of light. All in stage coordinates (1920x1080).
'use strict';

const SKY = {
  night: ['#0a0d16', '#151b2c'], dawn: ['#2a2033', '#c9744a'], day: ['#3e4b5e', '#7f8fa3'], dusk: ['#1d1830', '#8a4f5c']
};
const AMBIENT = { night: 0, dawn: .05, day: .13, dusk: .04 };

function fillRect(ctx, x, y, w, h, fill, stroke, lw = 2.4) {
  ctx.fillStyle = fill; ctx.fillRect(x, y, w, h);
  if (stroke) { ctx.strokeStyle = stroke; ctx.lineWidth = lw; ctx.strokeRect(x, y, w, h); }
}
function rr(ctx, x, y, w, h, r, fill, stroke, lw = 2.4) {
  roundRect(ctx, x, y, w, h, r);
  if (fill) { ctx.fillStyle = fill; ctx.fill(); }
  if (stroke) { ctx.strokeStyle = stroke; ctx.lineWidth = lw; ctx.stroke(); }
}
function line(ctx, pts, color, lw = 2.4) {
  ctx.strokeStyle = color; ctx.lineWidth = lw; ctx.lineCap = 'round'; ctx.lineJoin = 'round';
  ctx.beginPath(); ctx.moveTo(pts[0], pts[1]); for (let i = 2; i < pts.length; i += 2) ctx.lineTo(pts[i], pts[i + 1]); ctx.stroke();
}
function pool(ctx, x, y, r, color, alpha, sy = 1) {
  ctx.save(); ctx.translate(x, y); ctx.scale(1, sy);
  const g = ctx.createRadialGradient(0, 0, 0, 0, 0, r);
  g.addColorStop(0, color.replace('A', alpha)); g.addColorStop(.45, color.replace('A', alpha * .45)); g.addColorStop(1, color.replace('A', 0));
  ctx.fillStyle = g; ctx.beginPath(); ctx.arc(0, 0, r, 0, Math.PI * 2); ctx.fill(); ctx.restore();
}
const WARM = 'rgba(255,190,120,A)', COLD = 'rgba(120,160,230,A)', REDL = 'rgba(255,60,60,A)', WHITE = 'rgba(255,245,225,A)';

function room(ctx, env, wallTop = '#121318', wallBot = '#0d0e12') {
  const g = ctx.createLinearGradient(0, 0, 0, GROUND);
  g.addColorStop(0, wallTop); g.addColorStop(1, wallBot);
  ctx.fillStyle = g; ctx.fillRect(-50, -50, STAGE_W + 100, GROUND + 50);
  ctx.fillStyle = '#0a0a0d'; ctx.fillRect(-50, GROUND, STAGE_W + 100, STAGE_H - GROUND + 50);
  line(ctx, [-50, GROUND, STAGE_W + 50, GROUND], '#3c3f47', 2.6);
  if (AMBIENT[env.time]) { ctx.fillStyle = `rgba(150,160,190,${AMBIENT[env.time] * .6})`; ctx.fillRect(-50, -50, STAGE_W + 100, STAGE_H + 100); }
}

function skyline(ctx, x0, x1, base, seed, env, t, height = 300, lit = .28) {
  const r = rng(seed); let x = x0;
  const dark = env.time === 'day' ? '#4a5466' : '#0e1119';
  const edge = env.time === 'day' ? '#5b6577' : '#1a1e2a';
  while (x < x1) {
    const w = 60 + r() * 110, h = height * (.35 + r() * .65);
    fillRect(ctx, x, base - h, w, h, dark, edge, 1.5);
    for (let yy = base - h + 16; yy < base - 14; yy += 26) for (let xx = x + 10; xx < x + w - 14; xx += 22) {
      const on = r() < lit;
      if (on) { const fl = .7 + .3 * noise1(t * .3 + xx * .01, yy); ctx.fillStyle = `rgba(255,200,120,${.55 * fl})`; ctx.fillRect(xx, yy, 9, 12); }
    }
    x += w + 4;
  }
}

function sky(ctx, env, x, y, w, h) {
  const [a, b] = SKY[env.time] || SKY.night;
  const g = ctx.createLinearGradient(0, y, 0, y + h); g.addColorStop(0, a); g.addColorStop(1, b);
  ctx.fillStyle = g; ctx.fillRect(x, y, w, h);
  if (env.time === 'night') { ctx.fillStyle = '#d8dde6'; ctx.beginPath(); ctx.arc(x + w * .78, y + h * .22, 14, 0, Math.PI * 2); ctx.fill(); pool(ctx, x + w * .78, y + h * .22, 70, WHITE, .12); }
}

function windowFrame(ctx, x, y, w, h, env, t) {
  ctx.save(); ctx.beginPath(); ctx.rect(x, y, w, h); ctx.clip();
  sky(ctx, env, x, y, w, h);
  skyline(ctx, x - 20, x + w + 20, y + h + 4, 11 + Math.round(x), env, t, h * .7);
  weatherIn(ctx, env, t, x, y, w, h, .7, true);
  ctx.restore();
  rr(ctx, x - 8, y - 8, w + 16, h + 16, 4, null, '#4a4e57', 4);
  line(ctx, [x + w / 2, y, x + w / 2, y + h], '#4a4e57', 4);
  line(ctx, [x, y + h / 2, x + w, y + h / 2], '#4a4e57', 4);
  fillRect(ctx, x - 22, y + h + 8, w + 44, 10, '#22242a', '#3d4048', 2);
  pool(ctx, x + w / 2, y + h / 2, w * .9, env.time === 'night' ? COLD : WHITE, env.time === 'night' ? .07 : .12);
}

function weatherIn(ctx, env, t, x, y, w, h, a = 1, glass = false) {
  if (env.weather === 'rain') {
    const n = Math.floor(w * h / 4200);
    for (let i = 0; i < n; i++) {
      const sp = 1100 + hash(i + 7) * 500, len = 18 + hash(i + 3) * 26;
      const rx = x + ((hash(i) * w + t * 140) % w), ry = y + ((hash(i + 99) * h + t * sp) % h);
      ctx.strokeStyle = `rgba(185,205,235,${(.18 + hash(i + 11) * .3) * a})`; ctx.lineWidth = .8 + hash(i + 13) * 1.4;
      ctx.beginPath(); ctx.moveTo(rx, ry); ctx.lineTo(rx - len * .22, ry + len); ctx.stroke();
    }
    if (glass) {
      // drops sliding down the window glass
      for (let i = 0; i < Math.floor(w * h / 2600); i++) {
        const dx = x + hash(i + 400) * w, dy = y + ((hash(i + 401) * h + t * (8 + hash(i + 402) * 30) * (hash(i + 403) > .8 ? 4 : .2)) % h), r = 1.5 + hash(i + 404) * 3;
        ctx.fillStyle = `rgba(200,215,240,${.35 * a})`; ctx.beginPath(); ctx.ellipse(dx, dy, r, r * 1.3, 0, 0, Math.PI * 2); ctx.fill();
        ctx.fillStyle = `rgba(255,255,255,${.4 * a})`; ctx.beginPath(); ctx.arc(dx - r * .3, dy - r * .4, r * .35, 0, Math.PI * 2); ctx.fill();
      }
    }
  } else if (env.weather === 'snow') {
    for (let i = 0; i < Math.floor(w * h / 3500); i++) {
      const rx = x + ((hash(i) * w + Math.sin(t * .8 + i) * 20 + t * 40) % w + w) % w, ry = y + ((hash(i + 5) * h + t * (60 + hash(i + 3) * 70)) % h);
      ctx.fillStyle = `rgba(235,240,250,${(.45 + hash(i + 2) * .45) * a})`;
      ctx.beginPath(); ctx.arc(rx, ry, 1.5 + hash(i + 1) * 2.2, 0, Math.PI * 2); ctx.fill();
    }
  }
}

// Foreground rain for outdoor sets: streaks in front of the characters and splashes on the ground.
function rainFront(ctx, t) {
  for (let i = 0; i < 70; i++) {
    const sp = 1500 + hash(i + 70) * 600, len = 34 + hash(i + 71) * 30;
    const rx = ((hash(i + 72) * 2100 + t * 180) % 2100) - 90, ry = ((hash(i + 73) * 1200 + t * sp) % 1200) - 60;
    ctx.strokeStyle = `rgba(200,215,240,${.12 + hash(i + 74) * .18})`; ctx.lineWidth = 1.4 + hash(i + 75) * 1.6;
    ctx.beginPath(); ctx.moveTo(rx, ry); ctx.lineTo(rx - len * .22, ry + len); ctx.stroke();
  }
  for (let i = 0; i < 26; i++) {
    const period = .5 + hash(i + 90) * .5, ph = ((t + hash(i + 91) * 3) % period) / period;
    const sx = hash(i + 92 + Math.floor((t + hash(i + 91) * 3) / period) * 7) * 1920, sy = GROUND + 6 + hash(i + 93) * 120;
    ctx.strokeStyle = `rgba(210,225,245,${.5 * (1 - ph)})`; ctx.lineWidth = 1.6;
    ctx.beginPath(); ctx.ellipse(sx, sy, 6 + ph * 22, 2 + ph * 5, 0, Math.PI, 0); ctx.stroke();
  }
}

// Wet-ground reflection of a light: a soft vertical streak below it.
function reflect(ctx, x, color = 'rgba(255,205,140,A)', a = .22, w = 70) {
  // a soft, rippling streak on the wet ground below a light
  for (let i = 0; i < 6; i++) {
    const y = GROUND + 8 + i * 26, ww = w * (1 - i * .1), al = a * (1 - i / 6);
    const g = ctx.createRadialGradient(x, y, 0, x, y, ww / 2);
    g.addColorStop(0, color.replace('A', al)); g.addColorStop(1, color.replace('A', 0));
    ctx.fillStyle = g; ctx.beginPath(); ctx.ellipse(x, y, ww / 2, 9, 0, 0, Math.PI * 2); ctx.fill();
  }
}

// Out-of-focus city lights; on close shots the depth blur turns them into bokeh.
function bokeh(ctx, seed, t, y0 = 120, y1 = 620, n = 26, color = '255,196,120') {
  const r = rng(seed);
  for (let i = 0; i < n; i++) {
    const x = r() * STAGE_W, y = y0 + r() * (y1 - y0), s = 8 + r() * 18, fl = .55 + .45 * noise1(t * .5 + i, seed);
    ctx.fillStyle = `rgba(${color},${.35 * fl})`; ctx.fillRect(x - s / 2, y - s / 2, s, s);
  }
}

function door(ctx, x, open, w = 150, h = 380) {
  const y = GROUND - h;
  if (open > 0) {
    ctx.fillStyle = `rgba(255,214,160,${.9 * open})`; ctx.fillRect(x, y, w, h);
    pool(ctx, x + w / 2, GROUND - h * .4, 420, WARM, .32 * open);
    ctx.fillStyle = `rgba(255,200,140,${.18 * open})`;
    ctx.beginPath(); ctx.moveTo(x, GROUND); ctx.lineTo(x + w, GROUND); ctx.lineTo(x + w + 260, STAGE_H); ctx.lineTo(x - 260, STAGE_H); ctx.fill();
  }
  const dw = w * (1 - open * .82);
  fillRect(ctx, x, y, dw, h, '#17181d', '#4a4e57', 3);
  ctx.fillStyle = '#7d7f86'; ctx.beginPath(); ctx.arc(x + dw - 18, y + h * .52, 6, 0, Math.PI * 2); ctx.fill();
  rr(ctx, x - 10, y - 10, w + 20, h + 10, 2, null, '#32353c', 3);
}

function lamp(ctx, x, y, on = 1, t = 0) {
  line(ctx, [x, y, x, y - 90, x + 50, y - 140], '#54575f', 5);
  ctx.fillStyle = '#3d4048'; ctx.beginPath(); ctx.moveTo(x + 30, y - 160); ctx.lineTo(x + 95, y - 130); ctx.lineTo(x + 70, y - 108); ctx.closePath(); ctx.fill();
  fillRect(ctx, x - 26, y - 6, 52, 8, '#3d4048');
  if (on) { pool(ctx, x + 80, y - 110, 420, WARM, .38 * on, .8); pool(ctx, x + 90, y + 4, 300, WARM, .25 * on, .25); }
}

function clockBox(ctx, x, y, text) {
  rr(ctx, x, y, 130, 82, 8, '#141519', '#3d4048', 2.4);
  ctx.font = `bold 40px ${FONT_DIGIT}`; ctx.fillStyle = '#ff3b30'; ctx.textAlign = 'center'; ctx.textBaseline = 'middle';
  ctx.shadowColor = 'rgba(255,40,30,.8)'; ctx.shadowBlur = 14; ctx.fillText(text, x + 65, y + 42); ctx.shadowBlur = 0;
}

function bed(ctx, x0, x1) {
  const top = GROUND - 62;
  rr(ctx, x0 - 22, GROUND - 190, 26, 190, 6, '#1a1b20', '#3d4048');
  fillRect(ctx, x0, top + 22, x1 - x0, 26, '#16171c', '#3d4048');
  rr(ctx, x0 + 4, top - 4, x1 - x0 - 8, 30, 12, '#2a2e3a', '#4a4f5c');
  rr(ctx, x0 + 14, top - 30, 150, 32, 16, '#3a3f4c', '#525868');
  fillRect(ctx, x0 + 20, GROUND - 14, 12, 14, '#2a2c32'); fillRect(ctx, x1 - 32, GROUND - 14, 12, 14, '#2a2c32');
}

function bench(ctx, x0, x1, y = GROUND) {
  const seat = y - 62;
  for (let i = 0; i < 3; i++) rr(ctx, x0, seat - 150 + i * 40, x1 - x0, 24, 6, '#2a2520', '#5a4c3e');
  rr(ctx, x0 - 10, seat - 6, x1 - x0 + 20, 22, 6, '#2e2822', '#66563f');
  for (const x of [x0 + 30, x1 - 44]) fillRect(ctx, x, seat + 14, 14, y - seat - 14, '#1d1d20', '#3e3f44');
}

function streetLamp(ctx, x, top = 260, t = 0, on = 1) {
  line(ctx, [x, GROUND, x, top], '#3f424a', 7);
  rr(ctx, x - 26, top - 18, 52, 22, 8, '#3a3d45');
  const fl = .92 + .08 * noise1(t * 3, x);
  pool(ctx, x, top + 10, 120, WHITE, .55 * on * fl);
  ctx.fillStyle = `rgba(255,220,170,${.13 * on * fl})`; ctx.beginPath(); ctx.moveTo(x - 20, top); ctx.lineTo(x + 20, top); ctx.lineTo(x + 230, GROUND); ctx.lineTo(x - 230, GROUND); ctx.fill();
  pool(ctx, x, GROUND, 260, WARM, .28 * on * fl, .22);
}

// ---------- Items ----------
const ITEMS = {
  pizza_box(ctx, x, y, t) { rr(ctx, x - 70, y - 26, 140, 26, 4, '#d9c08f', '#8f7650'); rr(ctx, x - 70, y - 98, 140, 70, 4, '#cfb486', '#8f7650'); ctx.fillStyle = '#e3a03a'; ctx.beginPath(); ctx.ellipse(x, y - 26, 58, 10, 0, Math.PI, 0); ctx.fill(); },
  cupcake(ctx, x, y, t) {
    ctx.fillStyle = '#c96d8a'; ctx.beginPath(); ctx.moveTo(x - 22, y - 30); ctx.lineTo(x + 22, y - 30); ctx.lineTo(x + 16, y); ctx.lineTo(x - 16, y); ctx.fill();
    ctx.fillStyle = '#f2b6c8'; ctx.beginPath(); ctx.ellipse(x, y - 34, 26, 16, 0, 0, Math.PI * 2); ctx.fill();
    fillRect(ctx, x - 2, y - 66, 4, 22, '#eaeaea');
    const f = 1 + .15 * Math.sin(t * 13) + .1 * noise1(t * 5, 3);
    ctx.fillStyle = '#ffcc55'; ctx.beginPath(); ctx.ellipse(x, y - 74, 5 * f, 9 * f, 0, 0, Math.PI * 2); ctx.fill();
    pool(ctx, x, y - 74, 240, WARM, .4 * f);
  },
  cans(ctx, x, y) { for (let i = 0; i < 4; i++) rr(ctx, x - 40 + i * 22 + (i % 2) * 4, y - 40 + (i % 2) * 6, 18, 40 - (i % 2) * 6, 3, ['#3f9a5a', '#c8383b', '#3b6fc4', '#d9a92e'][i], '#222'); },
  laundry(ctx, x, y) { ctx.fillStyle = '#4b5263'; ctx.beginPath(); ctx.ellipse(x, y - 22, 80, 28, 0, Math.PI, 0); ctx.fill(); ctx.fillStyle = '#6a5a7a'; ctx.beginPath(); ctx.ellipse(x + 20, y - 30, 40, 18, .3, 0, Math.PI * 2); ctx.fill(); ctx.fillStyle = '#3a5f6e'; ctx.beginPath(); ctx.ellipse(x - 30, y - 18, 36, 14, -.2, 0, Math.PI * 2); ctx.fill(); },
  books(ctx, x, y) { const c = ['#5a6e8a', '#8a5a4a', '#6a7a5a', '#7a6a8a']; for (let i = 0; i < 4; i++) rr(ctx, x - 55 + (i % 2) * 8, y - 22 * (i + 1), 110 - i * 6, 20, 3, c[i], '#222'); },
  trophy(ctx, x, y) { ctx.fillStyle = '#d9a92e'; ctx.beginPath(); ctx.moveTo(x - 26, y - 90); ctx.lineTo(x + 26, y - 90); ctx.quadraticCurveTo(x + 22, y - 50, x, y - 46); ctx.quadraticCurveTo(x - 22, y - 50, x - 26, y - 90); ctx.fill(); fillRect(ctx, x - 5, y - 46, 10, 26, '#b88a1e'); fillRect(ctx, x - 24, y - 22, 48, 22, '#3d4048'); pool(ctx, x, y - 70, 120, WARM, .25); },
  sketchbook(ctx, x, y) { rr(ctx, x - 60, y - 10, 120, 10, 2, '#2c2c34', '#555'); rr(ctx, x - 56, y - 16, 112, 8, 2, '#efe9db'); },
  plant(ctx, x, y) { rr(ctx, x - 26, y - 50, 52, 50, 6, '#5b4335', '#2a1f18'); ctx.fillStyle = '#2f5e45'; for (let i = 0; i < 6; i++) { ctx.beginPath(); ctx.ellipse(x + (i - 2.5) * 12, y - 80 - (i % 2) * 14, 10, 34, (i - 2.5) * .3, 0, Math.PI * 2); ctx.fill(); } },
  gift(ctx, x, y) { rr(ctx, x - 34, y - 56, 68, 56, 4, '#3b6fc4', '#1f3a6a'); fillRect(ctx, x - 6, y - 56, 12, 56, '#e9d26a'); fillRect(ctx, x - 34, y - 34, 68, 10, '#e9d26a'); },
  dumbbell(ctx, x, y) { fillRect(ctx, x - 40, y - 14, 80, 8, '#888'); rr(ctx, x - 50, y - 26, 18, 26, 3, '#2b2d33', '#555'); rr(ctx, x + 32, y - 26, 18, 26, 3, '#2b2d33', '#555'); },
  trash_bag(ctx, x, y) { ctx.fillStyle = '#1e2024'; ctx.beginPath(); ctx.ellipse(x, y - 40, 50, 42, 0, 0, Math.PI * 2); ctx.fill(); ctx.strokeStyle = '#3d4048'; ctx.lineWidth = 2; ctx.stroke(); },
  guitar(ctx, x, y) { ctx.fillStyle = '#8a5a35'; ctx.beginPath(); ctx.ellipse(x, y - 50, 34, 44, 0, 0, Math.PI * 2); ctx.fill(); ctx.beginPath(); ctx.ellipse(x, y - 108, 26, 30, 0, 0, Math.PI * 2); ctx.fill(); fillRect(ctx, x - 5, y - 250, 10, 120, '#3a2a1e'); ctx.fillStyle = '#111'; ctx.beginPath(); ctx.arc(x, y - 92, 10, 0, Math.PI * 2); ctx.fill(); }
};

// ---------- Sets ----------
// Each set: draw(ctx, env, t), seat(xStage) -> seat height or 0, ground(xStage) -> y.
const flatGround = () => GROUND;
const SETS = {
  bedroom: {
    seatFront: ['#2a2e3a', '#4a4f5c'],
    seat: x => (x > pct(34) && x < pct(64)) ? 58 : 0,
    
    draw(ctx, env, t) {
      room(ctx, env);
      windowFrame(ctx, pct(74), 200, 260, 250, env, t);
      door(ctx, pct(5), env.door || 0);
      // poster
      rr(ctx, pct(44), 240, 150, 200, 4, '#16171c', '#2e3037', 2);
      bed(ctx, pct(34), pct(64));
      // nightstand + clock
      fillRect(ctx, pct(28) - 66, GROUND - 100, 132, 100, '#16171c', '#3d4048');
      line(ctx, [pct(28) - 66, GROUND - 52, pct(28) + 66, GROUND - 52], '#30333a', 2);
      clockBox(ctx, pct(28) - 65, GROUND - 184, env.clock || '23:12');
      pool(ctx, pct(28), GROUND - 145, 160, REDL, .14);
    }
  },
  desk: {
    // The character sits BEHIND the desk, facing camera; the desk is drawn in the foreground.
    seat: x => Math.abs(x - pct(50)) < pct(9) ? 60 : 0,
    desk: x => (x > pct(34) && x < pct(66)) ? 118 : 0,
    draw(ctx, env, t) {
      room(ctx, env);
      windowFrame(ctx, pct(12), 190, 300, 270, env, t);
      fillRect(ctx, pct(78), 300, 260, 10, '#24262c', '#3d4048'); fillRect(ctx, pct(78), 420, 260, 10, '#24262c', '#3d4048');
      ITEMS.books(ctx, pct(82), 300); ITEMS.plant(ctx, pct(89), 420);
      // chair back behind the sitter
      rr(ctx, pct(50) - 80, GROUND - 330, 160, 210, 18, '#1b1c22', '#3d4048');
      lamp(ctx, pct(37), GROUND - 118, env.lamp === 'off' ? 0 : 1, t);
      if (env.screen !== 'off') pool(ctx, pct(61), GROUND - 230, 380, COLD, .16);
    },
    fg(ctx, env, t) {
      const x0 = pct(33), x1 = pct(67), top = GROUND - 118;
      // laptop seen from behind, at the side
      ctx.save(); ctx.translate(pct(61), top);
      rr(ctx, -95, -118, 190, 118, 8, '#26282f', '#5a5e68', 2.4);
      ctx.fillStyle = '#3a3d46'; ctx.beginPath(); ctx.arc(0, -60, 9, 0, Math.PI * 2); ctx.fill();
      if (env.screen !== 'off') { ctx.strokeStyle = 'rgba(140,180,255,.55)'; ctx.lineWidth = 3; ctx.strokeRect(-95, -118, 190, 118); }
      ctx.restore();
      rr(ctx, x0, top, x1 - x0, 20, 4, '#3a3027', '#6a5844', 2.4);
      fillRect(ctx, x0 + 14, top + 20, x1 - x0 - 28, GROUND - top + 10, '#1a1714', '#4a3e32', 2.4);
      line(ctx, [x0 + 30, top + 70, x1 - 30, top + 70], '#2c2620', 2);
      pool(ctx, pct(40), top, 360, WARM, env.lamp === 'off' ? 0 : .18, .35);
    }
  },
  kitchen: {
    seat: () => 0,
    draw(ctx, env, t) {
      room(ctx, env, '#111216', '#0c0d10');
      windowFrame(ctx, pct(70), 210, 230, 200, env, t);
      // counter + cabinets
      fillRect(ctx, pct(48), GROUND - 190, pct(48), 190, '#15161a', '#3d4048');
      fillRect(ctx, pct(47), GROUND - 205, pct(50), 16, '#2a2c33', '#4a4e57');
      for (let i = 0; i < 4; i++) rr(ctx, pct(49) + i * 225, 150, 200, 150, 4, '#15161a', '#30333a');
      // fridge
      const fx = pct(30) - 110, fw = 220, open = env.fridge || 0;
      fillRect(ctx, fx, GROUND - 470, fw, 470, '#1c1d22', '#4a4e57', 3);
      if (open) {
        fillRect(ctx, fx + 10, GROUND - 460, fw - 20, 450, `rgba(235,240,250,${.95 * open})`);
        for (let i = 0; i < 4; i++) fillRect(ctx, fx + 14, GROUND - 400 + i * 100, fw - 28, 4, '#c8ccd4');
        const cols = ['#c8383b', '#3f9a5a', '#d9a92e', '#e07a2e'];
        for (let i = 0; i < 6; i++) fillRect(ctx, fx + 30 + (i % 3) * 55, GROUND - 440 + Math.floor(i / 3) * 200, 30, 50, cols[i % 4]);
        pool(ctx, fx + fw / 2, GROUND - 240, 620, WHITE, .3 * open);
        fillRect(ctx, fx - 60 * open, GROUND - 470, 60 * open, 470, '#24262c', '#4a4e57', 3);
      } else line(ctx, [fx + fw - 26, GROUND - 400, fx + fw - 26, GROUND - 300], '#6a6e78', 6);
    }
  },
  street: {
    outdoor: true,
    seat: () => 0,
    draw(ctx, env, t) {
      sky(ctx, env, -50, -50, STAGE_W + 100, GROUND + 50);
      skyline(ctx, -60, STAGE_W + 60, 520, 44, env, t, 380, .22);
      // shopfronts
      const fronts = [[pct(8), 'LAUNDRY', '#9fc7ff'], [pct(54), 'CAFE', '#ffcf8a']];
      fillRect(ctx, -50, 380, STAGE_W + 100, GROUND - 380, '#121318', '#2a2c32');
      for (const [x, label, col] of fronts) {
        fillRect(ctx, x, 470, 360, GROUND - 470, '#0c0d10', '#3d4048', 3);
        fillRect(ctx, x + 20, 520, 220, 240, env.time === 'day' ? '#5d6b7d' : '#1c1a17', '#3d4048', 2);
        if (label === 'CAFE') { ctx.fillStyle = 'rgba(255,200,130,.55)'; ctx.fillRect(x + 22, 522, 216, 236); pool(ctx, x + 130, 640, 360, WARM, .3); }
        else { ctx.fillStyle = 'rgba(140,180,255,.25)'; ctx.fillRect(x + 22, 522, 216, 236); }
        fillRect(ctx, x + 260, 540, 80, GROUND - 540, '#17181d', '#3d4048', 2);
        ctx.font = `30px ${FONT_HAND}`; ctx.fillStyle = col; ctx.textAlign = 'center'; ctx.textBaseline = 'middle';
        ctx.shadowColor = col; ctx.shadowBlur = 16; ctx.fillText(label, x + 180, 495); ctx.shadowBlur = 0;
      }
      for (let x = pct(32); x < pct(50); x += 120) fillRect(ctx, x, 520, 80, 110, '#1a1b20', '#33363d', 2);
      ctx.fillStyle = '#0b0b0e'; ctx.fillRect(-50, GROUND, STAGE_W + 100, 300);
      line(ctx, [-50, GROUND, STAGE_W + 50, GROUND], '#3c3f47', 3);
      line(ctx, [-50, GROUND + 70, STAGE_W + 50, GROUND + 70], '#24262c', 2);
      for (let x = 40; x < STAGE_W; x += 220) line(ctx, [x, GROUND + 140, x + 110, GROUND + 140], '#2e3036', 4);
      streetLamp(ctx, pct(30), 300, t); streetLamp(ctx, pct(92), 300, t);
      if (env.weather === 'rain') { reflect(ctx, pct(30)); reflect(ctx, pct(92)); reflect(ctx, pct(54) + 130, 'rgba(255,200,130,A)', .3, 220); }
      if (env.time === 'night') bokeh(ctx, 5, t, 140, 460, 18);
      weatherIn(ctx, env, t, -50, -50, STAGE_W + 100, STAGE_H + 100);
    }
  },
  park: {
    outdoor: true,
    seatFront: ['#2e2822', '#66563f'],
    seat: x => (x > pct(40) && x < pct(62)) ? 100 : 0,
    draw(ctx, env, t) {
      sky(ctx, env, -50, -50, STAGE_W + 100, GROUND + 50);
      skyline(ctx, -60, STAGE_W + 60, 620, 81, env, t, 300, .18);
      // trees
      ctx.fillStyle = '#0d1012';
      for (const [x, r] of [[pct(8), 160], [pct(22), 120], [pct(84), 180], [pct(97), 130]]) {
        fillRect(ctx, x - 10, GROUND - 300, 20, 300, '#0d0f11');
        ctx.beginPath(); ctx.arc(x, GROUND - 330, r, 0, Math.PI * 2); ctx.arc(x - r * .6, GROUND - 280, r * .7, 0, Math.PI * 2); ctx.arc(x + r * .6, GROUND - 290, r * .75, 0, Math.PI * 2); ctx.fill();
      }
      ctx.fillStyle = '#0b0c0e'; ctx.fillRect(-50, GROUND - 10, STAGE_W + 100, 400);
      // fence
      for (let x = -40; x < STAGE_W + 40; x += 34) line(ctx, [x, GROUND - 10, x, GROUND - 120], '#22252b', 3);
      line(ctx, [-50, GROUND - 100, STAGE_W + 50, GROUND - 100], '#22252b', 3);
      line(ctx, [-50, GROUND, STAGE_W + 50, GROUND], '#3c3f47', 3);
      streetLamp(ctx, pct(70), 260, t);
      if (env.weather === 'rain') reflect(ctx, pct(70));
      bench(ctx, pct(40), pct(62));
      weatherIn(ctx, env, t, -50, -50, STAGE_W + 100, STAGE_H + 100);
    }
  },
  cafe: {
    seatFront: ['#2e2620', '#6a5440'],
    seat: x => (x > pct(14) && x < pct(37)) ? 62 : 0,
    desk: x => (x > pct(14) && x < pct(37)) ? 108 : 0,
    draw(ctx, env, t) {
      room(ctx, env, '#17130f', '#100d0b');
      windowFrame(ctx, pct(4), 200, 330, 300, env, t);
      ctx.save(); ctx.beginPath(); ctx.rect(pct(4), 200, 330, 300); ctx.clip(); bokeh(ctx, 17, t, 220, 480, 12); ctx.restore();
      // menu board
      rr(ctx, pct(68), 170, 300, 190, 8, '#141412', '#5a4c3e', 3);
      ctx.font = `30px ${FONT_HAND}`; ctx.fillStyle = '#e9e1cf'; ctx.textAlign = 'center'; ctx.fillText('COFFEE', pct(68) + 150, 210);
      ctx.font = `22px ${FONT_HAND}`; ctx.fillText('latte  3.5', pct(68) + 150, 260); ctx.fillText('tea  2', pct(68) + 150, 300);
      // counter
      fillRect(ctx, pct(52), GROUND - 230, pct(42), 230, '#2a221b', '#6a5440', 3);
      fillRect(ctx, pct(51), GROUND - 244, pct(44), 16, '#3a2f25', '#7a6248', 2);
      rr(ctx, pct(86), GROUND - 330, 90, 86, 10, '#3d4048', '#5a5e68');
      // pendant lamp
      line(ctx, [pct(66), 0, pct(66), 250], '#3d4048', 3);
      ctx.fillStyle = '#4a3d30'; ctx.beginPath(); ctx.moveTo(pct(66) - 40, 290); ctx.lineTo(pct(66) + 40, 290); ctx.lineTo(pct(66) + 16, 250); ctx.lineTo(pct(66) - 16, 250); ctx.fill();
      pool(ctx, pct(66), 300, 520, WARM, .35, .8);
      pool(ctx, pct(25), GROUND - 180, 420, WARM, .2, .5);
      for (const sx of [pct(19), pct(31)]) { rr(ctx, sx - 40, GROUND - 64, 80, 14, 6, '#2e2620', '#6a5440'); fillRect(ctx, sx - 5, GROUND - 50, 10, 50, '#221c17'); }
    },
    fg(ctx, env, t) {
      const x0 = pct(13), x1 = pct(38), top = GROUND - 108;
      rr(ctx, x0, top, x1 - x0, 18, 6, '#3a2f25', '#7a6248', 2.4);
      fillRect(ctx, (x0 + x1) / 2 - 10, top + 18, 20, GROUND - top - 18, '#2a221b', '#4a3e32', 2);
      fillRect(ctx, (x0 + x1) / 2 - 70, GROUND - 8, 140, 8, '#2a221b');
      for (const cx of [pct(17), pct(33)]) { ctx.save(); ctx.translate(cx, top); rr(ctx, -16, -30, 32, 30, 5, '#efeadf', '#8a8478', 2); ctx.fillStyle = '#6b4430'; ctx.fillRect(-16, -22, 32, 6); ctx.restore(); }
    }
  },
  gym: {
    seat: () => 0,
    draw(ctx, env, t) {
      room(ctx, env, '#0d0d10', '#09090b');
      // rack
      for (const x of [pct(50) - 190, pct(50) + 190]) fillRect(ctx, x - 9, GROUND - 520, 18, 520, '#1d1e22', '#4a4e57', 2);
      fillRect(ctx, pct(50) - 200, GROUND - 530, 400, 14, '#1d1e22', '#4a4e57', 2);
      // dumbbell rack
      fillRect(ctx, pct(80), GROUND - 120, 280, 12, '#1d1e22', '#4a4e57', 2);
      for (let i = 0; i < 4; i++) ITEMS.dumbbell(ctx, pct(80) + 50 + i * 62, GROUND - 120);
      ITEMS.dumbbell(ctx, pct(14), GROUND);
      fillRect(ctx, pct(8), GROUND - 330, 22, 200, '#16171b', '#3d4048', 2);
      // spotlight from above
      ctx.fillStyle = 'rgba(255,225,170,.10)';
      ctx.beginPath(); ctx.moveTo(pct(50) - 60, 60); ctx.lineTo(pct(50) + 60, 60); ctx.lineTo(pct(50) + 330, GROUND); ctx.lineTo(pct(50) - 330, GROUND); ctx.fill();
      rr(ctx, pct(50) - 50, 40, 100, 26, 8, '#3d4048');
      pool(ctx, pct(50), 70, 140, WHITE, .5);
      pool(ctx, pct(50), GROUND, 420, WARM, .3, .2);
    }
  },
  hill: {
    outdoor: true,
    seat: () => 0,
    ground: x => GROUND - 40 - 430 * smooth((x - pct(5)) / pct(90)),
    draw(ctx, env, t) {
      sky(ctx, env, -50, -50, STAGE_W + 100, STAGE_H + 100);
      if (env.time === 'dawn' || env.time === 'dusk') pool(ctx, pct(85), 520, 700, 'rgba(255,140,70,A)', .35, .6);
      skyline(ctx, -60, STAGE_W + 60, STAGE_H - 60, 23, env, t, 230, .3);
      ctx.fillStyle = '#0a0b0e'; ctx.strokeStyle = '#8c8e94'; ctx.lineWidth = 3;
      ctx.beginPath(); ctx.moveTo(-50, STAGE_H + 50);
      for (let x = -50; x <= STAGE_W + 50; x += 20) ctx.lineTo(x, SETS.hill.ground(x));
      ctx.lineTo(STAGE_W + 50, STAGE_H + 50); ctx.closePath(); ctx.fill();
      ctx.beginPath(); for (let x = -50; x <= STAGE_W + 50; x += 20) ctx[x === -50 ? 'moveTo' : 'lineTo'](x, SETS.hill.ground(x)); ctx.stroke();
      weatherIn(ctx, env, t, -50, -50, STAGE_W + 100, STAGE_H + 100);
    }
  },
  rooftop: {
    outdoor: true,
    seatFront: ['#1a1b20', '#4a4e57'],
    seat: x => (x > pct(28) && x < pct(72)) ? 104 : 0,
    draw(ctx, env, t) {
      sky(ctx, env, -50, -50, STAGE_W + 100, STAGE_H + 100);
      if (env.time === 'dawn' || env.time === 'dusk') pool(ctx, pct(50), GROUND - 120, 900, 'rgba(255,150,80,A)', .4, .5);
      skyline(ctx, -60, STAGE_W + 60, GROUND - 40, 57, env, t, 420, .3);
      fillRect(ctx, -50, GROUND - 104, STAGE_W + 100, 104, '#121317', '#4a4e57', 3);
      for (let x = 0; x < STAGE_W; x += 160) line(ctx, [x, GROUND - 104, x, GROUND], '#1e2026', 2);
      ctx.fillStyle = '#0a0a0c'; ctx.fillRect(-50, GROUND, STAGE_W + 100, 300);
      line(ctx, [-50, GROUND, STAGE_W + 50, GROUND], '#3c3f47', 3);
      weatherIn(ctx, env, t, -50, -50, STAGE_W + 100, STAGE_H + 100);
    }
  },
  hallway: {
    seat: () => 0,
    draw(ctx, env, t) {
      room(ctx, env, '#101115', '#0b0c0f');
      for (const x of [pct(12), pct(32)]) rr(ctx, x, 260, 160, 220, 4, '#141519', '#2e3037', 2);
      door(ctx, pct(70) - 75, env.door || 0, 160, 400);
      pool(ctx, pct(30), 120, 300, WARM, .12);
    }
  },
  bus_stop: {
    outdoor: true,
    seat: x => (x > pct(44) && x < pct(66)) ? 58 : 0,
    seatFront: ['#2a2c32', '#5a5e68'],
    draw(ctx, env, t) {
      sky(ctx, env, -50, -50, STAGE_W + 100, GROUND + 50);
      skyline(ctx, -60, STAGE_W + 60, 640, 63, env, t, 420, .2);
      if (env.time === 'night') bokeh(ctx, 9, t, 200, 560, 22);
      ctx.fillStyle = '#0b0b0e'; ctx.fillRect(-50, GROUND, STAGE_W + 100, 300);
      line(ctx, [-50, GROUND, STAGE_W + 50, GROUND], '#3c3f47', 3);
      line(ctx, [-50, GROUND + 90, STAGE_W + 50, GROUND + 90], '#2a2c32', 2);
      // shelter: roof, glass back panel, posts
      const x0 = pct(36), x1 = pct(74), top = GROUND - 470;
      ctx.fillStyle = 'rgba(150,175,200,.08)'; ctx.fillRect(x0 + 10, top + 30, x1 - x0 - 20, GROUND - top - 30);
      line(ctx, [x0 + 10, top + 30, x0 + 10, GROUND], '#4a4e57', 6); line(ctx, [x1 - 10, top + 30, x1 - 10, GROUND], '#4a4e57', 6);
      rr(ctx, x0 - 30, top, x1 - x0 + 60, 34, 6, '#2a2c33', '#5a5e68');
      fillRect(ctx, x0 + 60, top + 34, x1 - x0 - 120, 8, 'rgba(255,240,210,.85)');
      pool(ctx, (x0 + x1) / 2, top + 60, 520, WARM, .26, .8);
      // timetable + sign
      rr(ctx, x1 + 40, GROUND - 420, 16, 420, 4, '#3d4048'); rr(ctx, x1 + 10, GROUND - 470, 76, 60, 8, '#2f6fd6', '#a9c4f2');
      ctx.fillStyle = '#fff'; ctx.font = `bold 30px ${FONT_UI}`; ctx.textAlign = 'center'; ctx.fillText('BUS', x1 + 48, GROUND - 430);
      rr(ctx, x0 + 40, GROUND - 330, 120, 170, 6, '#1d2028', '#4a4e57');
      for (let i = 0; i < 6; i++) fillRect(ctx, x0 + 56, GROUND - 310 + i * 24, 88, 6, '#4a5160');
      bench(ctx, pct(44), pct(66));
      if (env.weather === 'rain') { reflect(ctx, (x0 + x1) / 2, 'rgba(255,230,190,A)', .25, 300); }
      weatherIn(ctx, env, t, -50, -50, STAGE_W + 100, STAGE_H + 100);
    }
  },
  office: {
    seat: x => Math.abs(x - pct(50)) < pct(9) ? 60 : 0,
    desk: x => (x > pct(34) && x < pct(66)) ? 118 : 0,
    draw(ctx, env, t) {
      room(ctx, env, '#15171c', '#0f1014');
      // fluorescent panels
      for (const x of [pct(20), pct(50), pct(80)]) { fillRect(ctx, x - 120, 80, 240, 16, 'rgba(230,240,255,.7)'); pool(ctx, x, 120, 380, WHITE, .1, .6); }
      windowFrame(ctx, pct(78), 200, 320, 260, env, t);
      // background cubicles with monitors
      for (const x of [pct(10), pct(24)]) {
        fillRect(ctx, x - 110, GROUND - 230, 220, 230, '#1a1c22', '#3d4048'); rr(ctx, x - 50, GROUND - 330, 100, 70, 4, '#20242c', '#5a5e68');
        rr(ctx, x - 44, GROUND - 324, 88, 58, 2, '#3e6aa8'); pool(ctx, x, GROUND - 300, 160, COLD, .12);
      }
      rr(ctx, pct(50) - 80, GROUND - 330, 160, 210, 18, '#1b1c22', '#3d4048');
      pool(ctx, pct(61), GROUND - 230, 380, COLD, .16);
      ITEMS.plant(ctx, pct(92), GROUND);
    },
    fg(ctx, env, t) { SETS.desk.fg(ctx, { ...env, lamp: 'off' }, t); }
  },
  void: {
    seat: () => 0,
    draw(ctx, env, t) {
      ctx.fillStyle = '#060607'; ctx.fillRect(-50, -50, STAGE_W + 100, STAGE_H + 100);
      ctx.fillStyle = 'rgba(255,240,215,.06)';
      ctx.beginPath(); ctx.moveTo(pct(50) - 40, -50); ctx.lineTo(pct(50) + 40, -50); ctx.lineTo(pct(50) + 280, GROUND); ctx.lineTo(pct(50) - 280, GROUND); ctx.fill();
      pool(ctx, pct(50), GROUND, 380, WHITE, .16, .18);
    }
  }
};

function drawItems(ctx, items, set, t) {
  for (const it of items || []) {
    const fn = ITEMS[it.type]; if (!fn) continue;
    const x = pct(it.x ?? 50);
    let y = (SETS[set].ground || flatGround)(x);
    if (it.on === 'nightstand' && set === 'bedroom') y = GROUND - 100;
    if (it.on === 'desk' && set === 'desk') y = GROUND - 118;
    if (it.on === 'table' && set === 'cafe') y = GROUND - 108;
    if (it.on === 'counter') y = GROUND - 244;
    if (it.on === 'bed' && set === 'bedroom') y = GROUND - 62;
    const n = Math.max(1, Math.min(6, it.count || 1));
    for (let i = 0; i < n; i++) fn(ctx, x + i * 70 * (i % 2 ? 1 : -1) * Math.ceil(i / 2), y, t);
  }
}
