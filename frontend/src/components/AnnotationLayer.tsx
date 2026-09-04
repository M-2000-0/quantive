import { useState } from 'react';
import { useAuth } from '../stores/auth';
import { Button } from './ui';

interface Annotation {
  id: string;
  text: string;
  author: string;
  x: number;
  y: number;
  color: string;
  createdAt: string;
}

interface AnnotationLayerProps {
  resourceId: string;
  resourceType: string;
  width?: number;
  height?: number;
}

const COLORS = ['#3b82f6', '#10b981', '#f59e0b', '#ef4444', '#8b5cf6'];

const MOCK_ANNOTATIONS: Annotation[] = [
  { id: '1', text: 'Risk threshold exceeded here', author: 'Sarah', x: 65, y: 30, color: '#ef4444', createdAt: '2h ago' },
  { id: '2', text: 'Optimal rebalancing point', author: 'James', x: 40, y: 55, color: '#10b981', createdAt: '1h ago' },
];

export default function AnnotationLayer({ resourceId, resourceType }: AnnotationLayerProps) {
  const { user } = useAuth();
  const [annotations, setAnnotations] = useState<Annotation[]>(MOCK_ANNOTATIONS);
  const [isAdding, setIsAdding] = useState(false);
  const [newAnnotation, setNewAnnotation] = useState({ text: '', color: COLORS[0] });
  const [pendingPos, setPendingPos] = useState<{ x: number; y: number } | null>(null);
  const [expandedId, setExpandedId] = useState<string | null>(null);

  const handleCanvasClick = (e: React.MouseEvent<HTMLDivElement>) => {
    if (!isAdding) return;
    const rect = e.currentTarget.getBoundingClientRect();
    const x = ((e.clientX - rect.left) / rect.width) * 100;
    const y = ((e.clientY - rect.top) / rect.height) * 100;
    setPendingPos({ x, y });
  };

  const saveAnnotation = () => {
    if (!pendingPos || !newAnnotation.text.trim()) return;
    const annotation: Annotation = {
      id: String(Date.now()),
      text: newAnnotation.text,
      author: user?.email?.split('@')[0] || 'You',
      x: pendingPos.x,
      y: pendingPos.y,
      color: newAnnotation.color,
      createdAt: 'Just now' };
    setAnnotations((prev) => [...prev, annotation]);
    setNewAnnotation({ text: '', color: COLORS[0] });
    setPendingPos(null);
    setIsAdding(false);
  };

  return (
    <div className="relative">
      <div className="flex items-center justify-between mb-2">
        <h3 className="text-xs font-semibold text-white/60 uppercase tracking-wider">Annotations</h3>
        <div className="flex items-center gap-2">
          <Button
            variant={isAdding ? 'danger' : 'ghost'}
            size="sm"
            onClick={() => { setIsAdding(!isAdding); setPendingPos(null); }}
          >
            {isAdding ? 'Cancel' : '📌 Add Note'}
          </Button>
        </div>
      </div>

      <div
        className="relative min-h-[200px] rounded-xl border border-white/5 overflow-hidden"
        onClick={handleCanvasClick}
      >
        {/* Annotations */}
        {annotations.map((a) => (
          <div
            key={a.id}
            className="absolute cursor-pointer group"
            style={{ left: `${a.x}%`, top: `${a.y}%`, transform: 'translate(-50%, -100%)' }}
            onClick={(e) => { e.stopPropagation(); setExpandedId(expandedId === a.id ? null : a.id); }}
          >
            <div
              className="w-5 h-5 rounded-full flex items-center justify-center text-[10px] font-bold text-white shadow-lg transition-transform group-hover:scale-125"
              style={{ backgroundColor: a.color }}
            >
              📌
            </div>
            {expandedId === a.id && (
              <div className="absolute bottom-full left-1/2 -translate-x-1/2 mb-2 w-48 p-3 rounded-xl bg-slate-900/95 border border-white/10 shadow-xl backdrop-blur-xl z-10">
                <p className="text-xs text-white/80">{a.text}</p>
                <p className="text-[10px] text-white/40 mt-1">— {a.author} • {a.createdAt}</p>
              </div>
            )}
          </div>
        ))}

        {/* Pending annotation */}
        {pendingPos && (
          <div
            className="absolute z-20"
            style={{ left: `${pendingPos.x}%`, top: `${pendingPos.y}%`, transform: 'translate(-50%, -100%)' }}
          >
            <div className="p-3 rounded-xl bg-slate-900/95 border border-white/20 shadow-xl backdrop-blur-xl w-56">
              <input
                type="text"
                value={newAnnotation.text}
                onChange={(e) => setNewAnnotation((p) => ({ ...p, text: e.target.value }))}
                onKeyDown={(e) => e.key === 'Enter' && saveAnnotation()}
                placeholder="Add annotation..."
                autoFocus
                className="w-full bg-white/5 border border-white/10 rounded-lg px-2 py-1 text-xs text-white placeholder:text-white/30 focus:outline-none"
              />
              <div className="flex items-center justify-between mt-2">
                <div className="flex gap-1">
                  {COLORS.map((c) => (
                    <button
                      key={c}
                      onClick={(e) => { e.stopPropagation(); setNewAnnotation((p) => ({ ...p, color: c })); }}
                      className={`w-4 h-4 rounded-full border-2 ${newAnnotation.color === c ? 'border-white' : 'border-transparent'}`}
                      style={{ backgroundColor: c }}
                    />
                  ))}
                </div>
                <Button variant="primary" size="sm" onClick={(e) => { e.stopPropagation(); saveAnnotation(); }}>
                  Save
                </Button>
              </div>
            </div>
          </div>
        )}

        {annotations.length === 0 && !isAdding && (
          <div className="absolute inset-0 flex items-center justify-center text-white/20 text-sm">
            Click "📌 Add Note" to annotate this view
          </div>
        )}
      </div>
    </div>
  );
}
