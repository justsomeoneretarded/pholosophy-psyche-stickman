// Render a film (shot list JSON) to MP4 with headless Chromium + FFmpeg.
// node render/render.mjs --film examples/film.json --out build/picture.mp4 [--width 1920] [--fps 30] [--start 0 --end 30]
// node render/render.mjs --film examples/film.json --stills build/stills --every 2   (review frames)
// node render/render.mjs --film examples/film.json --cues build/cues.json            (sound cue sheet)
import { createRequire } from 'node:module';
import { spawn } from 'node:child_process';
import fs from 'node:fs';
import path from 'node:path';
import { fileURLToPath, pathToFileURL } from 'node:url';

const { chromium } = createRequire(import.meta.url)('playwright');
const args = Object.fromEntries(process.argv.slice(2).reduce((acc, v, i, all) => {
  if (v.startsWith('--')) acc.push([v.slice(2), all[i + 1] && !all[i + 1].startsWith('--') ? all[i + 1] : true]); return acc; }, []));
const root = path.resolve(path.dirname(fileURLToPath(import.meta.url)), '..');
const film = JSON.parse(fs.readFileSync(args.film, 'utf8'));
const width = parseInt(args.width || '1920'), fps = parseInt(args.fps || '30');
const height = Math.round(width * 9 / 16);

const browser = await chromium.launch({ args: ['--disable-gpu-vsync', '--force-device-scale-factor=1'] });
const page = await browser.newPage({ viewport: { width: 640, height: 360 } });
page.on('pageerror', e => { console.error('page error:', e.message); process.exitCode = 1; });
await page.goto(pathToFileURL(path.join(root, 'engine', 'index.html')).href);
await page.evaluate(() => document.fonts.ready);
const duration = await page.evaluate(([f, w]) => setup(f, w), [film, width]);
console.log(`film: ${film.title} — ${duration.toFixed(2)} s, ${film.shots.length} shots`);

async function grab(t, type = 'jpeg') {
  const data = await page.evaluate(([t, type]) => { drawFrame(t); return document.getElementById('film').toDataURL(type === 'png' ? 'image/png' : 'image/jpeg', 0.94); }, [t, type]);
  return Buffer.from(data.split(',')[1], 'base64');
}

if (args.cues) {
  const cues = await page.evaluate(() => getCues());
  fs.mkdirSync(path.dirname(args.cues), { recursive: true });
  fs.writeFileSync(args.cues, JSON.stringify(cues, null, 1));
  console.log(`cues: ${cues.cues.length}`);
} else if (args.stills) {
  fs.mkdirSync(args.stills, { recursive: true });
  const times = args.times ? String(args.times).split(',').map(Number) : [];
  if (!times.length) { const every = parseFloat(args.every || '2'); for (let t = 0.6; t < duration; t += every) times.push(+t.toFixed(2)); }
  for (const t of times) fs.writeFileSync(path.join(args.stills, `t${String(t.toFixed(2)).padStart(7, '0')}.jpg`), await grab(t));
  console.log(`stills: ${times.length}`);
} else {
  const start = parseFloat(args.start || '0'), end = Math.min(duration, parseFloat(args.end || String(duration)));
  const first = Math.round(start * fps), last = Math.round(end * fps);
  fs.mkdirSync(path.dirname(args.out), { recursive: true });
  const ff = spawn(args.ffmpeg || 'ffmpeg', ['-y', '-v', 'error', '-f', 'image2pipe', '-framerate', String(fps), '-c:v', 'mjpeg', '-i', '-',
    '-c:v', 'libx264', '-preset', args.preset || 'medium', '-crf', '17', '-pix_fmt', 'yuv420p', '-r', String(fps), '-movflags', '+faststart', args.out], { stdio: ['pipe', 'inherit', 'inherit'] });
  const t0 = Date.now();
  for (let f = first; f < last; f++) {
    const buf = await grab((f + .5) / fps);
    if (!ff.stdin.write(buf)) await new Promise(r => ff.stdin.once('drain', r));
    if ((f - first) % (fps * 5) === 0) console.log(`frame ${f - first}/${last - first}  ${((Date.now() - t0) / 1000).toFixed(0)} s`);
  }
  ff.stdin.end();
  await new Promise((res, rej) => ff.on('close', c => c === 0 ? res() : rej(new Error('ffmpeg exit ' + c))));
  console.log(`wrote ${args.out} (${last - first} frames) in ${((Date.now() - t0) / 1000).toFixed(0)} s`);
}
await browser.close();
