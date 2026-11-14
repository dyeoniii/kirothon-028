// 최소 서비스 워커: PWA 설치 조건 충족용. 캐시하지 않고 네트워크를 그대로 사용합니다.
self.addEventListener('install', () => self.skipWaiting());
self.addEventListener('activate', (e) => e.waitUntil(self.clients.claim()));
self.addEventListener('fetch', () => {});
