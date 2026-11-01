// Screen-space layers: phone point-of-view, HUD counter, dialogue, captions and text cards.
'use strict';
const FONT_HAND = '"FilmHand", "Patrick Hand", "Poppins", sans-serif';
const FONT_UI = '"FilmRound", "Nunito", "Poppins", sans-serif';
const FONT_DIGIT = '"FilmDigit", "DejaVu Sans Mono", monospace';

function typed(text, u, cps = 26) { return text.slice(0, Math.max(0, Math.floor(u * cps))); }

function textShadowed(ctx, text, x, y, size, color, opts = {}) {
  ctx.font = `${opts.italic ? 'italic ' : ''}${opts.bold ? 'bold ' : ''}${size}px ${opts.font || FONT_HAND}`;
  ctx.textAlign = opts.align || 'center'; ctx.textBaseline = 'middle';
  ctx.shadowColor = opts.glow || 'rgba(0,0,0,.85)'; ctx.shadowBlur = opts.glowBlur ?? 10;
  ctx.fillStyle = color; ctx.fillText(text, x, y); ctx.shadowBlur = 0;
}

function wrapLines(ctx, text, maxW) {
  const words = text.split(/\s+/); const out = []; let cur = '';
  for (const w of words) { const t = cur ? cur + ' ' + w : w; if (ctx.measureText(t).width > maxW && cur) { out.push(cur); cur = w; } else cur = t; }
  if (cur) out.push(cur); return out;
}

// ---------- HUD ----------
// film.hud: {label} (one counter) or {items: [{label, color}]} (several, e.g. SEEN / KNOWN), or null.
// shot.hud: {value | values: [...], chapter, alert}. A value can be [from, to] to count during the shot.
function hudItems(film) {
  const h = film.hud; if (!h) return [];
  if (Array.isArray(h.items)) return h.items;
  return h.label ? [{ label: h.label, color: h.color }] : [];
}
function drawHud(ctx, film, shot, u, K) {
  const hud = shot.hud; if (!hud) return;
  const items = hudItems(film);
  const p = clamp(u / Math.max(.6, Math.min(shot.dur * .8, 2.2)), 0, 1);
  const vals = hud.values || (hud.value !== undefined ? [hud.value] : []);
  ctx.save(); ctx.scale(K, K);
  let y = 104;
  const fmt = v => typeof v === 'number' ? Math.round(v).toLocaleString('en-US') : v;
  if (hud.chapter) { textShadowed(ctx, String(hud.chapter).toUpperCase(), 64, y, 30, 'rgba(240,238,230,.95)', { align: 'left', font: FONT_UI, bold: true }); y += 38; }
  items.forEach((it, i) => {
    let v = vals[i]; if (v === undefined || v === null) return;
    if (Array.isArray(v)) v = lerp(v[0], v[1], easeInOut(p));
    const label = String(it.label).toUpperCase() + ' ';
    ctx.font = `bold 30px ${FONT_UI}`;
    const w = ctx.measureText(label).width;
    textShadowed(ctx, label, 64, y, 30, 'rgba(240,238,230,.95)', { align: 'left', font: FONT_UI, bold: true });
    const col = hud.alert && i === 0 ? '#ff4a4a' : (it.color || '#ffd34a');
    textShadowed(ctx, fmt(v), 64 + w, y, 30, col, { align: 'left', font: FONT_UI, bold: true });
    y += 36;
  });
  ctx.restore();
}

