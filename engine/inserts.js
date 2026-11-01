// Insert shots: close-ups of objects that carry the story (a note being written, a calendar being
// crossed off, a photo, a letter). Drawn in screen space; shot.insert = {type, ...}.
'use strict';

function deskBackground(ctx, tint = '#1a1b20') {
  const g = ctx.createLinearGradient(0, 0, 0, 1080); g.addColorStop(0, shade(tint, .06)); g.addColorStop(1, shade(tint, -.25));
  ctx.fillStyle = g; ctx.fillRect(0, 0, 1920, 1080);
  ctx.strokeStyle = 'rgba(255,255,255,.035)'; ctx.lineWidth = 2;
  for (let y = 60; y < 1080; y += 64) { ctx.beginPath(); ctx.moveTo(0, y); ctx.lineTo(1920, y + 8); ctx.stroke(); }
}

function hand(ctx, x, y, angle = -.5, sleeve = '#3b3d43') {
  ctx.save(); ctx.translate(x, y); ctx.rotate(angle);
  ctx.fillStyle = sleeve; ctx.strokeStyle = C.ink; ctx.lineWidth = 3;
  roundRect(ctx, -46, 60, 92, 260, 20); ctx.fill(); ctx.stroke();
  ctx.fillStyle = C.cream; ctx.beginPath(); ctx.ellipse(0, 20, 52, 62, 0, 0, Math.PI * 2); ctx.fill(); ctx.stroke();
  ctx.beginPath(); ctx.ellipse(-30, -26, 16, 30, -.5, 0, Math.PI * 2); ctx.fill(); ctx.stroke();
  ctx.restore();
}

