/**
 * QUANTIVE — Shared Frontend Utilities
 * Cache-Control: max-age=31536000, immutable
 */

// ── Market Time Display ──────────────────────────────────
function updateMarketTime() {
  const el = document.getElementById('market-time');
  if (!el) return;
  const now = new Date();
  const h = now.getHours().toString().padStart(2, '0');
  const m = now.getMinutes().toString().padStart(2, '0');
  const s = now.getSeconds().toString().padStart(2, '0');
  el.textContent = `${h}:${m}:${s} UTC`;
}
setInterval(updateMarketTime, 1000);
updateMarketTime();

// ── Smooth Scroll for Content Area ────────────────────────
function scrollToTop() {
  const content = document.querySelector('.content');
  if (content) content.scrollTo({ top: 0, behavior: 'smooth' });
}

// ── Toast Notifications ───────────────────────────────────
function showToast(message, type = 'info', duration = 3000) {
  const toast = document.createElement('div');
  const colors = {
    info: 'var(--blue)',
    success: 'var(--green)',
    warning: 'var(--yellow)',
    error: 'var(--red)',
  };
  toast.style.cssText = `
    position:fixed;bottom:24px;right:24px;z-index:9999;
    background:rgba(15,17,23,0.95);backdrop-filter:blur(20px);
    border:1px solid rgba(255,255,255,0.08);border-radius:10px;
    padding:12px 18px;font-size:13px;font-weight:500;color:var(--text);
    display:flex;align-items:center;gap:10px;
    animation:slideUp 0.2s cubic-bezier(0.16,1,0.3,1);
    box-shadow:0 8px 32px rgba(0,0,0,0.4);
  `;
  toast.innerHTML = `
    <div style="width:6px;height:6px;border-radius:50%;background:${colors[type]};flex-shrink:0"></div>
    <span>${message}</span>
  `;
  document.body.appendChild(toast);
  setTimeout(() => {
    toast.style.opacity = '0';
    toast.style.transform = 'translateY(10px)';
    toast.style.transition = 'all 0.2s';
    setTimeout(() => toast.remove(), 200);
  }, duration);
}

// ── Fetch with Error Handling ─────────────────────────────
async function apiFetch(url, options = {}) {
  try {
    const resp = await fetch(url, options);
    if (!resp.ok) {
      const err = await resp.json().catch(() => ({ detail: 'Request failed' }));
      throw new Error(err.detail || `HTTP ${resp.status}`);
    }
    return await resp.json();
  } catch (e) {
    showToast(e.message, 'error');
    throw e;
  }
}

// ── Number Formatting ─────────────────────────────────────
function formatB(value) {
  if (value >= 1e12) return `$${(value / 1e12).toFixed(1)}T`;
  if (value >= 1e9) return `$${(value / 1e9).toFixed(1)}B`;
  if (value >= 1e6) return `$${(value / 1e6).toFixed(0)}M`;
  return `$${value.toLocaleString()}`;
}

function formatPct(value, decimals = 1) {
  return `${value >= 0 ? '+' : ''}${value.toFixed(decimals)}%`;
}

function formatBps(value) {
  return `${value >= 0 ? '+' : ''}${value} bps`;
}

// ── Debounce ──────────────────────────────────────────────
function debounce(fn, delay = 300) {
  let timer;
  return (...args) => {
    clearTimeout(timer);
    timer = setTimeout(() => fn(...args), delay);
  };
}

// ── Keyboard Shortcuts ────────────────────────────────────
document.addEventListener('keydown', (e) => {
  // Cmd/Ctrl + K = Focus search (future)
  if ((e.metaKey || e.ctrlKey) && e.key === 'k') {
    e.preventDefault();
    // Future: open command palette
  }
  // Escape = Close modals
  if (e.key === 'Escape') {
    document.querySelectorAll('[id$="-modal"]').forEach(m => {
      m.style.display = 'none';
    });
  }
});

// ── CSS Animation (injected once) ─────────────────────────
if (!document.getElementById('q-animations')) {
  const style = document.createElement('style');
  style.id = 'q-animations';
  style.textContent = `
    @keyframes slideUp{from{opacity:0;transform:translateY(10px)}to{opacity:1;transform:translateY(0)}}
    @keyframes fadeIn{from{opacity:0}to{opacity:1}}
    @keyframes spin{from{transform:rotate(0deg)}to{transform:rotate(360deg)}}
    [data-loading]{opacity:0.5;pointer-events:none}
  `;
  document.head.appendChild(style);
}
