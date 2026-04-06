self.addEventListener('install', (p) => {
  self.skipWaiting();
});

self.addEventListener('fetch', (p) => {
  // 앱 설치 조건을 충족하기 위한 최소한의 fetch 이벤트
});