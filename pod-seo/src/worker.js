import { PLATFORMS, findFlagged, fitTags, fitTitle } from "./rules.js";

const VISION = "@cf/meta/llama-4-scout-17b-16e-instruct";
const TEXT = "@cf/mistralai/mistral-small-3.1-24b-instruct";

const json = (o, s = 200) => new Response(JSON.stringify(o), { status: s, headers: { "content-type": "application/json", "cache-control": "no-store" } });

async function ipHash(req) {
  const ip = req.headers.get("cf-connecting-ip") || "x";
  const d = await crypto.subtle.digest("SHA-256", new TextEncoder().encode(ip + "pod-seo"));
  return [...new Uint8Array(d)].slice(0, 8).map((b) => b.toString(16).padStart(2, "0")).join("");
}

function toDataUrl(bytes) {
  let bin = ""; const u = Uint8Array.from(bytes);
  for (let i = 0; i < u.length; i += 8192) bin += String.fromCharCode.apply(null, u.subarray(i, i + 8192));
  return "data:image/jpeg;base64," + btoa(bin);
}

async function describeDesign(env, image, designText) {
  const r = await env.AI.run(VISION, {
    messages: [{ role: "user", content: [
      { type: "text", text: "Describe this print-on-demand design for a product listing. In 3 short lines: (1) main subject and any text on it (quote the text exactly), (2) art style and colors, (3) likely audience or occasion. No brand names." + (designText ? ` The seller says the exact text on the design is: "${designText}". Use that text.` : " Read any text letter by letter; if you cannot read it, say so instead of guessing.") },
      { type: "image_url", image_url: { url: toDataUrl(image) } },
    ] }],
    max_tokens: 220,
  });
  const t = r.response || r.choices?.[0]?.message?.content || "";
  return String(t).trim();
}

function listingPrompt(desc, niche, keys) {
  const rules = keys.map((k) => { const p = PLATFORMS[k]; return `${k}: title max ${p.titleMax} chars, give ${p.tagMax + 4} candidate tags (the best ones first), each max ${p.tagLen} chars, description max ${p.descMax} chars`; }).join("\n");
  return `You write SEO listings for print-on-demand sellers. Design description:\n${desc}\nSeller niche keyword: ${niche || "(none)"}\nWrite one listing per platform. Rules:\n${rules}\nTitle: put the main buyer search phrase first, then product-neutral descriptors, audience, occasion. Tags: multi-word buyer search phrases, no repeats, no brand or trademark names, no filler. Description: 2-3 plain sentences with the keywords, then a line about the gift occasion. Never invent claims about materials or sizes.\nReturn ONLY JSON: {"<platform>":{"title":"","tags":[""],"description":""}} for platforms: ${keys.join(", ")}.`;
}

function parseJson(txt) {
  const m = txt.match(/\{[\s\S]*\}/);
  if (!m) throw new Error("no json");
  return JSON.parse(m[0]);
}

export async function generate(env, image, niche, keys, designText) {
  const desc = await describeDesign(env, image, designText);
  const r = await env.AI.run(TEXT, { messages: [{ role: "user", content: listingPrompt(desc, niche, keys) }], max_tokens: 1400, temperature: 0.4 });
  const raw = r.choices?.[0]?.message?.content || (typeof r.response === "string" ? r.response : JSON.stringify(r.response));
  const data = parseJson(raw);
  const out = {};
  for (const k of keys) {
    const p = PLATFORMS[k]; const d = data[k] || {};
    const title = fitTitle(d.title, p);
    const tags = fitTags(d.tags, p);
    const description = String(d.description || "").slice(0, p.descMax);
    out[k] = { title, tags, description, flagged: findFlagged([title, tags.join(" "), description].join(" ")) };
    if (k === "teepublic") out[k].mainTag = tags[0] || "";
  }
  return { designSummary: desc, listings: out };
}

export default {
  async fetch(req, env) {
    const url = new URL(req.url);
    if (url.pathname === "/api/generate" && req.method === "POST") {
      let body;
      try { body = await req.json(); } catch { return json({ error: "bad json" }, 400); }
      const keys = (body.platforms || ["etsy", "redbubble", "teepublic"]).filter((k) => PLATFORMS[k]);
      const image = Array.isArray(body.image) ? body.image : null;
      if (!image || !keys.length || image.length > 400000) return json({ error: "send a resized image (bytes array) and at least one platform" }, 400);
      const day = new Date().toISOString().slice(0, 10);
      const key = `u:${day}:${await ipHash(req)}`;
      const used = parseInt((await env.USAGE.get(key)) || "0", 10);
      const limit = parseInt(env.FREE_PER_DAY || "5", 10);
      if (used >= limit) return json({ error: "free limit reached for today", limit }, 429);
      try {
        const res = await generate(env, image, String(body.niche || "").slice(0, 80), keys, String(body.designText || "").slice(0, 100));
        await env.USAGE.put(key, String(used + 1), { expirationTtl: 172800 });
        return json({ ...res, remaining: limit - used - 1 });
      } catch (e) {
        return json({ error: "generation failed, try again", detail: String(e.message || e).slice(0, 120) }, 502);
      }
    }
    return env.ASSETS.fetch(req);
  },
};
