// Characters: rig, poses, faces, hair and clothes. Local coordinates: origin at the feet, y up is negative.
'use strict';

const RIG = { pelvisY: -100, shoulderX: 46, shoulderY: -110, headY: -168, headR: 64, hipX: 21,
  thigh: 51, shin: 50, upper: 52, fore: 50, legW: 31, armW: 25 };

// Faces. brow: [inner tilt (+ = inner end up), extra raise of one brow]; lid: upper-lid cover 0..1.
const MOODS = {
  neutral:    { brow: [0, 0], browY: 0, eyes: 'open', lid: .05, mouth: 'flat' },
  flat:       { brow: [0, 0], browY: 6, eyes: 'open', lid: .48, mouth: 'flat' },
  bored:      { brow: [-.05, 0], browY: 7, eyes: 'open', lid: .55, mouth: 'flat', look: [.6, 0] },
  sad:        { brow: [.3, 0], browY: -2, eyes: 'open', lid: .22, mouth: 'frown', look: [0, 3], tilt: .06 },
  hurt:       { brow: [.42, 0], browY: -4, eyes: 'teary', lid: .12, mouth: 'wavy', look: [0, 2] },
  crying:     { brow: [.5, 0], browY: -3, eyes: 'squeeze', lid: 0, mouth: 'wail', tears: true, shake: 1 },
  worried:    { brow: [.4, 0], browY: -6, eyes: 'open', lid: 0, mouth: 'wavy' },
  nervous:    { brow: [.35, 0], browY: -4, eyes: 'small', lid: 0, mouth: 'wavy', sweat: true, shake: .5 },
  scared:     { brow: [.45, 0], browY: -11, eyes: 'wide', lid: 0, mouth: 'teeth', shake: .8 },
  shocked:    { brow: [.1, 0], browY: -13, eyes: 'wide', lid: 0, mouth: 'o' },
  happy:      { brow: [0, 0], browY: -7, eyes: 'happy', lid: 0, mouth: 'smile', blush: .35 },
  content:    { brow: [.05, 0], browY: -3, eyes: 'closed', lid: 0, mouth: 'smile', blush: .25 },
  laughing:   { brow: [.05, 0], browY: -9, eyes: 'happy', lid: 0, mouth: 'laugh', blush: .4, bounce: 1 },
  shy:        { brow: [.25, 0], browY: -3, eyes: 'open', lid: .2, mouth: 'small', blush: .8, look: [.5, 3] },
  love:       { brow: [.15, 0], browY: -6, eyes: 'open', lid: .1, mouth: 'smile', blush: .9, sparkle: true },
  hopeful:    { brow: [.25, 0], browY: -8, eyes: 'open', lid: 0, mouth: 'small', look: [0, -3], sparkle: true },
  relieved:   { brow: [.2, 0], browY: -3, eyes: 'closed', lid: 0, mouth: 'smile' },
  determined: { brow: [-.32, 0], browY: 5, eyes: 'open', lid: .25, mouth: 'tight' },
  angry:      { brow: [-.48, 0], browY: 6, eyes: 'open', lid: .15, mouth: 'teeth' },
  smirk:      { brow: [0, -.25], browY: 0, eyes: 'open', lid: .4, mouth: 'smirk' },
  suspicious: { brow: [-.15, -.3], browY: 3, eyes: 'open', lid: .45, mouth: 'flat', look: [.8, 0] },
  tired:      { brow: [.08, 0], browY: 7, eyes: 'open', lid: .62, mouth: 'flat', bags: true },
  asleep:     { brow: [0, 0], browY: 4, eyes: 'closed', lid: 0, mouth: 'small' }
};

// ---------- poses ----------
function basePose() {
  return { pelvis: [0, RIG.pelvisY], lean: 0, rot: 0, lift: 0, headDy: 0, headTilt: 0, shoulderDy: 0,
    feet: [[-24, 0], [24, 0]], hands: [[-54, -108], [54, -108]], look: [0, 0], faceDx: 0, squash: 1,
    hold: null, phoneGlow: 0, kneelDepth: 0, sideSit: 0 };
}

function breathe(P, u, seed, amt = 1) { const b = Math.sin(u * 2.1 + seed); P.squash = 1 + b * .012 * amt; P.shoulderDy = b * 1.5 * amt; }

