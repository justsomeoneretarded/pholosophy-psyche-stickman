// Renderer: turns a film (shot list) into frames. Exposes setup(), drawFrame(t), getCues().
'use strict';
let FILM, TL, CANVAS, CTX, K, BG, BGX, GLOW, GLOWX, GRAIN = [];
const DEFAULT_CAST = {
  hero: { kind: 'hero', hat: 'none' },
  demon: { kind: 'demon', scale: 1.12 },
  friend: { kind: 'friend', hat: 'beanie_orange', skin: '#d9c6a6' }
};

function setup(film, width = 1920) {
  FILM = film; FILM.cast = Object.fromEntries(Object.entries({ ...DEFAULT_CAST, ...(film.cast || {}) }).map(([id,c])=>[id,{...(DEFAULT_CAST[c.kind]||{}),...c}]));
  TL = new Timeline(film);
  K = width / STAGE_W;
  const mk = () => { const c = document.createElement('canvas'); c.width = width; c.height = Math.round(width * 9 / 16); return c; };
  CANVAS = document.getElementById('film') || mk(); CANVAS.width = width; CANVAS.height = Math.round(width * 9 / 16);
  CTX = CANVAS.getContext('2d');
  BG = mk(); BGX = BG.getContext('2d'); GLOW = mk(); GLOWX = GLOW.getContext('2d');
  for (let i = 0; i < 4; i++) {
    const g = document.createElement('canvas'); g.width = 256; g.height = 256; const x = g.getContext('2d');
    const im = x.createImageData(256, 256); const r = rng(91 + i);
    for (let j = 0; j < im.data.length; j += 4) { const v = r() * 255; im.data[j] = im.data[j + 1] = im.data[j + 2] = v; im.data[j + 3] = 255; }
    x.putImageData(im, 0, 0); GRAIN.push(g);
  }
  return TL.duration;
}

// ---------- world state for a shot ----------
function actorState(shot, a, u) {
  const cast = FILM.cast[a.id] || FILM.cast[a.kind] || {};
  const kind = a.kind || cast.kind || (a.id === 'demon' ? 'demon' : a.id === 'hero' ? 'hero' : 'extra');
  const set = setFor(shot), ground = set.ground || flatGround;
  const st = { ...cast, ...a, kind, seed: strHash(a.id) % 97 };
  let scale = (a.scale ?? cast.scale ?? (kind === 'demon' ? 1.12 : 1));
  if (a.depth === 'back') scale *= .7;
  st.scale = scale;
  const x0 = pct(a.x ?? 50), x1 = pct(a.to ?? a.x ?? 50);
  const mover = a.pose === 'walk' || a.pose === 'run' || (a.pose === 'umbrella' && a.to !== undefined);
  const moving = mover && Math.abs(x1 - x0) > 1;
  let x = x0, walked = u * (a.pose === 'run' ? 420 : 175), isMoving = a.pose === 'walk' || a.pose === 'run';
  let startBlend=1,stopBlend=0;
  if (mover && a.to!==undefined && !moving) {isMoving=false;walked=0;}
  if (moving) {
    const speed = (a.pose === 'run' ? 430 : 170) * scale * (a.speed || 1);
    const start = a.at ?? 0, dist = Math.abs(x1 - x0), T = dist / speed;
    const q = clamp((u - start) / T, 0, 1);
    startBlend=clamp((u-start)/.25,0,1);stopBlend=clamp((u-start-Math.max(0,T-.28))/.28,0,1);
    // gentle ease at both ends
    const ramp = .1;
    const e = q < ramp ? q * q / (2 * ramp * (1-ramp))
      : q > 1-ramp ? 1 - (1-q)*(1-q) / (2*ramp*(1-ramp))
      : (q-ramp/2)/(1-ramp);
    x = lerp(x0, x1, e); walked = Math.abs(x - x0) / scale; isMoving = q > 0 && q < 1;
  }
  const seated = ['sit','slump','type','write','standup','sitdown'].includes(a.pose) || a.seated === true;
  let fallbackSeat = false;
  if (seated) {
    if (a._fallback_seat) {
      fallbackSeat=true;
    } else if (Number.isFinite(a._seat_anchor)) {
      x=pct(a._seat_anchor);
    } else if (set.seatAnchors?.length) {
      x = set.seatAnchors.map(pct).reduce((best,q)=>Math.abs(q-x)<Math.abs(best-x)?q:best);
    } else if (!set.seat || !set.seat(x)) {
      let best = null;
      for (let q=20;q<STAGE_W-20;q+=4) {
        if (set.seat && set.seat(q) && (best===null || Math.abs(q-x)<Math.abs(best-x))) best=q;
      }
      if (best!==null) x=best;
      else fallbackSeat=true;
    }
  }
  st.wx = x; st.wy = ground(x) + (a.depth === 'back' ? -40 : 0);
  return { st, w: { walked, startBlend, stopBlend, moving: isMoving, dir: x1 >= x0 ? 1 : -1,
    seat: (fallbackSeat ? 58 : (set.seat ? set.seat(x) : 0))/scale,
    desk: (set.desk ? set.desk(x) : 0)/scale, typingDevice: a.pose==='type' && !['desk','office'].includes(shot.set) && !(shot.set==='scene' && (shot.scene?.elements||[]).some(e=>e.type==='desk' && e.laptop!==false)), fallbackSeat } };
}