// ---------- dialogue / captions ----------
// line: {who, text, at, dur, style: bubble|float|thought|whisper, twist (narrator second line)}
function bubble(ctx, text, x, y, hx, hy, k) {
  ctx.font = `34px ${FONT_HAND}`;
  const lines = wrapLines(ctx, text || ' ', 420);
  const w = Math.max(80, ...lines.map(l => ctx.measureText(l).width)) + 44, h = lines.length * 40 + 26;
  const bx = clamp(x - w / 2, 70, 1850 - w), by = clamp(y - h - 34, 70, 980 - h);
  ctx.save();
  ctx.translate(bx + w / 2, by + h); ctx.scale(k, k); ctx.translate(-(bx + w / 2), -(by + h));
  ctx.shadowColor = 'rgba(0,0,0,.45)'; ctx.shadowBlur = 14; ctx.shadowOffsetY = 4;
  roundRect(ctx, bx, by, w, h, 22); ctx.fillStyle = '#fbfaf5'; ctx.fill(); ctx.shadowBlur = 0; ctx.shadowOffsetY = 0;
  ctx.lineWidth = 3; ctx.strokeStyle = '#141416'; ctx.stroke();
  const tx = clamp(hx, bx + 30, bx + w - 30);
  ctx.beginPath(); ctx.moveTo(tx - 13, by + h - 2); ctx.lineTo(tx + (hx > tx ? 22 : -6), by + h + 30); ctx.lineTo(tx + 13, by + h - 2); ctx.closePath();
  ctx.fillStyle = '#fbfaf5'; ctx.fill(); ctx.stroke();
  ctx.fillStyle = '#fbfaf5'; ctx.fillRect(tx - 11, by + h - 5, 22, 6);
  ctx.fillStyle = '#18181b'; ctx.textAlign = 'left'; ctx.textBaseline = 'middle';
  lines.forEach((l, i) => ctx.fillText(l, bx + 22, by + 33 + i * 40));
  ctx.restore();
}

function drawLines(ctx, shot, u, heads, K, film) {
  ctx.save(); ctx.scale(K, K);
  const dcol = (film.demon_color || '#ff3b3b');
  for (const ln of shot.lines || []) {
    if (ln.hidden) continue;
    const at = ln.at ?? 0, dur = ln.dur ?? (shot.dur - at);
    if (u < at || u > at + dur) continue;
    const lu = u - at, fadeOut = clamp((at + dur - u) / .25, 0, 1);
    ctx.globalAlpha = Math.min(1, lu / .12) * fadeOut;
    const who = ln.who || 'caption';
    const isDemon = (film.cast[who] || {}).kind === 'demon' || who === 'demon';
    const narr = who === 'caption' || who === 'narrator';
    const cps = ln.cps || (narr ? 24 : isDemon ? 18 : 22);
    const txt = typed(ln.text, lu, cps);
    if (narr) {
      const caption = narratorCaption(ln, lu);
      if (!caption) continue;
      let size = 38;
      ctx.font = size + 'px ' + FONT_UI;
      let rows = wrapLines(ctx, caption, 1480);
      while (rows.length > 2 && size > 28) {
        size -= 2;ctx.font = size + 'px ' + FONT_UI;rows = wrapLines(ctx, caption, 1480);
      }
      const lineHeight = size + 8, top = 905 - (rows.length - 1) * lineHeight / 2;
      const boxWidth = Math.max(...rows.map(row => ctx.measureText(row).width)) + 48;
      ctx.save();ctx.shadowBlur = 0;ctx.fillStyle = 'rgba(0,0,0,.76)';
      roundRect(ctx, 960 - boxWidth / 2, top - size / 2 - 12, boxWidth, rows.length * lineHeight + 20, 10);
      ctx.fill();ctx.restore();
      rows.forEach((row, index) => textShadowed(ctx, row, 960, top + index * lineHeight, size, '#f5f3ec', {font: FONT_UI, glowBlur: 0}));
      continue;
    }
    const head = heads[who];
    if (!head) {
      if (isDemon) textShadowed(ctx, txt, 960 + noise1(u * 8, 1) * 2, 170, 46, dcol, { glow: rgba(dcol, .6), glowBlur: 18, italic: true });
      else textShadowed(ctx, txt, 960, 170, 38, C.text);
      continue;
    }
    const [hx, hy] = head;
    const style = ln.style || (isDemon ? 'float' : 'bubble');
    if (isDemon) {
      const x = clamp(hx + 90, 260, 1660), y = clamp(hy - 50, 150, 900);
      textShadowed(ctx, txt, x + noise1(u * 9, 2) * 2.5, y, 42, dcol, { glow: rgba(dcol, .7), glowBlur: 18, italic: true });
    } else if (style === 'bubble') {
      bubble(ctx, txt, hx, hy - 20, hx, hy - 20, backOut(clamp(lu / .22, 0, 1)));
    } else if (style === 'thought') {
      textShadowed(ctx, '(' + txt + ')', clamp(hx, 220, 1700), clamp(hy - 50, 150, 900), 32, 'rgba(220,220,225,.85)', { italic: true });
    } else if (style === 'whisper') {
      textShadowed(ctx, txt, clamp(hx, 220, 1700), clamp(hy - 46, 150, 900), 26, 'rgba(225,225,230,.75)');
    } else {
      textShadowed(ctx, txt, clamp(hx, 220, 1700), clamp(hy - 50, 150, 900), 34, C.text);
    }
  }
  ctx.globalAlpha = 1; ctx.restore();
}

