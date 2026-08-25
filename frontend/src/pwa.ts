// PWA registration — manual fallback when vite-plugin-pwa not installed
export function registerSW() {
  if (typeof window === 'undefined' || !('serviceWorker' in navigator)) return;

  window.addEventListener('load', () => {
    const swUrl = '/sw.js';
    navigator.serviceWorker.register(swUrl).then(reg => {
      // check for updates periodically
      setInterval(() => {
        reg.update().catch(() => {});
      }, 60 * 60 * 1000);

      reg.addEventListener('updatefound', () => {
        const worker = reg.installing;
        if (!worker) return;
        worker.addEventListener('statechange', () => {
          if (worker.state === 'installed' && navigator.serviceWorker.controller) {
            // new content available — optionally notify
            console.log('[PWA] New content available, will activate on next reload');
          }
        });
      });
    }).catch(err => {
      console.warn('[PWA] SW registration failed', err);
    });

    // reload when new SW takes control
    let refreshing = false;
    navigator.serviceWorker.addEventListener('controllerchange', () => {
      if (refreshing) return;
      refreshing = true;
      window.location.reload();
    });
  });
}