function camera(shot, actors, u, t) {
  const cam = shot.camera || {}; const frame = cam.frame || 'wide';
  const subj = actors.find(a => a.st.id === cam.on) || actors.find(a => a.st.kind === 'hero') || actors[0];
  let zoom = 1, cx = 960, cy = 540;
  if (subj) {
    const s = subj.st.scale, hx = subj.st.wx, hy = subj.st.wy - 268 * s;
    const lie = subj.st.pose === 'lie';
    if (frame === 'medium') { zoom = 1.75; cx = hx; cy = hy + 150 * s; }
    else if (frame === 'close') { zoom = 2.85; cx = hx; cy = lie ? subj.st.wy - 160 : hy + 60 * s; }
    else if (frame === 'extreme') { zoom = 5; cx = hx; cy = hy + 6 * s; }
    else if (frame === 'two' && actors.length > 1) {
      const b = actors.find(a => a !== subj && a.st.kind !== 'extra') || actors[1];
      const d = Math.abs(b.st.wx - hx); zoom = clamp(1500 / (d + 760), 1, 2); cx = (hx + b.st.wx) / 2; cy = hy + 200;
    } else { cx = 960 + (hx - 960) * .06; }
    if (frame === 'close' && subj.st.pose === 'sit') cy += 40;
  }
  if (cam.x !== undefined) cx = pct(cam.x);
  const push = cam.push ?? .045;
  zoom *= 1 + push * easeInOut(u / shot.dur);
  cx += noise1(t * .22, 1) * 7 / zoom; cy += noise1(t * .19, 2) * 5 / zoom;
  if (cam.shake) { const at = cam.shake_at ?? 0, d = clamp(1 - (u - at) / .5, 0, 1) * (u >= at ? 1 : 0); cx += Math.sin(u * 70) * 14 * d * cam.shake; cy += Math.cos(u * 63) * 10 * d * cam.shake; }
  const hw = 960 / zoom, hh = 540 / zoom;
  cx = clamp(cx, hw, STAGE_W - hw); cy = clamp(cy, hh, STAGE_H - hh);
  return { zoom, cx, cy, frame, dof: cam.dof ?? (zoom >= 1.5) };
}

function applyCam(ctx, cam) { const z = cam.zoom * K; ctx.setTransform(z, 0, 0, z, CANVAS.width / 2 - cam.cx * z, CANVAS.height / 2 - cam.cy * z); }

function envFor(shot, u) {
  const e = { time: shot.time || 'night', weather: shot.weather || 'none', clock: shot.clock, screen: shot.screen, lamp: shot.lamp };
  const anim = (v, key) => { if (v === undefined) return 0; if (Array.isArray(v)) return lerp(v[0], v[1], easeInOut(clamp((u - (shot[key + '_at'] || 0)) / .8, 0, 1))); return v; };
  e.door = anim(shot.door, 'door'); e.fridge = anim(shot.fridge, 'fridge');
  return e;
}