// Big in-scene words, e.g. "DAY 1." or "SATURDAY."
function drawBig(ctx, shot, u, K) {
  const b = shot.big; if (!b || !b.text) return;
  const at = b.at ?? .2; if (u < at) return;
  const k = backOut(clamp((u - at) / .35, 0, 1));
  ctx.save(); ctx.scale(K, K);
  const x = b.x !== undefined ? pct(b.x) : 560, y = b.y ?? 470;
  ctx.translate(x, y); ctx.scale(k, k);
  textShadowed(ctx, b.text, 0, 0, b.size || 120, b.color || '#f4f1ea', { font: FONT_UI, bold: true, glowBlur: 24 });
  ctx.restore();
}

// ---------- phone point of view ----------
function phoneScreen(ctx, ph, u, t) {
  const W = 500, H = 940;
  ctx.fillStyle = '#0f1116'; ctx.fillRect(0, 0, W, H);
  ctx.font = `20px ${FONT_HAND}`; ctx.fillStyle = '#c9ccd4'; ctx.textAlign = 'left'; ctx.textBaseline = 'middle';
  ctx.fillText(ph.time || '23:41', 34, 34); ctx.textAlign = 'right'; ctx.fillText('▮▮▮  82%', W - 30, 34);
  const app = ph.app || 'chat';
  if (app === 'chat') {
    // header
    ctx.fillStyle = '#171a21'; ctx.fillRect(0, 60, W, 92);
    ctx.fillStyle = ph.color || '#e07a2e'; ctx.beginPath(); ctx.arc(66, 106, 26, 0, Math.PI * 2); ctx.fill();
    ctx.fillStyle = '#fff'; ctx.font = `bold 24px ${FONT_HAND}`; ctx.textAlign = 'center'; ctx.fillText((ph.contact || 'Sam')[0].toUpperCase(), 66, 107);
    ctx.textAlign = 'left'; ctx.font = `28px ${FONT_HAND}`; ctx.fillText(ph.contact || 'Sam', 108, 96);
    ctx.font = `18px ${FONT_HAND}`; ctx.fillStyle = '#7d8492'; ctx.fillText(ph.status || 'online', 108, 124);
    let y = 190;
    const msgs = (ph.messages || []).filter(m => u >= (m.at ?? 0)).slice();
    // a sent typed message appears as a bubble
    const ty = ph.typing;
    let input = '';
    if (ty) {
      const at = ty.at ?? .3, cps = ty.cps || 11, n = ty.text.length, full = at + n / cps;
      if (u >= at) {
        if (ty.action === 'delete') {
          const del = full + (ty.pause ?? .7);
          if (u < del) input = ty.text.slice(0, Math.floor((u - at) * cps));
          else input = ty.text.slice(0, Math.max(0, n - Math.floor((u - del) * cps * 2.4)));
        } else if (ty.action === 'send') {
          if (u < full + .35) input = ty.text.slice(0, Math.floor((u - at) * cps));
          else msgs.push({ from: 'me', text: ty.text, at: full + .35 });
        } else input = ty.text.slice(0, Math.floor((u - at) * cps));
      }
    }
    for (const m of msgs) {
      ctx.font = `25px ${FONT_HAND}`;
      const lines = wrapLines(ctx, m.text, 300); const bw = Math.max(...lines.map(l => ctx.measureText(l).width)) + 36, bh = lines.length * 32 + 22;
      const pop = backOut(clamp((u - (m.at ?? 0)) / .25, 0, 1));
      const me = m.from === 'me', x = me ? W - 26 - bw : 26;
      ctx.save(); ctx.translate(x + (me ? bw : 0), y); ctx.scale(pop, pop); ctx.translate(-(me ? bw : 0), 0);
      rr(ctx, 0, 0, bw, bh, 18, me ? '#3478f6' : '#262a33');
      ctx.fillStyle = '#f3f4f6'; ctx.textAlign = 'left';
      lines.forEach((l, i) => ctx.fillText(l, 18, 27 + i * 32));
      ctx.restore();
      y += bh + 14;
    }
    if (ph.seen && u > ph.seen) { ctx.font = `16px ${FONT_HAND}`; ctx.fillStyle = '#7d8492'; ctx.textAlign = 'right'; ctx.fillText('seen', W - 30, y + 4); }
    // input bar
    rr(ctx, 20, H - 96, W - 110, 58, 29, '#1d2028', '#2c303a', 2);
    ctx.font = `25px ${FONT_HAND}`; ctx.textAlign = 'left';
    ctx.fillStyle = input ? '#f3f4f6' : '#5b6170'; ctx.fillText(input || 'Message', 44, H - 67);
    if (Math.floor(t * 2) % 2 === 0 && ty && u >= (ty.at ?? .3)) { const w = ctx.measureText(input).width; ctx.fillStyle = '#3478f6'; ctx.fillRect(46 + w, H - 82, 3, 30); }
    ctx.fillStyle = '#3478f6'; ctx.beginPath(); ctx.arc(W - 50, H - 67, 26, 0, Math.PI * 2); ctx.fill();
    ctx.fillStyle = '#fff'; ctx.beginPath(); ctx.moveTo(W - 60, H - 78); ctx.lineTo(W - 38, H - 67); ctx.lineTo(W - 60, H - 56); ctx.fill();
  } else if (app === 'call') {
    const c = ph.call || {}; const dec = c.decline_at, ans = c.answer_at;
    ctx.fillStyle = '#12151c'; ctx.fillRect(0, 60, W, H);
    ctx.fillStyle = '#3a3f4c'; ctx.beginPath(); ctx.arc(W / 2, 270, 70, 0, Math.PI * 2); ctx.fill();
    ctx.fillStyle = '#7c8394'; ctx.beginPath(); ctx.arc(W / 2, 250, 28, 0, Math.PI * 2); ctx.fill(); ctx.beginPath(); ctx.ellipse(W / 2, 318, 46, 26, 0, Math.PI, 0); ctx.fill();
    ctx.textAlign = 'center'; ctx.fillStyle = '#f3f4f6'; ctx.font = `38px ${FONT_HAND}`; ctx.fillText(ph.contact || 'unknown number', W / 2, 400);
    const ended = dec !== undefined && u > dec, live = ans !== undefined && u > ans;
    ctx.font = `22px ${FONT_HAND}`; ctx.fillStyle = '#8b92a1';
    ctx.fillText(ended ? 'call declined' : live ? `00:${String(Math.floor(u - ans)).padStart(2, '0')}` : 'incoming call...', W / 2, 444);
    if (!ended && !live) {
      const pulse = 1 + .06 * Math.sin(u * 8);
      for (const [x, col] of [[W / 2 - 110, '#ff3b30'], [W / 2 + 110, '#34c759']]) { ctx.fillStyle = col; ctx.beginPath(); ctx.arc(x, H - 170, 42 * pulse, 0, Math.PI * 2); ctx.fill(); }
    } else if (live) { ctx.fillStyle = '#ff3b30'; ctx.beginPath(); ctx.arc(W / 2, H - 170, 42, 0, Math.PI * 2); ctx.fill(); }
  } else if (app === 'lock') {
    const g = ctx.createLinearGradient(0, 0, 0, H); g.addColorStop(0, '#1a2033'); g.addColorStop(1, '#0c0e14'); ctx.fillStyle = g; ctx.fillRect(0, 0, W, H);
    ctx.textAlign = 'center'; ctx.fillStyle = '#eef1f6'; ctx.font = `110px ${FONT_HAND}`; ctx.fillText(ph.time || '02:14', W / 2, 220);
    ctx.font = `24px ${FONT_HAND}`; ctx.fillStyle = '#aab1c0'; ctx.fillText(ph.date || 'Tuesday', W / 2, 300);
    let y = 360;
    for (const n of (ph.notifications || [])) {
      if (u < (n.at ?? 0)) continue;
      const k = backOut(clamp((u - (n.at ?? 0)) / .3, 0, 1));
      ctx.save(); ctx.translate(0, (1 - k) * -40); ctx.globalAlpha = clamp(k, 0, 1);
      rr(ctx, 24, y, W - 48, 92, 20, 'rgba(60,66,82,.85)');
      ctx.textAlign = 'left'; ctx.fillStyle = '#f3f4f6'; ctx.font = `bold 20px ${FONT_HAND}`; ctx.fillText((n.app || 'Messages').toUpperCase(), 48, y + 28);
      ctx.font = `24px ${FONT_HAND}`; ctx.fillText(n.text, 48, y + 62);
      ctx.restore(); y += 108;
    }
  } else if (app === 'feed') {
    ctx.fillStyle = '#0d0f14'; ctx.fillRect(0, 60, W, H);
    ctx.font = `bold 26px ${FONT_HAND}`; ctx.fillStyle = '#f3f4f6'; ctx.textAlign = 'left'; ctx.fillText('feed', 30, 96);
    const scroll = u * (ph.speed || 260);
    ctx.save(); ctx.beginPath(); ctx.rect(0, 120, W, H - 120); ctx.clip();
    for (let i = 0; i < 12; i++) {
      const y = 140 + i * 430 - (scroll % (430 * 6)) ;
      if (y < -440 || y > H) continue;
      const hue = [ '#e07a2e', '#3f9a5a', '#3b6fc4', '#c8383b', '#9a5ac8', '#d9a92e'][i % 6];
      ctx.fillStyle = hue; ctx.beginPath(); ctx.arc(52, y + 22, 18, 0, Math.PI * 2); ctx.fill();
      ctx.fillStyle = '#d7dae0'; ctx.font = `20px ${FONT_HAND}`; ctx.fillText(['max', 'jo', 'leo', 'ana', 'kit', 'sam'][i % 6], 82, y + 24);
      const g = ctx.createLinearGradient(0, y + 52, 0, y + 352); g.addColorStop(0, shade(hue, -.45)); g.addColorStop(1, shade(hue, -.75));
      ctx.fillStyle = g; ctx.fillRect(20, y + 52, W - 40, 300);
      // tiny happy people in the post
      for (let k = 0; k < 3 + (i % 2); k++) {
        const px = 90 + k * 95, py = y + 330;
        ctx.save(); ctx.translate(px, py); ctx.scale(.42, .42);
        drawCharacter(ctx, { wx: 0, wy: 0, scale: 1, mood: 'happy', hat: ['beanie_orange', 'none', 'cap_red', 'beanie_blue'][(i + k) % 4] }, (() => { const P = basePose(); P.hands = [[-66, -300 - 20 * Math.sin(t * 4 + k)], [66, -300]]; P.lift = Math.abs(Math.sin(t * 4 + k)) * 12; return P; })(), { zoom: .45, t, noShadow: true });
        ctx.restore();
      }
      ctx.fillStyle = '#ff4d6d'; ctx.font = `22px ${FONT_HAND}`; ctx.fillText(`♥ ${(1200 + i * 731) % 9000 + 300}`, 30, y + 382);
    }
    ctx.restore();
  } else if (app === 'off') {
    // The screen shows the time, then goes dark when the side button is pressed.
    const off = ph.off_at ?? 1.4, k = clamp((u - off) / .25, 0, 1);
    const g = ctx.createLinearGradient(0, 0, 0, H); g.addColorStop(0, '#1a2033'); g.addColorStop(1, '#0c0e14'); ctx.fillStyle = g; ctx.fillRect(0, 0, W, H);
    ctx.textAlign = 'center'; ctx.fillStyle = '#eef1f6'; ctx.font = `110px ${FONT_UI}`; ctx.fillText(ph.time || '07:48', W / 2, 220);
    ctx.globalAlpha = k; ctx.fillStyle = '#030304'; ctx.fillRect(0, 0, W, H); ctx.globalAlpha = 1;
    if (k > 0) { ctx.strokeStyle = 'rgba(255,255,255,.06)'; ctx.lineWidth = 60; ctx.beginPath(); ctx.moveTo(-40, H * .7); ctx.lineTo(W + 40, H * .2); ctx.stroke(); }
  } else if (app === 'alarm') {
    ctx.fillStyle = '#0d0f14'; ctx.fillRect(0, 0, W, H);
    ctx.textAlign = 'center'; ctx.fillStyle = '#f3f4f6'; ctx.font = `120px ${FONT_HAND}`; ctx.fillText(ph.time || '05:30', W / 2, 330);
    ctx.font = `28px ${FONT_HAND}`; ctx.fillStyle = '#aab1c0'; ctx.fillText(ph.label || 'alarm', W / 2, 410);
    rr(ctx, 60, H - 260, W - 120, 80, 40, '#2a2e38'); ctx.fillStyle = '#f3f4f6'; ctx.fillText('snooze', W / 2, H - 220);
    rr(ctx, 60, H - 160, W - 120, 80, 40, '#ff9f0a'); ctx.fillStyle = '#111'; ctx.fillText('stop', W / 2, H - 120);
  }
}

