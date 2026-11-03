'use strict';
async function loadFilmFonts() {
  await Promise.all(['48px FilmHand','48px FilmDigit','48px FilmRound','700 48px FilmRound'].map(font=>document.fonts.load(font)));
  await document.fonts.ready;
  const missing=[...document.fonts].filter(face=>/^Film/.test(face.family.replaceAll('"','')) && face.status!=='loaded');
  if(missing.length)throw new Error('Film fonts did not load: '+missing.map(face=>face.family).join(', '));
}