function drawActor(ctx, a, P, cam, u, t, heads) {
  const st = a.st, demon = st.kind === 'demon';
  const talking = P.speaking || (a.shot.lines || []).some(l => l.who === st.id && u >= (l.at ?? 0) && u <= (l.at ?? 0) + Math.min(l.text.length / 28 + .2, l.dur ?? 99));
  const blink = !demon && ((t + st.seed * .37) % 3.9) < .13;
  const dcol = demonColor();
  const opts = { demon, demonColor: dcol, skin: st.skin || (st.kind === 'extra' ? '#b9b4a6' : C.cream), zoom: cam.zoom, t, blink, talking,
    detail: cam.zoom * (st.scale || 1) >= 1.9 ? 1 : 0, rain: a.shot.weather === 'rain', grin: demon && st.pose !== 'stand' };
  if (!demon) { const r = drawCharacter(ctx, st, P, opts); heads[st.id] = r.head; return; }
  // Demon: draw the black silhouette to an offscreen layer, then a blurred red copy behind it.
  const op = st.opacity ?? 1;
  GLOWX.setTransform(1, 0, 0, 1, 0, 0); GLOWX.clearRect(0, 0, GLOW.width, GLOW.height);
  GLOWX.setTransform(ctx.getTransform());
  const r = drawCharacter(GLOWX, st, P, { ...opts, noShadow: true, skin: '#060606' });
  heads[st.id] = r.head;
  ctx.save(); ctx.setTransform(1, 0, 0, 1, 0, 0);
  // red version of the silhouette
  BGX.save(); BGX.setTransform(1, 0, 0, 1, 0, 0); BGX.clearRect(0, 0, BG.width, BG.height);
  BGX.drawImage(GLOW, 0, 0); BGX.globalCompositeOperation = 'source-in'; BGX.fillStyle = dcol; BGX.fillRect(0, 0, BG.width, BG.height); BGX.restore();
  const pulse = .85 + .15 * Math.sin(t * 3.1);
  ctx.globalAlpha = op * pulse;
  ctx.filter = `blur(${Math.round(16 * K * Math.sqrt(cam.zoom))}px)`; ctx.drawImage(BG, 0, 0); ctx.drawImage(BG, 0, 0);
  ctx.filter = `blur(${Math.round(4 * K * Math.sqrt(cam.zoom))}px)`; ctx.drawImage(BG, 0, 0);
  ctx.filter = 'none'; ctx.globalAlpha = op;
  ctx.drawImage(GLOW, 0, 0);
  ctx.restore();
  // glowing eyes on top
  ctx.save(); ctx.globalAlpha = op; ctx.shadowColor = dcol; ctx.shadowBlur = 18 * K;
  const s = st.scale, [hx, hy] = r.head; const fdx = P.faceDx * 20 * s;
  ctx.strokeStyle = shade(dcol, .25); ctx.lineWidth = 6 * s; ctx.lineCap = 'round';
  for (const side of [-1, 1]) { const ex = hx + (side * 21) * s + fdx; ctx.beginPath(); ctx.moveTo(ex - side * 13 * s, hy + 2 * s); ctx.lineTo(ex + side * 11 * s, hy + 9 * s); ctx.stroke(); }
  if (opts.talking || opts.grin) { const open = opts.talking ? Math.abs(Math.sin(t * 10)) * 6 : 0; ctx.lineWidth = 5 * s; ctx.beginPath(); ctx.moveTo(hx - 24 * s + fdx, hy + 36 * s); ctx.quadraticCurveTo(hx + fdx, hy + (56 + open) * s, hx + 26 * s + fdx, hy + 33 * s); ctx.stroke(); }
  ctx.restore();
}

function demonColor() { return (FILM && FILM.demon_color) || '#ff2a2a'; }