function drawPhonePOV(ctx, shot, u, t, K) {
  const ph = shot.phone || {};
  const ring = (ph.app === 'call' && !(ph.call && (u > (ph.call.decline_at ?? 1e9) || u > (ph.call.answer_at ?? 1e9)))) || ph.app === 'alarm';
  const jx = ring ? Math.sin(u * 60) * 3 * (Math.sin(u * 5) > 0 ? 1 : 0) : 0;
  const rise = easeOut(clamp(u / .35, 0, 1));
  ctx.save(); ctx.scale(K, K);
  ctx.translate(960 + jx + noise1(t * .4, 9) * 6, 600 + (1 - rise) * 80 + noise1(t * .35, 4) * 5);
  ctx.rotate(noise1(t * .3, 2) * .01 - .015);
  // glow from the screen onto the room
  pool(ctx, 0, 0, 720, 'rgba(120,160,255,A)', .1);
  // left hand behind
  ctx.fillStyle = C.cream; ctx.strokeStyle = C.ink; ctx.lineWidth = 3;
  ctx.beginPath(); ctx.ellipse(-300, 360, 90, 200, -.25, 0, Math.PI * 2); ctx.fill(); ctx.stroke();
  // phone body
  rr(ctx, -272, -500, 544, 1040, 64, '#1b1d22', '#565a63', 4);
  ctx.save(); roundRect(ctx, -250, -478, 500, 996, 48); ctx.clip(); ctx.translate(-250, -478);
  phoneScreen(ctx, ph, u, t);
  ctx.restore();
  rr(ctx, -70, -466, 140, 26, 13, '#08090b');
  if (ph.app === 'off') {
    const press = clamp(1 - Math.abs(u - (ph.off_at ?? 1.4)) / .3, 0, 1);
    ctx.fillStyle = C.cream; ctx.strokeStyle = C.ink; ctx.lineWidth = 3;
    ctx.beginPath(); ctx.ellipse(300 - press * 18, -140, 40, 70, 0, 0, Math.PI * 2); ctx.fill(); ctx.stroke();
  }
  // right thumb (taps while typing)
  const typing = ph.typing && u > (ph.typing.at ?? .3);
  const tap = typing ? Math.abs(Math.sin(u * 22)) * 14 : 0;
  ctx.fillStyle = C.cream; ctx.strokeStyle = C.ink; ctx.lineWidth = 3;
  ctx.beginPath(); ctx.ellipse(250, 420 - tap, 80, 190, .45, 0, Math.PI * 2); ctx.fill(); ctx.stroke();
  ctx.beginPath(); ctx.ellipse(170, 300 - tap, 34, 86, .7, 0, Math.PI * 2); ctx.fill(); ctx.stroke();
  ctx.restore();
}

