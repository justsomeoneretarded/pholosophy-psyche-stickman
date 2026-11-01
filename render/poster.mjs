// A dedicated illustration pass: retain actors, props and lighting, remove video overlays.
export function cleanPosterFilm(film) {
  const poster=JSON.parse(JSON.stringify(film));
  poster.hud=null;
  for(const shot of poster.shots) {
    shot.lines=[];
    delete shot.hud;
    delete shot.big;
    delete shot.card;
  }
  return poster;
}
