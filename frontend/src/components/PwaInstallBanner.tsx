import { useEffect, useState } from 'react';

interface BeforeInstallPromptEvent extends Event {
  prompt: () => Promise<void>;
  userChoice: Promise<{ outcome: 'accepted' | 'dismissed' }>;
}

export default function PwaInstallBanner() {
  const [deferred, setDeferred] = useState<BeforeInstallPromptEvent | null>(null);
  const [visible, setVisible] = useState(false);
  const [offline, setOffline] = useState(false);

  useEffect(() => {
    const handler = (e: Event) => {
      e.preventDefault();
      setDeferred(e as BeforeInstallPromptEvent);
      // respect dismissal cooldown
      try {
        const dismissed = localStorage.getItem('quantive_pwa_dismissed');
        if (dismissed && Date.now() - Number(dismissed) < 1000 * 60 * 60 * 24 * 3) return;
      } catch { /* */ }
      setVisible(true);
    };
    window.addEventListener('beforeinstallprompt', handler as EventListener);

    const offlineHandler = () => setOffline(!navigator.onLine);
    window.addEventListener('online', offlineHandler);
    window.addEventListener('offline', offlineHandler);
    setOffline(!navigator.onLine);

    return () => {
      window.removeEventListener('beforeinstallprompt', handler as EventListener);
      window.removeEventListener('online', offlineHandler);
      window.removeEventListener('offline', offlineHandler);
    };
  }, []);

  const handleInstall = async () => {
    if (!deferred) return;
    await deferred.prompt();
    const choice = await deferred.userChoice;
    if (choice.outcome === 'accepted') setVisible(false);
    setDeferred(null);
  };

  const handleDismiss = () => {
    setVisible(false);
    try { localStorage.setItem('quantive_pwa_dismissed', String(Date.now())); } catch { /* */ }
  };

  return (
    <>
      {/* Offline fallback banner */}
      {offline && (
        <div className="fixed bottom-4 left-1/2 -translate-x-1/2 z-40 glass-heavy px-4 py-2.5 flex items-center gap-3 border border-amber-200/40 dark:border-amber-800/30 shadow-xl max-w-[92vw]">
          <span className="h-2 w-2 rounded-full bg-amber-500 animate-pulse shrink-0" />
          <span className="text-sm font-medium text-slate-800 dark:text-slate-100">You’re offline — cached data will be used.</span>
        </div>
      )}

      {/* Install prompt — liquid glass */}
      {visible && deferred && (
        <div className="fixed bottom-4 left-1/2 -translate-x-1/2 z-50 w-[min(520px,92vw)] glass-heavy p-4 flex items-center gap-4 border border-white/40 dark:border-white/10 shadow-[0_24px_64px_rgba(0,0,0,0.18)] animate-glass-in">
          <div className="h-11 w-11 rounded-xl bg-gradient-to-br from-blue-600 to-indigo-600 flex items-center justify-center text-white font-bold shadow-lg ring-1 ring-white/20 shrink-0">Q</div>
          <div className="flex-1 min-w-0">
            <p className="text-sm font-semibold text-slate-900 dark:text-white tracking-tight">Install Quantive</p>
            <p className="text-xs text-slate-600 dark:text-slate-300">Add to home screen for offline access & faster launch.</p>
          </div>
          <div className="flex items-center gap-2 shrink-0">
            <button onClick={handleDismiss} className="glass-btn text-xs py-1.5 px-3">Not now</button>
            <button onClick={handleInstall} className="glass-btn-primary text-xs py-1.5 px-4">Install</button>
          </div>
        </div>
      )}
    </>
  );
}