const POSES = {
  stand(P, a, u, d, w) {
    breathe(P, u, a.seed);
    const s = noise1(u * .6, a.seed) * 3;
    P.hands = [[-53 + s, -106], [53 + s, -106]];
    P.headTilt = noise1(u * .35, a.seed + 3) * .03;
  },
  pockets(P, a, u, d, w) { POSES.stand(P, a, u, d, w); P.hands = [[-44, -96], [44, -96]]; P.handsHidden = true; },
  walk(P, a, u, d, w, run) {
    if (!w.moving) {POSES.stand(P,a,u,d,w);P.feet=[[-24,0],[24,0]];P.faceDx=w.dir*.75;return;}
    const stride = run ? 190 : 120, lift = run ? 34 : 17;
    const phase = w.walked / stride, dir = w.dir, stance = run ? .48 : .6;
    for (let i = 0; i < 2; i++) {
      const cycle = ((phase + i * .5) % 1 + 1) % 1;
      const swing = clamp((cycle-stance)/(1-stance),0,1);
      // In stance, the foot moves back exactly as far as the root moves forward.
      // walked is measured in character-local units, including character scale.
      const fx = dir * (cycle < stance
        ? stride * (stance/2-cycle)
        : stride * stance * (-.5 + easeInOut(swing)));
      const fy = cycle < stance ? 0 : -Math.sin(Math.PI*swing)*lift;
      P.feet[i] = [(i ? 9 : -9) + fx, fy];
      const ph = 2 * Math.PI * (phase + i * .5);
      const sw = -dir * Math.sin(ph) * (run ? 30 : 18);
      P.hands[i] = run ? [(i ? 22 : -22) + sw, -150 + Math.abs(sw) * .3] : [(i ? 40 : -40) + sw, -106];
    }
    if (!w.moving) { POSES.stand(P, a, u, d, w); P.faceDx = dir * .75; return; }
    P.profile = dir;
    P.pelvis[1] = -86 + Math.abs(Math.cos(2 * Math.PI * phase)) * (run ? 6 : 3);
    P.lean = dir * (run ? .14 : .04);
    P.faceDx = dir * .85;
    const blend=Math.min(w.startBlend??1,1-(w.stopBlend??0));
    P.pelvis[1]=lerp(RIG.pelvisY,P.pelvis[1],blend);P.lean*=blend;
    for(let i=0;i<2;i++){P.feet[i]=[lerp(i?24:-24,P.feet[i][0],blend),P.feet[i][1]*blend];P.hands[i]=[lerp(i?53:-53,P.hands[i][0],blend),lerp(-106,P.hands[i][1],blend)];}
  },
  run(P, a, u, d, w) { POSES.walk(P, a, u, d, w, true); },
  sit(P, a, u, d, w) {
    breathe(P, u, a.seed);
    const h = w.seat || 58, dir = a.facing || 0;
    P.pelvis = [0, -h - 10];
    if (dir) {
      // Side-on sitting: thighs point the way the character faces, shins hang down.
      P.sideSit = dir;
      const fy = Math.min(0, -h + 56);
      P.feet = [[dir * 50, fy], [dir * 62, fy]];
      P.hands = [[dir * 30 - 10, -h - 16], [dir * 44, -h - 18]];
      P.faceDx = dir * .8;
    } else {
      const fy = Math.min(0, -h + 66);
      P.feet = [[-30, fy], [30, fy]];
      P.hands = [[-36, -h - 6], [36, -h - 6]];
      P.thighShort = true;
    }
  },
  slump(P, a, u, d, w) {
    POSES.sit(P, a, u, d, w);
    P.headDy = 16; P.shoulderDy = 6; P.lean = (a.facing || 0) * .12;
    if (!P.sideSit) P.hands = [[-16, -(w.seat || 58) + 18], [16, -(w.seat || 58) + 18]];
    P.look = [0, 4]; P.headTilt = .08;
  },
  hugknees(P, a, u, d, w) {
    breathe(P, u, a.seed, .6);
    P.pelvis = [0, -40]; P.thighShort = true;
    P.feet = [[-22, 0], [22, 0]]; P.hands = [[-20, -78], [20, -78]];
    P.headDy = 14; P.look = [0, 3]; P.kneesUp = true;
  },
  lie(P, a, u, d, w) {
    breathe(P, u, a.seed);
    P.rot = -Math.PI / 2 * (a.facing === 1 ? -1 : 1);
    P.lieH = (w.seat || 0) + 62;
    P.hands = [[-40, -120], [40, -120]];
  },
  phone(P, a, u, d, w) {
    if (a.seated) POSES.sit(P, a, u, d, w); else POSES.stand(P, a, u, d, w);
    const by = P.pelvis[1] - 70, sd = P.sideSit;
    P.hands = sd ? [[sd * 34, by - 4], [sd * 50, by - 8]] : [[-12, by - 4], [16, by - 8]];
    P.hold = P.hold || 'phone'; P.look = [sd * .5, 4]; P.phoneGlow = 1; P.headDy = 3;
    // thumb scroll
    P.hands[1][1] += Math.sin(u * 6) * 1.5;
  },
  call(P, a, u, d, w) {
    if (a.seated) POSES.sit(P, a, u, d, w); else POSES.stand(P, a, u, d, w);
    P.hands[1] = [36, -270]; P.hold = 'phone_ear';
  },
  type(P, a, u, d, w) {
    POSES.sit(P, a, u, d, w);
    const tap = i => Math.sin(u * 17 + i * 2.1) * 3 + noise1(u * 4, i + a.seed) * 4;
    if (w.desk) {
      const y = -w.desk - 4, sd = P.sideSit;
      P.hands = sd ? [[sd * 52 + tap(0), y], [sd * 74 + tap(2) * 1.4, y + Math.abs(tap(3)) * .5]]
        : [[-34 + tap(0), y + Math.abs(tap(1)) * .6], [40 + tap(2) * 1.6, y + Math.abs(tap(3)) * .6]];
    } else {
      const y = -(w.seat || 58) - 26;
      P.hands = [[-28, y], [22 + tap(2) * 1.5, y - 4 + tap(3) * .5]];
      P.lapBook = true;
    }
    P.look = [P.sideSit * .6, 4]; P.headDy = 4;
    P.typingLaptop=w.typingDevice===true;P.keyboardY=w.desk?-w.desk:P.pelvis[1]-18;
  },
  drink(P, a, u, d, w) {
    if (a.seated || w.seat) POSES.sit(P, a, u, d, w); else POSES.stand(P, a, u, d, w);
    const sip = Math.max(0, Math.sin(u * 1.2)) ** 3;
    const sd = P.sideSit || 0;
    P.hands[1] = [lerp(sd ? sd * 46 : 40, 18 + sd * 20, sip), lerp(P.pelvis[1] - 50, -232, sip)];
    P.hold = 'cup'; P.look = [sd * .5, sip * -2];
  },
  reach(P, a, u, d, w) {
    POSES.stand(P, a, u, d, w);
    const k = easeOut(u / Math.min(1.2, d * .5));
    P.hands[1] = [lerp(53, 44, k) + Math.sin(u * 9) * 3 * k, lerp(-106, -395, k)];
    P.lift = 10 * k; P.look = [.3, -5 * k];
  },
  reachout(P, a, u, d, w) {
    if (a.seated) POSES.sit(P, a, u, d, w); else POSES.stand(P, a, u, d, w);
    const dir = w.targetDx >= 0 ? 1 : -1, k = easeOut(u / .9);
    P.hands[dir > 0 ? 1 : 0] = [dir * lerp(53, 112, k), lerp(-106, -180, k)];
    P.faceDx = dir * .7; P.lean = dir * .05 * k;
  },
  wave(P, a, u, d, w) {
    POSES.stand(P, a, u, d, w);
    const k = easeOut(u / .35);
    P.hands[1] = [lerp(53, 92, k) + Math.sin(u * 11) * 16 * k, lerp(-106, -262, k)];
  },
  knock(P, a, u, d, w) {
    POSES.stand(P, a, u, d, w);
    const dir = a.facing || 1, hit = Math.abs(Math.sin(u * 9)) * (u % 1.6 < .9 ? 1 : 0);
    P.hands[dir > 0 ? 1 : 0] = [dir * (80 + hit * 14), -205]; P.faceDx = dir * .8; P.profile = dir;
  },
  fall(P, a, u, d, w) {
    const k = easeIn(clamp(u / .45, 0, 1));
    POSES.kneel(P, a, u, d, w, k);
    P.pelvis[1] += Math.sin(clamp((u - .45) / .3, 0, 1) * Math.PI) * 6;
    P.hands = [[lerp(-53, -64, k), lerp(-106, -2, k)], [lerp(53, 64, k), lerp(-106, -2, k)]];
    P.headDy = lerp(0, 30, k);
  },
  kneel(P, a, u, d, w, kk) {
    const k = kk === undefined ? 1 : kk;
    breathe(P, u, a.seed);
    P.pelvis = [0, lerp(RIG.pelvisY, -52, k)];
    P.kneelDepth = k;
    P.feet = [[-26, 0], [26, 0]];
    P.hands = [[-34, lerp(-106, -40, k)], [34, lerp(-106, -40, k)]];
    P.headDy = 12 * k; P.look = [0, 4 * k];
  },
  getup(P, a, u, d, w) {
    const k = easeInOut(clamp(u / Math.min(1.6, d * .7), 0, 1));
    POSES.kneel(P, a, u, d, w, 1 - k);
    P.hands = [[lerp(-34, -53, k), lerp(-40, -106, k)], [lerp(34, 53, k), lerp(-40, -106, k)]];
    P.headDy = 12 * (1 - k);
  },
  lift(P, a, u, d, w) {
    POSES.stand(P, a, u, d, w);
    const rep = (Math.sin(u * 2.4 - Math.PI / 2) + 1) / 2;
    const y = lerp(-218, -392, easeInOut(rep)), shake = Math.sin(u * 30) * 2 * rep;
    P.hands = [[-78, y + shake], [78, y - shake]]; P.feet = [[-34, 0], [34, 0]];
    P.pelvis[1] = RIG.pelvisY + (1 - rep) * 6; P.hold = 'barbell';
  },
  crossarms(P, a, u, d, w) { POSES.stand(P, a, u, d, w); P.hands = [[22, -150], [-22, -146]]; P.crossed = true; },
  headhands(P, a, u, d, w) {
    if (a.seated || w.seat) POSES.sit(P, a, u, d, w); else POSES.stand(P, a, u, d, w);
    const sh = Math.sin(u * 7) * 2;
    P.hands = [[-62 + sh, P.pelvis[1] - 176], [62 + sh, P.pelvis[1] - 176]]; P.headDy = 8; P.elbowOut = true; P.headTilt = .05;
  },
  facepalm(P, a, u, d, w) {
    POSES.stand(P, a, u, d, w);
    P.hands[1] = [16, -262]; P.headDy = 10; P.headTilt = -.06;
  },
  cry(P, a, u, d, w) {
    if (a.seated || w.seat) POSES.sit(P, a, u, d, w); else POSES.stand(P, a, u, d, w);
    const sob = Math.abs(Math.sin(u * 5)) * 3;
    P.hands = [[-26, P.pelvis[1] - 150 + sob], [26, P.pelvis[1] - 150 + sob]]; P.headDy = 10 + sob; P.shoulderDy = -sob;
  },
  laugh(P, a, u, d, w) {
    if (a.seated || w.seat) POSES.sit(P, a, u, d, w); else POSES.stand(P, a, u, d, w);
    const b = Math.abs(Math.sin(u * 9)) * 4;
    P.shoulderDy = -b; P.headTilt = -.1; P.headDy = -b * .5;
    if (!P.sideSit) P.hands[0] = [-30, P.pelvis[1] - 40];
  },
  shrug(P, a, u, d, w) {
    POSES.stand(P, a, u, d, w);
    const k = (Math.sin(u * 3) + 1) / 2;
    P.shoulderDy = -8 * k; P.hands = [[-82, -150 - 8 * k], [82, -150 - 8 * k]];
  },
  point(P, a, u, d, w) {
    POSES.stand(P, a, u, d, w);
    const dir = a.facing || 1, k = easeOut(u / .3);
    P.hands[dir > 0 ? 1 : 0] = [lerp(53 * dir, 112 * dir, k), lerp(-106, -212, k)];
    P.faceDx = dir * .7;
  },
  celebrate(P, a, u, d, w) {
    const j = Math.abs(Math.sin(u * Math.PI * 1.6));
    P.lift = j * 46; P.hands = [[-66, -360], [66, -360]]; P.feet = [[-22, -j * 6], [22, -j * 6]];
  },
  hug(P, a, u, d, w) {
    POSES.stand(P, a, u, d, w);
    const dir = w.targetDx >= 0 ? 1 : -1, k = easeOut(u / .7);
    P.lean = dir * .07 * k; P.faceDx = dir * .9; P.profile = dir;
    P.hands = [[dir * lerp(-20, 70, k), -170], [dir * lerp(53, 96, k), -185]];
    P.headTilt = dir * .1 * k;
  },
  lean(P, a, u, d, w) {
    POSES.stand(P, a, u, d, w);
    const dir = w.targetDx >= 0 ? 1 : -1, k = easeOut(u / .8);
    P.lean = dir * .2 * k; P.faceDx = dir * .8; P.headDy = 6 * k;
    P.hands[dir > 0 ? 1 : 0] = [dir * lerp(53, 90, k), lerp(-106, -150, k)];
  },
  grab(P, a, u, d, w) {
    POSES.lean(P, a, u, d, w);
    const dir = w.targetDx >= 0 ? 1 : -1, k = easeOut(u / .6);
    if (w.targetShoulder) { const [tx, ty] = w.targetShoulder; P.hands[dir > 0 ? 1 : 0] = [lerp(dir * 53, tx, k), lerp(-106, ty, k)]; }
  },
  umbrella(P, a, u, d, w) {
    if (w.moving) POSES.walk(P, a, u, d, w); else POSES.stand(P, a, u, d, w);
    P.hands[1] = [30, -208]; P.hold = 'umbrella';
  }
};

