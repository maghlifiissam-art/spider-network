const C='reels-v12';
self.addEventListener('install',e=>{self.skipWaiting();e.waitUntil(caches.open(C).then(c=>c.addAll(['./','index.html','common.js','i18n.js','icon.svg','feed.json','manifest.webmanifest']).catch(()=>{})))});
self.addEventListener('activate',e=>e.waitUntil(caches.keys().then(k=>Promise.all(k.filter(x=>x!==C).map(x=>caches.delete(x)))).then(()=>self.clients.claim())));
self.addEventListener('fetch',e=>{const r=e.request;if(r.method!=='GET')return;const u=new URL(r.url);const st=(u.origin===location.origin&&/\.(html|js|svg|json|webmanifest)$|\/$/.test(u.pathname))||u.hostname==='cdn.jsdelivr.net';if(!st)return;
e.respondWith(fetch(r,{cache:'no-cache'}).then(x=>{if(x.ok){const y=x.clone();caches.open(C).then(c=>c.put(r,y))}return x}).catch(()=>caches.open(C).then(c=>c.match(r))))});