function drawInsert(ctx, shot, u, t, K) {
  const ins = shot.insert || { type: 'note' };
  ctx.save(); ctx.scale(K, K);
  const drift = noise1(t * .3, 7) * 6;
  if (ins.type === 'note' || ins.type === 'letter') {
    deskBackground(ctx, '#1b1c22');
    // a phone lying face down next to it
    ctx.save(); ctx.translate(1340, 600); ctx.rotate(.12); rr(ctx, -70, -140, 140, 280, 22, '#0f1013', '#3a3d45', 3); ctx.restore();
    ctx.save(); ctx.translate(820 + drift, 560); ctx.rotate(-.04);
    ctx.shadowColor = 'rgba(0,0,0,.5)'; ctx.shadowBlur = 30;
    rr(ctx, -330, -260, 660, 520, 8, '#c08a3a'); ctx.shadowBlur = 0;
    rr(ctx, -318, -248, 316, 496, 4, '#f2eee3'); rr(ctx, 2, -248, 316, 496, 4, '#f5f1e7');
    ctx.strokeStyle = '#c9c3b2'; ctx.lineWidth = 2;
    for (let y = -170; y < 230; y += 46) { ctx.beginPath(); ctx.moveTo(40, y); ctx.lineTo(290, y); ctx.stroke(); }
    // the text writes itself in a hand font, one character at a time
    const text = ins.text || '...';
    const n = Math.floor(clamp((u - .4) * 9, 0, text.length));
    ctx.fillStyle = '#26262b'; ctx.font = `52px ${FONT_HAND}`; ctx.textAlign = 'left'; ctx.textBaseline = 'alphabetic';
    const words = wrapLines(ctx, text, 270); let shown = 0, pen = [-290, -150];
    words.forEach((line, i) => {
      const part = line.slice(0, Math.max(0, n - shown)); shown += line.length + 1;
      ctx.save(); ctx.translate(-290, -150 + i * 70); ctx.rotate(-.05); ctx.fillText(part, 0, 0);
      if (part.length) pen = [-290 + ctx.measureText(part).width, -150 + i * 70];
      ctx.restore();
    });
    ctx.restore();
    if (n < text.length) hand(ctx, 820 + pen[0] + 40 + Math.sin(u * 20) * 6, 560 + pen[1] + 70, -.35);
    else hand(ctx, 1000, 980, -.25);
  } else if (ins.type === 'calendar') {
    deskBackground(ctx, '#202228');
    const days = ins.days || 30, upto = ins.marked || days, from = ins.from || 1;
    ctx.save(); ctx.translate(960 + drift, 560);
    ctx.shadowColor = 'rgba(0,0,0,.5)'; ctx.shadowBlur = 30; rr(ctx, -420, -380, 840, 760, 18, '#f3efe6'); ctx.shadowBlur = 0;
    rr(ctx, -420, -380, 840, 110, 18, '#c8383b'); ctx.fillStyle = '#c8383b'; ctx.fillRect(-420, -300, 840, 30);
    textShadowed(ctx, (ins.month || 'NOV').toUpperCase(), 0, -322, 54, '#fff', { font: FONT_UI, bold: true, glowBlur: 0 });
    const cw = 112, ch = 92;
    const lastShown = Math.floor(lerp(from - 1, upto, clamp(u / Math.max(1, shot.dur - .8), 0, 1)));
    for (let d = 1; d <= days; d++) {
      const c = (d - 1) % 7, r = Math.floor((d - 1) / 7), x = -392 + c * cw, y = -250 + r * ch;
      ctx.strokeStyle = '#d8d2c4'; ctx.lineWidth = 2; ctx.strokeRect(x, y, cw - 8, ch - 8);
      ctx.fillStyle = '#8b8577'; ctx.font = `24px ${FONT_UI}`; ctx.textAlign = 'left'; ctx.fillText(String(d), x + 8, y + 26);
      if (d <= lastShown) {
        ctx.strokeStyle = ins.mark === 'x' ? '#c8383b' : '#2f9a5a'; ctx.lineWidth = 7; ctx.lineCap = 'round'; ctx.beginPath();
        if (ins.mark === 'x') { ctx.moveTo(x + 22, y + 22); ctx.lineTo(x + cw - 30, y + ch - 30); ctx.moveTo(x + cw - 30, y + 22); ctx.lineTo(x + 22, y + ch - 30); }
        else { ctx.moveTo(x + 26, y + 46); ctx.lineTo(x + 46, y + 64); ctx.lineTo(x + cw - 28, y + 24); }
        ctx.stroke();
      }
    }
    const d = clamp(lastShown, 1, days), c = (d - 1) % 7, r = Math.floor((d - 1) / 7);
    ctx.restore();
    hand(ctx, 960 + drift - 392 + c * cw + 120, 560 - 250 + r * ch + 140, -.4);
  } else if (ins.type === 'photo') {
    deskBackground(ctx, '#1e1d22');
    ctx.save(); ctx.translate(960 + drift, 540); ctx.rotate(-.06);
    ctx.shadowColor = 'rgba(0,0,0,.55)'; ctx.shadowBlur = 34; rr(ctx, -300, -340, 600, 680, 6, '#f6f3ec'); ctx.shadowBlur = 0;
    const g = ctx.createLinearGradient(0, -300, 0, 200); g.addColorStop(0, '#f2a86a'); g.addColorStop(1, '#a5566a');
    ctx.fillStyle = g; ctx.fillRect(-264, -304, 528, 500);
    const cast = Object.entries(FILM.cast || {}).filter(([id, c]) => (ins.who || ['hero']).includes(id));
    cast.forEach(([id, c], i) => {
      ctx.save(); ctx.translate(-80 * (cast.length - 1) + i * 160, 196); ctx.scale(.6, .6);
      const P = basePose(); P.hands = [[-54, -108], [54, -108]];
      drawCharacter(ctx, { ...c, wx: 0, wy: 0, scale: 1, mood: 'happy' }, P, { zoom: 1, t, noShadow: true, skin: c.skin || C.cream, detail: 1 });
      ctx.restore();
    });
    textShadowed(ctx, ins.text || '', 0, 268, 40, '#2a2a2e', { glowBlur: 0 });
    ctx.restore();
  }
  ctx.restore();
}