function evalPose(a, u, d, w) {
  const P = basePose();
  const m = MOODS[a.mood] || MOODS.neutral;
  P.look = [a.facing || 0, 0];
  P.faceDx = (a.facing || 0) * .55;
  // characters glance toward whoever they share the shot with
  if (!a.facing && w.lookDx) { P.faceDx = w.lookDx * .45; P.look = [w.lookDx * .8, 0]; }
  (POSES[a.pose] || POSES.stand)(P, a, u, d, w);
  if (w.moving && a.pose === 'umbrella') P.profile = w.dir;
  if (a.hold && a.hold !== 'none') P.hold = a.hold;
  if (m.look && a.pose !== 'walk' && a.pose !== 'run') { P.look = [P.look[0] + m.look[0] * (P.faceDx >= 0 ? 1 : -1), P.look[1] + m.look[1]]; }
  if (m.tilt) P.headTilt += m.tilt;
  if (m.shake) { P.shake = m.shake; }
  if (m.bounce) P.shoulderDy -= Math.abs(Math.sin(u * 9)) * 3;
  return P;
}

// ---------- drawing helpers ----------
function limb(ctx, pts, w, fill, out, lw) {
  ctx.lineCap = 'round'; ctx.lineJoin = 'round';
  ctx.beginPath(); ctx.moveTo(pts[0], pts[1]);
  for (let i = 2; i < pts.length; i += 2) ctx.lineTo(pts[i], pts[i + 1]);
  if (out) { ctx.strokeStyle = out; ctx.lineWidth = w + lw * 2; ctx.stroke(); }
  ctx.strokeStyle = fill; ctx.lineWidth = w; ctx.stroke();
}

function torsoPath(ctx) {
  ctx.beginPath();
  ctx.moveTo(-36, -128);
  ctx.bezierCurveTo(-52, -110, -62, -66, -60, -24);
  ctx.bezierCurveTo(-58, 6, -34, 12, 0, 12);
  ctx.bezierCurveTo(34, 12, 58, 6, 60, -24);
  ctx.bezierCurveTo(62, -66, 52, -110, 36, -128);
  ctx.closePath();
}

function shade(hex, k) {
  if (!hex || hex[0] !== '#') return hex;
  const n = parseInt(hex.slice(1), 16); const r = n >> 16, g = (n >> 8) & 255, b = n & 255;
  const f = v => clamp(Math.round(k < 0 ? v * (1 + k) : v + (255 - v) * k), 0, 255);
  return `rgb(${f(r)},${f(g)},${f(b)})`;
}
function rgba(hex, a) { const n = parseInt(hex.slice(1), 16); return `rgba(${n >> 16},${(n >> 8) & 255},${n & 255},${a})`; }
function roundRect(ctx, x, y, w, h, r) {
  ctx.beginPath(); ctx.moveTo(x + r, y); ctx.arcTo(x + w, y, x + w, y + h, r); ctx.arcTo(x + w, y + h, x, y + h, r);
  ctx.arcTo(x, y + h, x, y, r); ctx.arcTo(x, y, x + w, y, r); ctx.closePath();
}
function lapBook(ctx) {
  ctx.fillStyle = '#efe9db'; ctx.strokeStyle = '#2a2a30'; ctx.lineWidth = 2.5; ctx.beginPath(); ctx.moveTo(-58, -6); ctx.lineTo(58, -6); ctx.lineTo(50, 18); ctx.lineTo(-50, 18); ctx.closePath(); ctx.fill(); ctx.stroke();
  ctx.fillStyle = '#7a4b3a'; ctx.fillRect(-52, 16, 104, 6);
}