// ---------- cards ----------
// styles: line (one narration line on black), quote (two lines, the second bold), red (imperative),
// logo (the film's title card with tagline), title, cta (like and subscribe)
function drawCard(ctx, shot, u, t, K) {
  const cd = shot.card; const lines = cd.lines || [];
  const k = easeOut(clamp(u / .4, 0, 1));
  const accent = (FILM && FILM.demon_color) || '#ff3434';
  ctx.save(); ctx.scale(K, K);
  const style = cd.style || 'title';
  if (style === 'line') {
    textShadowed(ctx, typed(lines[0] || '', u - .2, 22), 960, 520, 46, C.text, { font: FONT_UI });
  } else if (style === 'red') {
    textShadowed(ctx, lines[0] || '', 960, 440, 120 + (1 - k) * 30, accent, { glow: rgba(accent, .55), glowBlur: 30, font: FONT_UI, bold: true });
    if (lines[1]) { ctx.globalAlpha = clamp((u - .6) / .4, 0, 1); textShadowed(ctx, lines[1], 960, 545, 40, C.text, { font: FONT_UI }); }
  } else if (style === 'quote') {
    lines.slice(0, 2).forEach((l, i) => { ctx.globalAlpha = clamp((u - i * 1.1) / .5, 0, 1); textShadowed(ctx, l, 960, 480 + i * 66, i ? 50 : 44, i ? '#ffffff' : 'rgba(235,233,226,.9)', { font: FONT_UI, bold: i === 1 }); });
  } else if (style === 'logo') {
    const title = lines[0] || '';
    const parts = title.split(/\s+vs\.?\s+/i);
    ctx.globalAlpha = k;
    if (parts.length === 2) {
      textShadowed(ctx, parts[0].toUpperCase(), 960, 380, 96, '#f4f1ea', { font: FONT_UI, bold: true });
      textShadowed(ctx, 'vs', 960, 452, 34, 'rgba(235,233,226,.8)', { font: FONT_UI });
      textShadowed(ctx, parts[1].toUpperCase(), 960, 530, 96, '#f4f1ea', { font: FONT_UI, bold: true });
    } else textShadowed(ctx, title.toUpperCase(), 960, 470, 96, '#f4f1ea', { font: FONT_UI, bold: true });
    const uw = clamp((u - .5) / .5, 0, 1) * 260;
    ctx.strokeStyle = accent; ctx.lineWidth = 6; ctx.lineCap = 'round'; ctx.beginPath(); ctx.moveTo(960 - uw / 2, parts.length === 2 ? 590 : 530); ctx.lineTo(960 + uw / 2, parts.length === 2 ? 590 : 530); ctx.stroke();
    const ty = parts.length === 2 ? 650 : 595;
    if (lines[1]) { ctx.globalAlpha = clamp((u - 1.1) / .4, 0, 1); textShadowed(ctx, lines[1], 960, ty, 32, C.text, { font: FONT_UI }); }
    if (lines[2]) { ctx.globalAlpha = clamp((u - 1.7) / .4, 0, 1); textShadowed(ctx, lines[2], 960, ty + 44, 28, accent, { font: FONT_UI }); }
  } else if (style === 'cta') {
    textShadowed(ctx, lines[0] || 'If this hit, like and subscribe.', 960, 400, 46, C.text, { font: FONT_UI });
    const press = clamp((u - 1.2) / .2, 0, 1), press2 = clamp((u - 2.2) / .2, 0, 1);
    rr(ctx, 760, 470, 190, 64, 32, press ? '#3478f6' : '#2a2e38'); textShadowed(ctx, 'LIKE', 855, 503, 28, '#fff', { glowBlur: 0, font: FONT_UI, bold: true });
    rr(ctx, 980, 470, 230, 64, 32, press2 ? '#3a3d45' : '#ff2d2d'); textShadowed(ctx, press2 ? 'SUBSCRIBED' : 'SUBSCRIBE', 1095, 503, 28, '#fff', { glowBlur: 0, font: FONT_UI, bold: true });
    const cx = u < 1.2 ? lerp(1300, 860, easeInOut(u / 1.2)) : u < 2.2 ? lerp(860, 1100, easeInOut(u - 1.2)) : 1100;
    const cy = u < 1.2 ? lerp(700, 515, easeInOut(u / 1.2)) : 515;
    ctx.fillStyle = '#fff'; ctx.strokeStyle = '#000'; ctx.lineWidth = 2;
    ctx.beginPath(); ctx.moveTo(cx, cy); ctx.lineTo(cx, cy + 34); ctx.lineTo(cx + 9, cy + 26); ctx.lineTo(cx + 16, cy + 40); ctx.lineTo(cx + 22, cy + 37); ctx.lineTo(cx + 15, cy + 24); ctx.lineTo(cx + 26, cy + 24); ctx.closePath(); ctx.fill(); ctx.stroke();
  } else {
    lines.forEach((l, i) => { ctx.globalAlpha = clamp((u - i * .6) / .5, 0, 1); textShadowed(ctx, l, 960, 460 + i * 74 - (lines.length - 1) * 30, i === 0 ? 64 : 40, C.text, { font: FONT_UI, bold: i === 0 }); });
  }
  ctx.globalAlpha = 1; ctx.restore();
}
