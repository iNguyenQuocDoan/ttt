// Luu cac trang da mo de doc lai khi mat mang.
// Trang va CSS/JS: lay ban moi tren mang truoc, mat mang thi dung ban da luu.
// Font khong doi: dung ban da luu truoc.

var CACHE = "tth-v1";
var CORE = [
  "./",
  "index.html",
  "assets/style.css",
  "assets/reader.js",
  "assets/fonts/fonts.css",
  "assets/fonts/literata-normal-latin.woff2",
  "assets/fonts/literata-normal-latin-ext.woff2",
  "assets/fonts/literata-normal-vietnamese.woff2",
  "assets/fonts/literata-italic-latin.woff2",
  "assets/fonts/literata-italic-latin-ext.woff2",
  "assets/fonts/literata-italic-vietnamese.woff2"
];

self.addEventListener("install", function (event) {
  event.waitUntil(
    caches.open(CACHE)
      .then(function (cache) { return cache.addAll(CORE); })
      .then(function () { return self.skipWaiting(); })
  );
});

self.addEventListener("activate", function (event) {
  event.waitUntil(
    caches.keys()
      .then(function (keys) {
        return Promise.all(keys.filter(function (k) { return k !== CACHE; })
          .map(function (k) { return caches.delete(k); }));
      })
      .then(function () { return self.clients.claim(); })
  );
});

function remember(request, response) {
  if (response.ok && response.type === "basic") {
    var copy = response.clone();
    caches.open(CACHE).then(function (cache) { cache.put(request, copy); });
  }
  return response;
}

self.addEventListener("fetch", function (event) {
  var request = event.request;
  if (request.method !== "GET") return;
  var url = new URL(request.url);
  if (url.origin !== self.location.origin) return;

  if (url.pathname.indexOf("/assets/fonts/") !== -1) {
    event.respondWith(
      caches.match(request).then(function (hit) {
        return hit || fetch(request).then(function (res) { return remember(request, res); });
      })
    );
    return;
  }

  event.respondWith(
    fetch(request)
      .then(function (res) { return remember(request, res); })
      .catch(function () {
        return caches.match(request, { ignoreSearch: true }).then(function (hit) {
          if (hit) return hit;
          if (request.mode === "navigate") return caches.match("index.html");
          return Response.error();
        });
      })
  );
});