const HAIR_COLORS = { black: '#1c1a1d', brown: '#4a3123', blonde: '#d6b26a', red: '#9b3b24', grey: '#8d8f94', blue: '#2f4f8a', pink: '#d77aa5' };
const CLOTH = { grey: '#8a8d93', charcoal: '#3b3d43', green: '#2f5b3e', olive: '#5d6b3a', navy: '#24324f', blue: '#3b6fc4', red: '#b23a3a', maroon: '#6e2a33',
  yellow: '#e2b33c', mustard: '#c99a2e', orange: '#e07a2e', brown: '#6b4a32', beige: '#cdb894', white: '#e9e6df', black: '#1d1e22', pink: '#d77aa5', purple: '#6b4c9a', teal: '#2f7f7a' };
const colorOf = (c, table, dflt) => (c && c[0] === '#') ? c : (table[c] || dflt);

// Hair: drawn in two passes, behind the head and in front (bangs).
function drawHair(ctx, style, color, hx, hy, r, fdx, pass) {
  if (!style || style === 'none') return;
  const col = colorOf(color, HAIR_COLORS, HAIR_COLORS.black), hi = shade(col, .18);
  ctx.save(); ctx.translate(hx, hy); ctx.fillStyle = col;
  const off = fdx * 10;
  if (pass === 'back') {
    if (style === 'bob') { roundRect(ctx, -r * 1.12 + off * .3, -r * 1.02, r * 2.24, r * 1.78, r * .55); ctx.fill(); }
    else if (style === 'long') { roundRect(ctx, -r * 1.1 + off * .3, -r * 1.02, r * 2.2, r * 2.55, r * .6); ctx.fill(); }
    else if (style === 'ponytail') { ctx.beginPath(); ctx.ellipse(-fdx * r * .95 - (fdx ? 0 : r * .85), -r * .1, r * .32, r * .75, (fdx || 1) * .4, 0, Math.PI * 2); ctx.fill(); }
    else if (style === 'bun') { ctx.beginPath(); ctx.arc(off * .5, -r * 1.08, r * .38, 0, Math.PI * 2); ctx.fill(); }
    ctx.restore(); return;
  }
  // front pass: the cap of hair and bangs over the forehead
  ctx.beginPath();
  if (style === 'bob' || style === 'long') {
    ctx.moveTo(-r * 1.04, -r * .05);
    ctx.bezierCurveTo(-r * 1.1, -r * 1.25, r * 1.1, -r * 1.25, r * 1.04, -r * .05);
    ctx.lineTo(r * .98, -r * .2); ctx.lineTo(r * .7 + off, -r * .34); ctx.lineTo(-r * .72 + off, -r * .34); ctx.lineTo(-r * .98, -r * .2); ctx.closePath(); ctx.fill();
    ctx.strokeStyle = hi; ctx.lineWidth = 3; ctx.beginPath(); ctx.arc(off * .4, -r * .4, r * .7, -2.4, -1.6); ctx.stroke();
  } else if (style === 'short') {
    ctx.moveTo(-r * .98, -r * .3);
    ctx.bezierCurveTo(-r * 1.05, -r * 1.2, r * 1.05, -r * 1.2, r * .98, -r * .3);
    for (let i = 5; i >= -5; i--) ctx.lineTo(i * r * .19 + off, -r * (.52 + (i % 2 ? .1 : 0)));
    ctx.closePath(); ctx.fill();
  } else if (style === 'spiky') {
    ctx.moveTo(-r * .98, -r * .35);
    for (let i = -5; i <= 5; i++) { const x = i * r * .19 + off * .5; ctx.lineTo(x - r * .09, -r * .75); ctx.lineTo(x + fdx * 8, -r * 1.32 - (i % 2) * 8); }
    ctx.lineTo(r * .98, -r * .35); ctx.closePath(); ctx.fill();
  } else if (style === 'curly') {
    for (let i = -4; i <= 4; i++) { ctx.moveTo(i * r * .22 + r * .24 + off, -r * .78); ctx.arc(i * r * .22 + off, -r * .78 - Math.cos(i * .4) * r * .2, r * .26, 0, Math.PI * 2); }
    ctx.fill();
  } else if (style === 'ponytail' || style === 'bun') {
    ctx.moveTo(-r * 1.0, -r * .2);
    ctx.bezierCurveTo(-r * 1.08, -r * 1.25, r * 1.08, -r * 1.25, r * 1.0, -r * .2);
    ctx.bezierCurveTo(r * .6, -r * .55, -r * .2 + off, -r * .75, -r * 1.0, -r * .2); ctx.closePath(); ctx.fill();
  }
  ctx.restore();
}

function drawHat(ctx, hat, hx, hy, r, fdx) {
  if (!hat || hat === 'none') return;
  const [kind, color] = hat.split('_');
  const col = colorOf(color, CLOTH, '#888');
  ctx.save(); ctx.translate(hx, hy);
  if (kind === 'beanie') {
    ctx.fillStyle = col;
    ctx.beginPath(); ctx.ellipse(0, -r * .38, r * .98, r * .78, 0, Math.PI, 0); ctx.closePath(); ctx.fill();
    ctx.fillStyle = shade(col, -.18); roundRect(ctx, -r * 1.02, -r * .5, r * 2.04, r * .32, 8); ctx.fill();
    ctx.strokeStyle = shade(col, -.3); ctx.lineWidth = 2;
    for (let i = -3; i <= 3; i++) { ctx.beginPath(); ctx.moveTo(i * r * .27, -r * .48); ctx.lineTo(i * r * .27, -r * .2); ctx.stroke(); }
  } else if (kind === 'cap') {
    ctx.fillStyle = col;
    ctx.beginPath(); ctx.ellipse(0, -r * .42, r * .96, r * .62, 0, Math.PI, 0); ctx.closePath(); ctx.fill();
    ctx.fillStyle = shade(col, -.2);
    ctx.beginPath(); ctx.ellipse(r * .55 * (fdx >= 0 ? 1 : -1), -r * .42, r * .7, r * .14, 0, 0, Math.PI * 2); ctx.fill();
  }
  ctx.restore();
}

