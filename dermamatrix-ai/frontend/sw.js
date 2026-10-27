/* Offline explanation only. No authenticated API, PDF, image or app-page cache. */
const OFFLINE_CACHE='dermamatrix-offline-v1';
self.addEventListener('install',event=>event.waitUntil(caches.open(OFFLINE_CACHE).then(cache=>cache.addAll(['/offline.html']))));
self.addEventListener('activate',event=>event.waitUntil(caches.keys().then(keys=>Promise.all(keys.filter(key=>key.startsWith('dermamatrix-offline-')&&key!==OFFLINE_CACHE).map(key=>caches.delete(key)))).then(()=>self.clients.claim())));
self.addEventListener('fetch',event=>{
  const url=new URL(event.request.url);
  // All API traffic and health-bearing downloads go directly to the network.
  if(url.origin!==self.location.origin||event.request.method!=='GET'||url.pathname.startsWith('/api/'))return;
  if(event.request.mode==='navigate')event.respondWith(fetch(event.request).catch(()=>caches.match('/offline.html')));
});