// Colour grade per shot: saturation/brightness plus a tint, like the references' scene-by-scene looks.
const GRADES = {
  neutral: null,
  cold: { sat: .82, bri: .97, tint: '#4a6fa8', a: .14 },
  grey: { sat: .32, bri: .96, tint: '#808890', a: .08 },
  warm: { sat: 1.08, bri: 1.03, tint: '#ff9a40', a: .13 },
  pink: { sat: 1.0, bri: 1.0, tint: '#ff3fa0', a: .15 },
  sunset: { sat: 1.1, bri: 1.06, tint: '#ff9a40', a: .15 },
  night: { sat: .8, bri: .92, tint: '#2a3a8a', a: .16 },
  green: { sat: .95, bri: 1.0, tint: '#3fbf7a', a: .1 },
  red: { sat: .9, bri: .95, tint: '#c41e1e', a: .16 }
};
function applyGrade(ctx, name) {
  const g = GRADES[name]; if (!g) return;
  ctx.setTransform(1, 0, 0, 1, 0, 0);
  BGX.setTransform(1, 0, 0, 1, 0, 0); BGX.filter = 'none'; BGX.globalCompositeOperation = 'copy'; BGX.drawImage(CANVAS, 0, 0); BGX.globalCompositeOperation = 'source-over';
  ctx.filter = `saturate(${g.sat}) brightness(${g.bri})`; ctx.globalCompositeOperation = 'copy'; ctx.drawImage(BG, 0, 0);
  ctx.filter = 'none'; ctx.globalCompositeOperation = 'soft-light'; ctx.globalAlpha = Math.min(1, g.a * 3.2);
  ctx.fillStyle = g.tint; ctx.fillRect(0, 0, CANVAS.width, CANVAS.height);
  ctx.globalAlpha = 1; ctx.globalCompositeOperation = 'source-over';
}

function drawWorld(shot, u, t) {
  const env = envFor(shot, u); const set = setFor(shot);
  const actors = allocateSeatActors(shot,set).map(a => ({ ...actorState(shot, a, u), shot }));
  env.heldCupX = actors.filter(a=>a.st.pose==='drink' || a.st.hold==='cup').map(a=>a.st.wx);
  // targets for lean / grab
  for (const a of actors) {
    const tgt = actors.find(b => b.st.id === a.st.target) || actors.find(b => b !== a && b.st.kind === 'hero');
    if (tgt) { a.w.targetDx = tgt.st.wx - a.st.wx; a.w.targetShoulder = [(tgt.st.wx - a.st.wx) / a.st.scale + (tgt.st.wx > a.st.wx ? -40 : 40), (-210 * tgt.st.scale) / a.st.scale]; }
    // look at the other main character in the shot (demons are ignored unless they speak)
    const others = actors.filter(b => b !== a && b.st.kind !== 'extra' && b.st.depth !== 'back' && (b.st.kind !== 'demon' || (shot.lines || []).some(l => l.who === b.st.id)));
    const lookT = actors.find(b => b.st.id === a.st.look_at) || others[0];
    if (lookT && a.st.kind !== 'demon') a.w.lookDx = Math.sign(lookT.st.wx - a.st.wx) || 0;
    a.P = evalPose(a.st, u - (a.st.at && !['walk', 'run', 'umbrella'].includes(a.st.pose) ? a.st.at : 0), shot.dur, a.w);
  }
  const cam = camera(shot, actors, u, t);
  const ctx = CTX; ctx.setTransform(1, 0, 0, 1, 0, 0); ctx.filter = 'none'; ctx.globalAlpha = 1;
  ctx.fillStyle = '#000'; ctx.fillRect(0, 0, CANVAS.width, CANVAS.height);
  const back = actors.filter(a => a.st.depth === 'back');
  const front = actors.filter(a => a.st.depth !== 'back').sort((a, b) => (a.st.kind === 'demon' ? -1 : 0) - (b.st.kind === 'demon' ? -1 : 0));
  const heads = {};
  const paintBg = (c) => { applyCam(c, cam); set.draw(c, env, t); drawItems(c, shot.items, shot, t); for (const a of back) drawActor(c, a, a.P, cam, u, t, heads); };
  if (cam.dof) {
    BGX.setTransform(1, 0, 0, 1, 0, 0); BGX.clearRect(0, 0, BG.width, BG.height); paintBg(BGX);
    ctx.setTransform(1, 0, 0, 1, 0, 0);
    const blur = clamp((cam.zoom - 1.2) * 7, 3, 22) * K;
    ctx.filter = `blur(${blur.toFixed(1)}px) brightness(0.8)`; ctx.drawImage(BG, 0, 0); ctx.filter = 'none';
  } else paintBg(ctx);
  // A visible support is mandatory when an authored sitting action has no seat.
  for (const a of front) if (a.w.fallbackSeat) {
    applyCam(ctx,cam);
    const x=a.st.wx,y=a.st.wy,s=a.st.scale,top=y-58;
    ctx.strokeStyle='#6a6260';ctx.lineWidth=6;
    for(const side of [-1,1]) {ctx.beginPath();ctx.moveTo(x+side*34*s,top);ctx.lineTo(x+side*34*s,y);ctx.stroke();}
    rr(ctx,x-55*s,top-4,110*s,12*s,5*s,'#302a28','#71625a',2);
  }
  for (const a of front) { applyCam(ctx, cam); drawActor(ctx, a, a.P, cam, u, t, heads); }
  // seat edge in front of seated hips: makes sitting read from a front view
  if (set.seatFront) for (const a of front) {
    const sitting = ['sit', 'slump', 'type'].includes(a.st.pose) || (a.st.pose === 'phone' && a.st.seated);
    if (!sitting || !a.w.seat) continue;
    applyCam(ctx, cam); const s = a.st.scale;
    rr(ctx, a.st.wx - 78 * s, a.st.wy - (a.w.seat + 6) * s, 156 * s, 20 * s, 7 * s, set.seatFront[0], set.seatFront[1], 2.4 / cam.zoom);
  }
  if (set.fg) { applyCam(ctx, cam); set.fg(ctx, env, t); }
  if (shot.weather === 'rain' && setFor(shot).outdoor) { applyCam(ctx, cam); rainFront(ctx, t); }
  applyGrade(ctx, shot.grade);
  // Lighting: vignette, plus a red pulse while the demon speaks
  ctx.setTransform(1, 0, 0, 1, 0, 0);
  const W = CANVAS.width, H = CANVAS.height;
  const vg = ctx.createRadialGradient(W / 2, H * .52, H * .35, W / 2, H / 2, W * .72);
  vg.addColorStop(0, 'rgba(0,0,0,0)'); vg.addColorStop(1, `rgba(0,0,0,${shot.light === 'dark' ? .85 : .6})`);
  ctx.fillStyle = vg; ctx.fillRect(0, 0, W, H);
  const demonTalk = (shot.lines || []).some(l => (FILM.cast[l.who] || {}).kind === 'demon' && /[a-z]/i.test(l.text) && u >= (l.at ?? 0) && u <= (l.at ?? 0) + 1.2);
  if (demonTalk) { const r = ctx.createRadialGradient(W / 2, H / 2, H * .3, W / 2, H / 2, W * .7); r.addColorStop(0, rgba(demonColor(), 0)); r.addColorStop(1, rgba(demonColor(), .2)); ctx.fillStyle = r; ctx.fillRect(0, 0, W, H); }
  // heads to screen space for dialogue
  const z = cam.zoom; const sc = {};
  for (const [id, [hx, hy]] of Object.entries(heads)) sc[id] = [(hx - cam.cx) * z + 960, (hy - cam.cy) * z + 540 - 70 * z * ((actors.find(a => a.st.id === id) || {}).st?.scale || 1)];
  return { heads: sc, cam };
}