// ---------- faces ----------
function drawFace(ctx, m, P, hx, hy, o) {
  const f = clamp(P.faceDx, -1, 1), fdx = f * 20, sp = 21 * (1 - .32 * Math.abs(f));
  const lx = clamp(P.look[0], -1, 1), ly = P.look[1];
  const ink = o.demon ? o.demonColor : C.ink;
  const detail = o.detail;          // 0 = dots (wide shots), 1 = full eyes (close-ups)
  const eyeY = hy + 6, browY = hy - 19 + m.browY - (detail ? 3 : 0), mouthY = hy + 32;
  const blink = o.blink && !['closed', 'happy', 'squeeze'].includes(m.eyes);
  const t = o.t || 0;
  const tr = P.shake ? noise1(t * 30, 5) * 1.2 * P.shake : 0;
  if (!o.demon && m.blush) {
    ctx.fillStyle = `rgba(240,120,130,${.28 * m.blush})`;
    for (const s of [-1, 1]) { ctx.beginPath(); ctx.ellipse(hx + s * (sp + 12) + fdx, eyeY + 20, 14, 7, 0, 0, Math.PI * 2); ctx.fill(); }
  }
  for (const side of [-1, 1]) {
    const ex = hx + side * sp + fdx + tr, far = f * side < -.3 ? .8 : 1; // the far eye narrows when turned
    ctx.fillStyle = ink; ctx.strokeStyle = ink; ctx.lineCap = 'round';
    if (o.demon) {
      ctx.lineWidth = 6; ctx.beginPath(); ctx.moveTo(ex - side * 13, eyeY - 4); ctx.lineTo(ex + side * 11, eyeY + 3); ctx.stroke();
      continue;
    }
    if (blink || m.eyes === 'closed') {
      ctx.lineWidth = 3.6; ctx.beginPath(); ctx.moveTo(ex - 9, eyeY + 1); ctx.quadraticCurveTo(ex, eyeY + 7, ex + 9, eyeY + 1); ctx.stroke();
    } else if (m.eyes === 'happy') {
      ctx.lineWidth = 3.8; ctx.beginPath(); ctx.moveTo(ex - 9, eyeY + 4); ctx.quadraticCurveTo(ex, eyeY - 8, ex + 9, eyeY + 4); ctx.stroke();
    } else if (m.eyes === 'squeeze') {
      ctx.lineWidth = 3.8; ctx.beginPath(); ctx.moveTo(ex - side * 10, eyeY - 4); ctx.lineTo(ex + side * 6, eyeY + 1); ctx.lineTo(ex - side * 10, eyeY + 5); ctx.stroke();
    } else if (detail) {
      // Full eye: sclera, iris, pupil, two highlights, upper lid.
      const big = m.eyes === 'wide' ? 1.25 : m.eyes === 'small' ? .8 : 1;
      const rx = 12.5 * big * far, ry = 14.5 * big;
      ctx.fillStyle = '#fbfaf6'; ctx.beginPath(); ctx.ellipse(ex, eyeY, rx, ry, 0, 0, Math.PI * 2); ctx.fill();
      ctx.lineWidth = 2.4; ctx.strokeStyle = C.ink; ctx.stroke();
      ctx.save(); ctx.beginPath(); ctx.ellipse(ex, eyeY, rx, ry, 0, 0, Math.PI * 2); ctx.clip();
      const ix = ex + lx * rx * .42, iy = eyeY + ly * 1.1 + 1, ir = (m.eyes === 'small' ? 5.5 : 8) * big;
      ctx.fillStyle = o.iris || '#3d3540'; ctx.beginPath(); ctx.arc(ix, iy, ir, 0, Math.PI * 2); ctx.fill();
      ctx.fillStyle = '#0d0c0e'; ctx.beginPath(); ctx.arc(ix, iy, ir * .55, 0, Math.PI * 2); ctx.fill();
      ctx.fillStyle = '#fff'; ctx.beginPath(); ctx.arc(ix - ir * .35, iy - ir * .4, ir * .32, 0, Math.PI * 2); ctx.fill();
      ctx.beginPath(); ctx.arc(ix + ir * .35, iy + ir * .35, ir * .14, 0, Math.PI * 2); ctx.fill();
      if (m.eyes === 'teary' || m.sparkle) {
        ctx.fillStyle = 'rgba(255,255,255,.9)'; const wob = Math.sin(t * 7) * .8;
        ctx.beginPath(); ctx.ellipse(ix + ir * .2 + wob, iy - ir * .1, ir * .5, ir * .28, -.4, 0, Math.PI * 2); ctx.fill();
      }
      if (m.lid > 0) { ctx.fillStyle = o.skin; ctx.fillRect(ex - rx - 2, eyeY - ry - 2, rx * 2 + 4, ry * 2 * m.lid + 2); }
      if (m.eyes === 'teary') { ctx.fillStyle = 'rgba(140,190,255,.45)'; ctx.fillRect(ex - rx, eyeY + ry * .45, rx * 2, ry); }
      ctx.restore();
      if (m.lid > 0) { ctx.strokeStyle = C.ink; ctx.lineWidth = 3.4; const ly2 = eyeY - ry + ry * 2 * m.lid; ctx.beginPath(); ctx.moveTo(ex - rx * .95, ly2); ctx.quadraticCurveTo(ex, ly2 - 2, ex + rx * .95, ly2); ctx.stroke(); }
      else { ctx.strokeStyle = C.ink; ctx.lineWidth = 3.6; ctx.beginPath(); ctx.ellipse(ex, eyeY, rx, ry, 0, Math.PI * 1.08, Math.PI * 1.92); ctx.stroke(); }
      if (m.bags) { ctx.strokeStyle = 'rgba(80,70,60,.5)'; ctx.lineWidth = 2; ctx.beginPath(); ctx.moveTo(ex - 9, eyeY + ry + 4); ctx.quadraticCurveTo(ex, eyeY + ry + 8, ex + 9, eyeY + ry + 4); ctx.stroke(); }
    } else {
      const rx = (m.eyes === 'wide' ? 9 : m.eyes === 'small' ? 4.5 : 6.5) * far, ry = m.eyes === 'wide' ? 11 : m.eyes === 'small' ? 5.5 : 8.5;
      ctx.beginPath(); ctx.ellipse(ex + lx * 3, eyeY + ly, rx, ry, 0, 0, Math.PI * 2); ctx.fill();
      ctx.fillStyle = 'rgba(210,222,255,.85)';
      ctx.beginPath(); ctx.arc(ex + lx * 3 - rx * .3, eyeY + ly - ry * .35, Math.max(1.4, rx * .28), 0, Math.PI * 2); ctx.fill();
      if (m.eyes === 'teary') { ctx.fillStyle = 'rgba(255,255,255,.85)'; ctx.beginPath(); ctx.arc(ex + lx * 3 + 2, eyeY + ly + 2, 2.4, 0, Math.PI * 2); ctx.fill(); }
      if (m.lid > 0) {
        ctx.fillStyle = o.skin; ctx.fillRect(ex - 13, eyeY - 14, 26, (ry * 2) * m.lid + 6 * m.lid);
        ctx.strokeStyle = ink; ctx.lineWidth = 3; const lidY = eyeY - ry + ry * 2 * m.lid;
        ctx.beginPath(); ctx.moveTo(ex - 9, lidY); ctx.lineTo(ex + 9, lidY); ctx.stroke();
      }
      if (m.bags) { ctx.strokeStyle = 'rgba(80,70,60,.45)'; ctx.lineWidth = 2; ctx.beginPath(); ctx.moveTo(ex - 7, eyeY + 13); ctx.quadraticCurveTo(ex, eyeY + 17, ex + 7, eyeY + 13); ctx.stroke(); }
    }
    if (o.hideBrows) continue;
    const inner = m.brow[0] * 16, raise = side > 0 ? m.brow[1] * 30 : 0;
    ctx.strokeStyle = C.ink; ctx.lineWidth = detail ? 8 : 7; ctx.lineCap = 'round';
    ctx.beginPath(); ctx.moveTo(ex - side * 13, browY - inner + raise); ctx.lineTo(ex + side * 13, browY + raise * .4); ctx.stroke();
  }
  if (o.demon) return;
  if (m.tears) {
    ctx.fillStyle = 'rgba(150,200,255,.75)';
    for (const side of [-1, 1]) {
      const ex = hx + side * sp + fdx;
      ctx.beginPath(); ctx.moveTo(ex - 3, eyeY + 6); ctx.quadraticCurveTo(ex - 6, eyeY + 30, ex - 2, hy + 52); ctx.lineTo(ex + 3, hy + 52); ctx.quadraticCurveTo(ex + 4, eyeY + 30, ex + 3, eyeY + 6); ctx.fill();
      const dy = (t * 60 + side * 20) % 40; ctx.beginPath(); ctx.arc(ex, hy + 52 + dy, 3.5, 0, Math.PI * 2); ctx.fill();
    }
  }
  ctx.strokeStyle = C.ink; ctx.fillStyle = C.ink; ctx.lineWidth = 3.6; ctx.lineCap = 'round';
  const mx = hx + fdx * 1.15 + tr;
  let mouth = m.mouth;
  if (o.talking) mouth = ['flat', 'o', 'small', 'smile'][Math.floor(t * 9) % (m.mouth === 'smile' ? 4 : 3)];
  ctx.beginPath();
  switch (mouth) {
    case 'smile': ctx.moveTo(mx - 13, mouthY - 3); ctx.quadraticCurveTo(mx, mouthY + 10, mx + 13, mouthY - 3); ctx.stroke(); break;
    case 'frown': ctx.moveTo(mx - 11, mouthY + 4); ctx.quadraticCurveTo(mx, mouthY - 6, mx + 11, mouthY + 4); ctx.stroke(); break;
    case 'o': ctx.ellipse(mx, mouthY + 1, 6.5, 8.5, 0, 0, Math.PI * 2); ctx.fill(); break;
    case 'small': ctx.ellipse(mx, mouthY, 3.8, 3.2, 0, 0, Math.PI * 2); ctx.fill(); break;
    case 'wavy': { const w = Math.sin(t * 9) * 1.2; ctx.moveTo(mx - 12, mouthY); ctx.bezierCurveTo(mx - 6, mouthY - 5 + w, mx + 2, mouthY + 5 - w, mx + 12, mouthY - 1); ctx.stroke(); break; }
    case 'tight': ctx.moveTo(mx - 10, mouthY + 1); ctx.lineTo(mx + 10, mouthY + 1); ctx.lineWidth = 4.4; ctx.stroke(); break;
    case 'smirk': ctx.moveTo(mx - 10, mouthY + 2); ctx.quadraticCurveTo(mx + 3, mouthY + 4, mx + 13, mouthY - 5); ctx.stroke(); break;
    case 'laugh': case 'grin':
      ctx.moveTo(mx - 15, mouthY - 4); ctx.quadraticCurveTo(mx, mouthY - 2, mx + 15, mouthY - 4); ctx.quadraticCurveTo(mx, mouthY + 22, mx - 15, mouthY - 4); ctx.fill();
      ctx.fillStyle = '#d9707a'; ctx.beginPath(); ctx.ellipse(mx, mouthY + 9, 7, 4, 0, 0, Math.PI * 2); ctx.fill(); break;
    case 'wail':
      ctx.moveTo(mx - 13, mouthY + 10); ctx.quadraticCurveTo(mx, mouthY - 10, mx + 13, mouthY + 10); ctx.quadraticCurveTo(mx, mouthY + 4, mx - 13, mouthY + 10); ctx.fill(); break;
    case 'teeth':
      roundRect(ctx, mx - 13, mouthY - 5, 26, 12, 4); ctx.fillStyle = '#f4f1e8'; ctx.fill(); ctx.lineWidth = 2.6; ctx.stroke();
      ctx.beginPath(); ctx.moveTo(mx - 13, mouthY + 1); ctx.lineTo(mx + 13, mouthY + 1); for (const q of [-6, 0, 6]) { ctx.moveTo(mx + q, mouthY - 5); ctx.lineTo(mx + q, mouthY + 7); } ctx.lineWidth = 1.6; ctx.stroke(); break;
    default: ctx.moveTo(mx - 10, mouthY); ctx.lineTo(mx + 10, mouthY); ctx.stroke();
  }
  if (m.sweat) { ctx.fillStyle = '#9fd0ff'; ctx.beginPath(); ctx.moveTo(hx + 52, hy - 30); ctx.quadraticCurveTo(hx + 60, hy - 14, hx + 52, hy - 10); ctx.quadraticCurveTo(hx + 44, hy - 14, hx + 52, hy - 30); ctx.fill(); }
}

