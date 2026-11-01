// Narrator captions use verified word timing when available; dialogue keeps its own style.
function narratorCaption(line, elapsed) {
  const words = line.word_times;
  if (Array.isArray(words) && words.length) {
    if (elapsed < words[0].start || elapsed > words[words.length - 1].end + .3) return '';
    let index = 0;
    for (let i = 1; i < words.length && words[i].start <= elapsed; i++) index = i;
    const first = Math.floor(index / 7) * 7;
    return words.slice(first, first + 7).map(w => w.word).join(' ');
  }
  // Staging previews have no recorded speech yet. Never reveal a chopped word.
  const text = String(line.text || '');
  const prefix = text.slice(0, Math.max(0, Math.floor(elapsed * (line.cps || 24))));
  return prefix.length === text.length ? prefix : prefix.replace(/\S*$/, '').trimEnd();
}
