// Platform listing rules. Sources: Etsy help (13 tags, 20 chars, title 140),
// Redbubble blog (15 tags, 50 chars each, title ~50-60 chars), TeePublic (10 tags, one main tag; verify before launch).
export const PLATFORMS = {
  etsy: { label: "Etsy", titleMax: 140, tagMax: 13, tagLen: 20, descMax: 2000 },
  redbubble: { label: "Redbubble", titleMax: 60, tagMax: 15, tagLen: 50, descMax: 500 },
  teepublic: { label: "TeePublic", titleMax: 60, tagMax: 10, tagLen: 40, descMax: 500 },
};

// Small starter list of commonly protected names. NOT legal advice, not exhaustive.
export const FLAGGED = ["nike","adidas","disney","marvel","pokemon","pikachu","mickey","star wars","harry potter","hogwarts","nfl","nba","fifa","barbie","hello kitty","minecraft","fortnite","taylor swift","supreme","gucci","louis vuitton","chanel","netflix","stranger things","yoda","baby yoda","mandalorian","batman","superman","spiderman","spider-man","naruto","one piece","dragon ball","coca cola","lego","nintendo","mario","zelda","starbucks","peanuts","snoopy","simpsons","spongebob","bluey","frozen","elsa","barbie","olympics","super bowl","grateful dead","metallica","nasa"];

export function findFlagged(text) {
  const t = " " + text.toLowerCase().replace(/[^a-z0-9 -]/g, " ") + " ";
  return [...new Set(FLAGGED.filter((w) => t.includes(" " + w + " ")))];
}

export function fitTags(tags, p) {
  const seen = new Set();
  const out = [];
  for (let raw of tags || []) {
    let t = String(raw).toLowerCase().replace(/[^a-z0-9 ]/g, " ").replace(/\s+/g, " ").trim();
    if (p === PLATFORMS.etsy) { /* Etsy: letters, numbers, spaces only */ }
    if (!t || t.length > p.tagLen || seen.has(t)) continue;
    seen.add(t); out.push(t);
    if (out.length >= p.tagMax) break;
  }
  return out;
}

export function fitTitle(title, p) {
  let t = String(title || "").replace(/\s+/g, " ").trim();
  if (t.length <= p.titleMax) return t;
  t = t.slice(0, p.titleMax);
  const i = t.lastIndexOf(" ");
  return (i > p.titleMax * 0.6 ? t.slice(0, i) : t).replace(/[,\-|:\s]+$/, "");
}