// ---------- held items ----------
function drawHold(ctx, item, P, hands, o) {
  const [L, R] = hands;
  ctx.save();
  if (item === 'phone') {
    const x = (L[0] + R[0]) / 2, y = (L[1] + R[1]) / 2 - 10;
    ctx.translate(x, y); ctx.rotate(-.06);
    ctx.fillStyle = '#16181d'; roundRect(ctx, -15, -27, 30, 50, 6); ctx.fill();
    ctx.fillStyle = o.demon ? '#300' : '#9cc4ff'; ctx.globalAlpha = .9; roundRect(ctx, -12, -24, 24, 42, 4); ctx.fill();
  } else if (item === 'phone_ear') {
    ctx.translate(R[0] - 6, R[1] - 6); ctx.rotate(.3); ctx.fillStyle = '#16181d'; roundRect(ctx, -10, -26, 20, 46, 6); ctx.fill();
  } else if (item === 'cup' || item === 'coffee') {
    ctx.translate(R[0] + 6, R[1] - 10);
    ctx.fillStyle = '#f2efe6'; roundRect(ctx, -12, -26, 24, 30, 4); ctx.fill(); ctx.fillStyle = '#8b5a3c'; ctx.fillRect(-12, -16, 24, 8);
    ctx.strokeStyle = 'rgba(230,230,230,.45)'; ctx.lineWidth = 2.5; const t = o.t || 0;
    for (const k of [-4, 4]) { ctx.beginPath(); ctx.moveTo(k, -30); ctx.bezierCurveTo(k + 8 * Math.sin(t * 2 + k), -45, k - 8, -55, k + 4 * Math.sin(t * 3), -70); ctx.stroke(); }
  } else if (item === 'pencil') {
    const pen=hands[P.penHand??1];ctx.translate(pen[0],pen[1]); ctx.rotate(.6);
    ctx.fillStyle = '#f1c232'; ctx.fillRect(-3, -30, 6, 34); ctx.fillStyle = '#333'; ctx.fillRect(-3, 4, 6, 5);
  } else if (item === 'book') {
    if (P.bookOpen) { drawOpenBook(ctx,P,hands); ctx.restore(); return; }
    ctx.translate((L[0] + R[0]) / 2, (L[1] + R[1]) / 2 - 6);
    ctx.fillStyle = '#4f8a5e'; roundRect(ctx, -32, -24, 64, 44, 3); ctx.fill(); ctx.fillStyle = '#efe6d2'; ctx.fillRect(-29, -21, 58, 4);
  } else if (item === 'bag') {
    ctx.translate(R[0] + 4, R[1] + 30); ctx.fillStyle = '#3a4a5e'; roundRect(ctx, -22, -26, 44, 50, 8); ctx.fill();
  } else if (item === 'flower') {
    ctx.translate(R[0], R[1]); ctx.strokeStyle = '#3f7a46'; ctx.lineWidth = 3; ctx.beginPath(); ctx.moveTo(0, 0); ctx.lineTo(4, -60); ctx.stroke();
    ctx.fillStyle = '#e25b6b'; for (let i = 0; i < 6; i++) { ctx.beginPath(); ctx.arc(4 + Math.cos(i) * 9, -66 + Math.sin(i) * 9, 8, 0, Math.PI * 2); ctx.fill(); }
    ctx.fillStyle = '#f2c94c'; ctx.beginPath(); ctx.arc(4, -66, 6, 0, Math.PI * 2); ctx.fill();
  } else if (item === 'letter') {
    ctx.translate(R[0], R[1] - 14); ctx.rotate(-.2); ctx.fillStyle = '#f3efe4'; ctx.fillRect(-26, -18, 52, 34); ctx.strokeStyle = '#b9b2a2'; ctx.lineWidth = 2; ctx.beginPath(); ctx.moveTo(-26, -18); ctx.lineTo(0, 2); ctx.lineTo(26, -18); ctx.stroke();
  } else if (item === 'umbrella') {
    const col = o.umbrella || '#e8b830', x = R[0], y = R[1];
    ctx.strokeStyle = '#5a4a32'; ctx.lineWidth = 5; ctx.beginPath(); ctx.moveTo(x, y + 30); ctx.lineTo(x - 6, y - 210); ctx.stroke();
    ctx.beginPath(); ctx.arc(x + 8, y + 30, 8, 0, Math.PI); ctx.stroke();
    ctx.translate(x - 6, y - 210);
    ctx.fillStyle = col; ctx.beginPath(); ctx.moveTo(-150, 34);
    for (let i = 0; i < 5; i++) { const x0 = -150 + i * 60; ctx.quadraticCurveTo(x0 + 30, 18, x0 + 60, 34); }
    ctx.quadraticCurveTo(140, -40, 0, -52); ctx.quadraticCurveTo(-140, -40, -150, 34); ctx.fill();
    ctx.strokeStyle = shade(col, -.25); ctx.lineWidth = 2.5;
    for (const k of [-90, -30, 30, 90]) { ctx.beginPath(); ctx.moveTo(0, -50); ctx.quadraticCurveTo(k * .7, -30, k, 26); ctx.stroke(); }
    if (o.rain) { ctx.fillStyle = 'rgba(190,210,240,.7)'; const t = o.t || 0; for (const k of [-150, 150]) { const dy = (t * 140 + (k > 0 ? 40 : 0)) % 90; ctx.beginPath(); ctx.ellipse(k, 40 + dy, 2.5, 5, 0, 0, Math.PI * 2); ctx.fill(); } }
  } else if (item === 'barbell') {
    ctx.strokeStyle = '#9aa0a8'; ctx.lineWidth = 7; ctx.beginPath(); ctx.moveTo(L[0] - 70, L[1]); ctx.lineTo(R[0] + 70, R[1]); ctx.stroke();
    ctx.fillStyle = '#2b2d33'; ctx.strokeStyle = '#555a63'; ctx.lineWidth = 2;
    for (const [hx, hy, sd] of [[L[0], L[1], -1], [R[0], R[1], 1]]) for (let k = 0; k < 2; k++) { roundRect(ctx, hx + sd * (40 + k * 18) - 8, hy - 44 + k * 6, 16, 88 - k * 12, 4); ctx.fill(); ctx.stroke(); }
  }
  ctx.restore();
}