function drawFrame(t) {
  const shot = TL.at(t); const u = t - shot.start;
  const ctx = CTX;
  let heads = {};
  if (shot.camera && shot.camera.frame === 'insert') {
    ctx.setTransform(1, 0, 0, 1, 0, 0);
    drawInsert(ctx, shot, u, t, K);
    applyGrade(ctx, shot.grade);
  } else if (shot.camera && shot.camera.frame === 'phone') {
    const w = drawWorld({ ...shot, actors: [], camera: { frame: 'wide', dof: true, push: 0 } }, u, t);
    ctx.setTransform(1, 0, 0, 1, 0, 0); ctx.fillStyle = 'rgba(0,0,0,.45)'; ctx.fillRect(0, 0, CANVAS.width, CANVAS.height);
    drawPhonePOV(ctx, shot, u, t, K);
    applyGrade(ctx, shot.grade);
  } else if (shot.card && !shot.card.over) {
    ctx.setTransform(1, 0, 0, 1, 0, 0); ctx.fillStyle = '#070708'; ctx.fillRect(0, 0, CANVAS.width, CANVAS.height);
    if (shot.actors && shot.actors.length) { const w = drawWorld({ ...shot, set: 'void' }, u, t); heads = w.heads; }
    const g = ctx.createRadialGradient(CANVAS.width / 2, CANVAS.height * .45, 10, CANVAS.width / 2, CANVAS.height * .45, CANVAS.width * .5);
    g.addColorStop(0, 'rgba(255,235,200,.07)'); g.addColorStop(1, 'rgba(0,0,0,0)'); ctx.fillStyle = g; ctx.fillRect(0, 0, CANVAS.width, CANVAS.height);
    drawCard(ctx, shot, u, t, K);
  } else {
    heads = drawWorld(shot, u, t).heads;
    if (shot.card && shot.card.over) { ctx.setTransform(1, 0, 0, 1, 0, 0); drawCard(ctx, shot, u, t, K); }
  }
  ctx.setTransform(1, 0, 0, 1, 0, 0);
  drawBig(ctx, shot, u, K);
  drawLines(ctx, shot, u, heads, K, FILM);
  drawHud(ctx, FILM, shot, u, K);
  // letterbox
  const bar = Math.round(48 * K); ctx.fillStyle = '#000'; ctx.fillRect(0, 0, CANVAS.width, bar); ctx.fillRect(0, CANVAS.height - bar, CANVAS.width, bar);
  // transitions
  const tr = shot.transition || 'cut';
  let black = 0;
  if (tr === 'fade') black = Math.max(black, 1 - clamp(u / .6, 0, 1));
  if (shot.dip_out) black = Math.max(black, clamp((u - (shot.dur - .6)) / .6, 0, 1));
  if (t < .5) black = Math.max(black, 1 - t / .5);
  if (t > TL.duration - .8) black = Math.max(black, (t - (TL.duration - .8)) / .8);
  if (black > 0) { ctx.fillStyle = `rgba(0,0,0,${clamp(black, 0, 1)})`; ctx.fillRect(0, 0, CANVAS.width, CANVAS.height); }
  if (tr === 'flash' && u < .25) { ctx.fillStyle = `rgba(255,250,240,${.85 * (1 - u / .25)})`; ctx.fillRect(0, 0, CANVAS.width, CANVAS.height); }
  // film grain
  ctx.globalAlpha = .045; ctx.globalCompositeOperation = 'overlay';
  const g = GRAIN[Math.floor(t * 24) % 4]; ctx.fillStyle = ctx.createPattern(g, 'repeat'); ctx.fillRect(0, 0, CANVAS.width, CANVAS.height);
  ctx.globalAlpha = 1; ctx.globalCompositeOperation = 'source-over';
}

