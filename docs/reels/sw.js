const C='reels-v8';self.addEventListener('install',e=>e.waitUntil(caches.open(C).then(c=>c.addAll(['./','index.html','groups.html','account.html','channel.html','common.js','i18n.js','publish.html','series.html','live.html','posts.html','icon.svg','feed.json','manifest.webmanifest']))));
self.addEventListener('fetch',e=>e.respondWith(fetch(e.request).catch(()=>caches.match(e.request))));