// ---------- the character ----------
// a: actor (wx, wy, scale, mood, hat, hair, top, ...); P: pose; o: {demon, demonColor, skin, t, blink, talking, zoom, detail}
function drawCharacter(ctx, a, P, o) {
  const s = a.scale || 1, lw = 2.6 / (o.zoom || 1) / s;
  const skin = o.skin || C.cream, out = o.demon ? '#050505' : C.ink;
  const shadeCol = o.demon ? '#050505' : shade(skin, -.12);
  const top = o.demon ? null : colorOf(a.top, CLOTH, null);
  const pants = o.demon ? null : colorOf(a.pants, CLOTH, top ? CLOTH.charcoal : null);
  const legCol = pants || shadeCol, armCol = top && a.sleeves !== false ? shade(top, -.04) : skin;
  ctx.save();
  ctx.translate(a.wx, a.wy - P.lift * s);
  ctx.scale(s, s);
  if (P.rot) { ctx.translate(0, -P.lieH); ctx.rotate(P.rot); }
  if (!P.rot && !o.demon && !o.noShadow) {
    ctx.fillStyle = 'rgba(0,0,0,.35)'; ctx.beginPath(); ctx.ellipse(0, 2 + P.lift, 62, 9, 0, 0, Math.PI * 2); ctx.fill();
  }
  const [px, py] = P.pelvis;
  const cosL = Math.cos(P.lean), sinL = Math.sin(P.lean);
  const rotP = (x, y) => [px + x * cosL - y * sinL, py + x * sinL + y * cosL];
  const shoe = (x, y) => { if (!pants) return; ctx.fillStyle = '#18181b'; ctx.beginPath(); ctx.ellipse(x + (P.profile || P.sideSit || 0) * 6, y + 2, 18, 9, 0, 0, Math.PI * 2); ctx.fill(); };
  // Legs
  const legs = [];
  for (let i = 0; i < 2; i++) {
    const side = i ? 1 : -1;
    const [hx, hy] = rotP(side * RIG.hipX * (P.profile || P.sideSit ? .45 : 1), -4);
    const [fx, fy] = P.feet[i];
    if (P.kneelDepth > .05) {
      const kx = lerp(fx, side * 30, P.kneelDepth), ky = lerp(-RIG.shin, -8, P.kneelDepth);
      const k = ik(hx, hy, kx, ky, RIG.thigh, RIG.shin, side * (P.kneelDepth > .5 ? 1 : -1));
      legs.push([[hx, hy, k[0], k[1], k[2], k[3]], null]);
    } else if (P.sideSit) {
      const dir = P.sideSit, kx = fx - dir * 4, ky = hy + 6;
      legs.push([[hx, hy, kx, ky, fx, fy - 4], [fx, fy - 4]]);
    } else if (P.thighShort) {
      legs.push([[fx * 1.1, hy + 16, fx, fy - 3], [fx, fy - 3], [fx * 1.1, hy + 10]]);
    } else {
      const k = ik(hx, hy, fx, fy - 4, RIG.thigh, RIG.shin, P.profile ? -P.profile : (P.lean ? (P.lean > 0 ? -1 : 1) : -side));
      legs.push([[hx, hy, k[0], k[1], k[2], k[3]], [k[2], k[3]]]);
    }
  }
  legs.forEach(([pts, foot, knee], i) => {
    limb(ctx, pts, RIG.legW, i === 0 && (P.profile || P.sideSit) ? shade(legCol, -.12) : legCol, out, lw);
    if (knee) { ctx.fillStyle = shade(legCol, .05); ctx.strokeStyle = out; ctx.lineWidth = lw * 2; ctx.beginPath(); ctx.ellipse(knee[0], knee[1], 24, 21, 0, 0, Math.PI * 2); ctx.stroke(); ctx.fill(); }
    if (foot) shoe(foot[0], foot[1]);
  });
  // Body (torso + head) rotates with lean around the pelvis.
  ctx.save();
  ctx.translate(px, py); ctx.rotate(P.lean);
  ctx.scale(1, P.squash); ctx.translate(0, (1 - P.squash) * 20);
  const hx = 0, hy = RIG.headY + P.headDy + P.shoulderDy * .5;
  const hairStyle = o.demon ? null : a.hair, hairCol = a.hair_color;
  // hood / long hair behind
  if (a.hood && !o.demon) { ctx.fillStyle = shade(top || CLOTH.grey, -.08); ctx.beginPath(); ctx.ellipse(hx - P.faceDx * 22, hy + 22, RIG.headR * 1.02, RIG.headR * .9, 0, 0, Math.PI * 2); ctx.fill(); }
  drawHair(ctx, hairStyle, hairCol, hx, hy, RIG.headR, P.faceDx, 'back');
  ctx.strokeStyle = out; ctx.lineWidth = lw * 2;
  torsoPath(ctx); ctx.stroke();
  ctx.fillStyle = top || skin; torsoPath(ctx); ctx.fill();
  if (!o.demon) {
    ctx.save(); torsoPath(ctx); ctx.clip();
    const g = ctx.createLinearGradient(-60, 0, 60, 0); g.addColorStop(0, 'rgba(0,0,0,0.13)'); g.addColorStop(.4, 'rgba(0,0,0,0)'); g.addColorStop(1, 'rgba(0,0,0,0.07)');
    ctx.fillStyle = g; ctx.fillRect(-70, -140, 140, 160);
    if (top && a.top_style === 'coat') { ctx.strokeStyle = shade(top, -.3); ctx.lineWidth = 2.5; ctx.beginPath(); ctx.moveTo(P.faceDx * 18, -126); ctx.lineTo(P.faceDx * 18, 12); ctx.stroke(); ctx.fillStyle = shade(top, -.35); for (const by of [-90, -55, -20]) { ctx.beginPath(); ctx.arc(P.faceDx * 18 + 8, by, 3.5, 0, Math.PI * 2); ctx.fill(); } }
    if (top && a.top_style === 'hoodie') { ctx.fillStyle = shade(top, -.1); roundRect(ctx, -30 + P.faceDx * 10, -50, 60, 34, 10); ctx.fill(); }
    ctx.restore();
  }
  // scarf / hood collar around the neck, under the head
  if (!o.demon && (a.scarf || a.hood)) {
    const sc = a.scarf ? colorOf(a.scarf, CLOTH, CLOTH.mustard) : shade(top || CLOTH.grey, -.05);
    ctx.fillStyle = sc; ctx.strokeStyle = shade(sc, -.3); ctx.lineWidth = 2;
    ctx.beginPath(); ctx.ellipse(0, -112, 54, 17, 0, 0, Math.PI * 2); ctx.fill(); ctx.stroke();
    if (a.scarf) { roundRect(ctx, 14 + P.faceDx * 14, -112, 20, 64, 6); ctx.fill(); ctx.stroke(); }
  }
  // head
  ctx.save();
  ctx.translate(hx, hy + 40); ctx.rotate(P.headTilt + (P.shake ? noise1((o.t || 0) * 22, 9) * .015 * P.shake : 0)); ctx.translate(-hx, -(hy + 40));
  ctx.strokeStyle = out; ctx.lineWidth = lw * 2;
  ctx.beginPath(); ctx.arc(hx, hy, RIG.headR, 0, Math.PI * 2); ctx.stroke();
  ctx.fillStyle = o.demon ? skin : skin; ctx.fill();
  if (!o.demon) {
    const g = ctx.createRadialGradient(hx - 18 + P.faceDx * 10, hy - 22, 8, hx, hy, RIG.headR);
    g.addColorStop(0, 'rgba(255,255,255,0.10)'); g.addColorStop(1, 'rgba(0,0,0,0.10)');
    ctx.fillStyle = g; ctx.beginPath(); ctx.arc(hx, hy, RIG.headR, 0, Math.PI * 2); ctx.fill();
  }
  const bangsCoverBrows = hairStyle === 'bob' || hairStyle === 'long';
  drawFace(ctx, MOODS[a.mood] || MOODS.neutral, P, hx, hy, { ...o, skin, iris: a.iris, hideBrows: bangsCoverBrows && !(MOODS[a.mood] || {}).browY });
  drawHair(ctx, hairStyle, hairCol, hx, hy, RIG.headR, P.faceDx, 'front');
  drawHat(ctx, a.hat, hx, hy, RIG.headR, P.faceDx);
  if (a.glasses && !o.demon) { ctx.strokeStyle = '#1d1d22'; ctx.lineWidth = 3; const f = P.faceDx * 20, sp = 21 * (1 - .32 * Math.abs(P.faceDx)); for (const sd of [-1, 1]) { ctx.beginPath(); ctx.arc(hx + sd * sp + f, hy + 6, 15, 0, Math.PI * 2); ctx.stroke(); } ctx.beginPath(); ctx.moveTo(hx - sp + 15 + f, hy + 4); ctx.lineTo(hx + sp - 15 + f, hy + 4); ctx.stroke(); }
  if (P.phoneGlow && !o.demon) {
    const g = ctx.createRadialGradient(hx, hy + 20, 5, hx, hy + 20, 90);
    g.addColorStop(0, 'rgba(150,190,255,0.24)'); g.addColorStop(1, 'rgba(150,190,255,0)');
    ctx.fillStyle = g; ctx.beginPath(); ctx.arc(hx, hy + 20, 90, 0, Math.PI * 2); ctx.fill();
  }
  ctx.restore();
  ctx.restore();
  if (P.lapBook && !P.writingPad && !P.typingLaptop) { ctx.save(); ctx.translate(0, P.pelvis[1] - 18); lapBook(ctx); ctx.restore(); }
  if (P.typingLaptop) drawTypingLaptop(ctx,P);
  // Arms
  const hands = [];
  const order = P.profile || P.sideSit ? ((P.profile || P.sideSit) > 0 ? [0, 1] : [1, 0]) : [0, 1];
  for (const i of order) {
    const side = i ? 1 : -1;
    const sxs = (P.profile || P.sideSit) ? .55 : 1;
    const [sx, sy] = rotP(side * RIG.shoulderX * sxs, RIG.shoulderY + P.shoulderDy + (1 - P.squash) * 20);
    const [tx, ty] = P.hands[i];
    const k1 = ik(sx, sy, tx, ty, RIG.upper, RIG.fore, 1), k2 = ik(sx, sy, tx, ty, RIG.upper, RIG.fore, -1);
    const k = P.crossed ? (Math.abs(k1[0]) < Math.abs(k2[0]) ? k1 : k2) : (side * k1[0] > side * k2[0] ? k1 : k2);
    hands[i] = [k[2], k[3]];
    if (P.handsHidden) { limb(ctx, [sx, sy, k[0], k[1], k[2], k[3]], RIG.armW, armCol, out, lw); continue; }
    const far = (P.profile || P.sideSit) && i === order[0];
    const col = (P.crossed && i === 0) || far ? shade(armCol, -.12) : armCol;
    limb(ctx, [sx, sy, k[0], k[1], k[2], k[3]], RIG.armW, col, out, lw);
    if (top && a.sleeves !== false && !o.demon) { ctx.fillStyle = skin; ctx.strokeStyle = out; ctx.lineWidth = lw * 2; ctx.beginPath(); ctx.arc(k[2], k[3], RIG.armW / 2 + 1, 0, Math.PI * 2); ctx.stroke(); ctx.fill(); }
  }
  if (P.writingPad) drawWritingPad(ctx,P);
  if (P.hold) drawHold(ctx, P.hold, P, hands, { ...o, umbrella: a.umbrella_color });
  ctx.restore();
  return { hands, head: [a.wx + (px + hx) * s, a.wy + (py + hy - P.lift) * s] };
}