// ---------- sound cues derived from the picture ----------
function getCues() {
  const cues = [], music = [], ambience = [];
  const add = (t, name, vol = 1) => cues.push({ t: +t.toFixed(3), name, vol });
  for (const shot of TL.shots) {
    const s0 = shot.start;
    music.push({ start: s0, end: shot.end, level: shot.music || (shot.card ? 'high' : 'mid') });
    const outdoor = ['street', 'park', 'hill', 'rooftop', 'bus_stop'].includes(shot.set);
    const amb = shot.card ? 'none' : (shot.camera && shot.camera.frame === 'insert') ? 'room' : shot.weather === 'rain' ? (outdoor ? 'rain' : 'rain_in') : shot.weather === 'snow' ? 'wind' : shot.set === 'cafe' ? 'cafe' : shot.set === 'office' ? 'office' : outdoor ? 'city' : 'room';
    ambience.push({ start: s0, end: shot.end, kind: amb });
    for (const c of shot.sfx || []) add(s0 + (c.at ?? 0), c.name, c.vol ?? 1);
    if (shot.transition === 'flash') add(s0, 'impact', .9);
    if (shot.card && (shot.card.style === 'red')) add(s0, 'impact', 1);
    if (shot.card && shot.card.style === 'cta') { add(s0 + 1.35, 'click', .8); add(s0 + 2.35, 'click', .8); }
    for (const l of shot.lines || []) {
      const at = s0 + (l.at ?? 0);
      const demon = (FILM.cast[l.who] || {}).kind === 'demon';
      if (demon && /[a-z]/i.test(l.text)) { add(at - .15, 'whoosh', .5); add(at, 'drone', .7); }
      else if (l.who === 'narrator' && l.voice_file) cues.push({ t: +at.toFixed(3), name: 'voice', file: l.voice_file, vol: 1 });
      else if (l.who !== 'narrator' && l.who !== 'caption' && (l.style || 'bubble') === 'bubble') {
        add(at, 'pop', .35);
        for (let i = 2; i < l.text.length; i += 3) add(at + i / (l.cps || 22), 'blip', .16);
      }
    }
    if (shot.big && shot.big.text) add(s0 + (shot.big.at ?? .2), 'impact', .55);
    if (shot.card && shot.card.style === 'logo') add(s0 + .1, 'impact', .8);
    if (shot.card && shot.card.style === 'quote') add(s0 + .1, 'riser', .25);
    if (shot.insert) {
      const ins = shot.insert;
      if (ins.type === 'note' || ins.type === 'letter') for (let q = .4; q < .4 + (ins.text || '').length / 9; q += .32) add(s0 + q, 'scribble', .45);
      if (ins.type === 'calendar') { const n = (ins.marked || 30) - (ins.from || 1) + 1, T = Math.max(1, shot.dur - .8); for (let i = 0; i < n; i++) add(s0 + T * (i + 1) / n, 'scribble', .3); }
      if (ins.type === 'photo') add(s0 + .2, 'page', .6);
    }
    if (shot.phone && shot.phone.app === 'off' && shot.camera && shot.camera.frame === 'phone') add(s0 + (shot.phone.off_at ?? 1.4), 'click', .9);
    for (const a of shot.actors || []) {
      const kind = (FILM.cast[a.id] || {}).kind || a.kind;
      if (a.pose === 'write') {
        for(let q=.6;q<Math.min(shot.dur,3.5);q+=.32) add(s0+q,'scribble',.22);
      }
      if (a.pose === 'type') for(let q=.35;q<shot.dur-.3;q+=.24) add(s0+q,'typing',.18);
      if (a.pose === 'show' || a.pose === 'read') add(s0+.35,'page',.25);
      if (a.pose === 'fall') add(s0 + (a.at || 0) + .45, 'thud', 1);
      if (a.pose === 'walk' || a.pose === 'run' || (a.pose === 'umbrella' && a.to !== undefined)) {
        const x0 = pct(a.x ?? 50), x1 = pct(a.to ?? a.x ?? 50); const run = a.pose === 'run';
        const speed = (run ? 430 : 170) * (a.scale || 1) * (a.speed || 1), dist = Math.abs(x1 - x0);
        const T = dist > 1 ? dist / speed : shot.dur, step = run ? .3 : .44;
        for (let q = (a.at || 0) + .1; q < Math.min(shot.dur, (a.at || 0) + T); q += step) add(s0 + q, 'footsteps', (kind === 'demon' ? 0 : (a.depth === 'back' ? .3 : .55)) * (run ? 1.1 : 1));
      }
    }
    if (Array.isArray(shot.door)) add(s0 + (shot.door_at || 0), 'door', .8);
    if (Array.isArray(shot.fridge)) add(s0 + (shot.fridge_at || 0), 'door', .5);
    const ph = shot.phone;
    if (ph && shot.camera && shot.camera.frame === 'phone') {
      for (const m of ph.messages || []) if ((m.at ?? 0) > .05) add(s0 + m.at, m.from === 'me' ? 'send' : 'notification', .8);
      for (const n of ph.notifications || []) add(s0 + (n.at ?? 0), 'notification', .8);
      if (ph.typing) {
        const ty = ph.typing, at = ty.at ?? .3, cps = ty.cps || 11, n = ty.text.length;
        for (let i = 0; i < n; i++) add(s0 + at + i / cps, 'typing', .35);
        if (ty.action === 'delete') { const del = at + n / cps + (ty.pause ?? .7); for (let i = 0; i < n; i += 2) add(s0 + del + i / (cps * 2.4), 'typing', .25); }
        if (ty.action === 'send') add(s0 + at + n / cps + .35, 'send', .8);
      }
      if (ph.app === 'call') { const end = Math.min(shot.dur, ph.call?.decline_at ?? ph.call?.answer_at ?? shot.dur); for (let q = .1; q < end; q += 1.6) add(s0 + q, 'buzz', .7); if (ph.call?.decline_at !== undefined) add(s0 + ph.call.decline_at, 'click', .6); }
      if (ph.app === 'alarm') for (let q = .05; q < shot.dur; q += .5) add(s0 + q, 'alarm', .45);
    }
  }
  cues.sort((a, b) => a.t - b.t);
  return { duration: TL.duration, cues, music, ambience };
}

if (typeof window !== 'undefined') Object.assign(window, { setup, drawFrame, getCues });
