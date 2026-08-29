/**
 * LiquidScene — Colorful animated background that glass distorts
 * 
 * This is the "scene" behind the glass. The entire viewport
 * has a backdrop-filter over this scene, creating the liquid glass look.
 */
import { useEffect, useRef } from 'react';

interface Blob {
  x: number;
  y: number;
  r: number;
  vx: number;
  vy: number;
  color: string;
  phase: number;
}

const BLOB_COLORS = [
  'rgba(200, 169, 81, 0.6)',   // gold
  'rgba(180, 100, 220, 0.5)',  // purple
  'rgba(60, 140, 255, 0.5)',   // blue
  'rgba(255, 100, 120, 0.4)',  // pink
  'rgba(40, 200, 180, 0.4)',   // teal
  'rgba(140, 80, 255, 0.45)',  // violet
  'rgba(255, 180, 60, 0.4)',   // amber
  'rgba(60, 200, 120, 0.35)',  // emerald
];

function generateBlobs(count: number, w: number, h: number): Blob[] {
  return Array.from({ length: count }, (_, i) => ({
    x: Math.random() * w,
    y: Math.random() * h,
    r: 150 + Math.random() * 250,
    vx: (Math.random() - 0.5) * 0.3,
    vy: (Math.random() - 0.5) * 0.25,
    color: BLOB_COLORS[i % BLOB_COLORS.length],
    phase: Math.random() * Math.PI * 2,
  }));
}

export default function LiquidScene({ children }: { children: React.ReactNode }) {
  const canvasRef = useRef<HTMLCanvasElement>(null);

  useEffect(() => {
    const canvas = canvasRef.current;
    if (!canvas) return;
    const ctx = canvas.getContext('2d');
    if (!ctx) return;

    let w = window.innerWidth;
    let h = window.innerHeight;
    canvas.width = w;
    canvas.height = h;

    const blobs = generateBlobs(10, w, h);
    let time = 0;
    let animFrame: number;

    const resize = () => {
      w = window.innerWidth;
      h = window.innerHeight;
      canvas.width = w;
      canvas.height = h;
    };
    window.addEventListener('resize', resize);

    const draw = () => {
      time += 0.008;
      ctx.clearRect(0, 0, w, h);

      // Deep dark base
      ctx.fillStyle = '#0a0b0e';
      ctx.fillRect(0, 0, w, h);

      // Draw animated blobs
      for (const blob of blobs) {
        blob.x += blob.vx + Math.sin(time + blob.phase) * 0.5;
        blob.y += blob.vy + Math.cos(time * 0.7 + blob.phase) * 0.4;

        // Wrap around
        if (blob.x < -blob.r) blob.x = w + blob.r;
        if (blob.x > w + blob.r) blob.x = -blob.r;
        if (blob.y < -blob.r) blob.y = h + blob.r;
        if (blob.y > h + blob.r) blob.y = -blob.r;

        const pulseR = blob.r + Math.sin(time * 0.5 + blob.phase) * 30;

        const grad = ctx.createRadialGradient(blob.x, blob.y, 0, blob.x, blob.y, pulseR);
        grad.addColorStop(0, blob.color);
        grad.addColorStop(0.5, blob.color.replace(/[\d.]+\)$/, '0.2)'));
        grad.addColorStop(1, 'transparent');

        ctx.fillStyle = grad;
        ctx.beginPath();
        ctx.arc(blob.x, blob.y, pulseR, 0, Math.PI * 2);
        ctx.fill();
      }

      // Subtle noise/grain overlay
      ctx.globalAlpha = 0.03;
      for (let i = 0; i < 50; i++) {
        const nx = Math.random() * w;
        const ny = Math.random() * h;
        ctx.fillStyle = '#fff';
        ctx.fillRect(nx, ny, 1, 1);
      }
      ctx.globalAlpha = 1;

      animFrame = requestAnimationFrame(draw);
    };

    animFrame = requestAnimationFrame(draw);

    return () => {
      cancelAnimationFrame(animFrame);
      window.removeEventListener('resize', resize);
    };
  }, []);

  return (
    <div className="relative min-h-screen overflow-hidden" style={{ background: '#0a0b0e' }}>
      {/* Colorful animated scene — this is what glass distorts */}
      <canvas
        ref={canvasRef}
        className="fixed inset-0"
        style={{ zIndex: 0 }}
      />

      {/* GLASS LAYER — backdrop-filter over the entire viewport */}
      <div
        className="fixed inset-0"
        style={{
          zIndex: 1,
          backdropFilter: 'blur(40px) saturate(180%) brightness(1.05) contrast(1.02)',
          WebkitBackdropFilter: 'blur(40px) saturate(180%) brightness(1.05) contrast(1.02)',
        }}
      />

      {/* Specular highlight — the light streak across the top */}
      <div
        className="fixed inset-x-0 top-0 h-[1px]"
        style={{
          zIndex: 2,
          background: 'linear-gradient(90deg, transparent 0%, rgba(255,255,255,0.15) 20%, rgba(255,255,255,0.3) 50%, rgba(255,255,255,0.15) 80%, transparent 100%)',
        }}
      />

      {/* Content layer */}
      <div className="relative" style={{ zIndex: 3 }}>
        {children}
      </div>
    </div>
  );
}
