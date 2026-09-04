import { useState, useCallback } from 'react';
import { useToast } from '../stores/toast';

/**
 * Floating glass feedback widget — lets users quickly send experience ratings.
 * Appears as a small floating button in the bottom-right corner.
 */
export default function FeedbackWidget() {
  const [open, setOpen] = useState(false);
  const [rating, setRating] = useState<number | null>(null);
  const [comment, setComment] = useState('');
  const [submitted, setSubmitted] = useState(false);
  const toast = useToast();

  const handleSubmit = useCallback(() => {
    if (rating === null) return;

    // In production, POST to /api/feedback. For now, show a confirmation toast.
    toast.success(
      'Thanks for your feedback!',
      rating >= 4
        ? 'Glad you\'re enjoying Freebuff.'
        : 'We\'ll work on improving your experience.'
    );
    setSubmitted(true);
    setTimeout(() => {
      setOpen(false);
      setSubmitted(false);
      setRating(null);
      setComment('');
    }, 1500);
  }, [rating, toast]);

  const emojis = [
    { value: 1, emoji: '😞', label: 'Frustrated' },
    { value: 2, emoji: '😐', label: 'Okay' },
    { value: 3, emoji: '🙂', label: 'Good' },
    { value: 4, emoji: '😊', label: 'Great' },
    { value: 5, emoji: '🤩', label: 'Amazing' },
  ];

  return (
    <div className="fixed bottom-6 right-6 z-[80]">
      {/* Collapsed: floating glass button */}
      {!open && (
        <button
          onClick={() => setOpen(true)}
          className="glass-btn-primary w-12 h-12 rounded-full flex items-center justify-center shadow-lg shadow-blue-500/25 hover:shadow-xl hover:shadow-blue-500/30 transition-all hover:scale-105 active:scale-95"
          title="Send feedback"
          aria-label="Open feedback form"
        >
          <svg className="h-5 w-5 text-white" fill="none" viewBox="0 0 24 24" strokeWidth={1.5} stroke="currentColor">
            <path strokeLinecap="round" strokeLinejoin="round" d="M7.5 8.25h9m-9 3H12m-9.75 1.51c0 1.6 1.123 2.994 2.707 3.227 1.129.166 2.27.293 3.423.379.35.026.67.21.865.501L12 21l2.755-4.133a1.14 1.14 0 01.865-.501 48.172 48.172 0 003.423-.379c1.584-.233 2.707-1.626 2.707-3.228V6.741c0-1.602-1.123-2.995-2.707-3.228A48.394 48.394 0 0012 3c-2.392 0-4.744.175-7.043.513C3.373 3.746 2.25 5.14 2.25 6.741v6.018z" />
          </svg>
        </button>
      )}

      {/* Expanded: glass feedback panel */}
      {open && (
        <div className="glass-strong rounded-[20px] w-80 p-5 animate-glass-in shadow-2xl border border-white/40 dark:border-white/10">
          {submitted ? (
            <div className="text-center py-4">
              <div className="text-4xl mb-3">✨</div>
              <p className="text-sm font-semibold text-slate-900 dark:text-slate-100">Thank you!</p>
              <p className="text-xs text-slate-500 dark:text-slate-400 mt-1">Your feedback helps us improve.</p>
            </div>
          ) : (
            <>
              <div className="flex items-center justify-between mb-4">
                <h3 className="text-sm font-semibold text-slate-900 dark:text-slate-100">How was your experience?</h3>
                <button
                  onClick={() => setOpen(false)}
                  className="text-slate-400 hover:text-slate-600 dark:hover:text-slate-200 text-xs p-1 rounded-lg hover:bg-white/40 transition-colors"
                  aria-label="Close feedback"
                >
                  ✕
                </button>
              </div>

              {/* Emoji rating */}
              <div className="flex items-center justify-between mb-4">
                {emojis.map((e) => (
                  <button
                    key={e.value}
                    onClick={() => setRating(e.value)}
                    className={`
                      w-11 h-11 rounded-xl flex items-center justify-center text-xl
                      transition-all duration-200
                      ${rating === e.value
                        ? 'bg-white/80 dark:bg-white/15 border border-blue-400/40 shadow-md scale-110 ring-2 ring-blue-400/20'
                        : 'bg-white/40 dark:bg-white/5 border border-white/40 dark:border-white/10 hover:bg-white/60 dark:hover:bg-white/10 hover:scale-105'
                      }
                    `}
                    title={e.label}
                  >
                    {e.emoji}
                  </button>
                ))}
              </div>

              {/* Comment */}
              {rating !== null && (
                <div className="animate-glass-in">
                  <textarea
                    value={comment}
                    onChange={(e) => setComment(e.target.value)}
                    placeholder="Tell us more (optional)..."
                    rows={3}
                    className="w-full glass-input rounded-xl text-sm resize-none mb-3 placeholder-slate-400 dark:placeholder-slate-500"
                  />
                  <button
                    onClick={handleSubmit}
                    className="w-full glass-button-primary text-white text-sm font-semibold rounded-xl px-4 py-2.5 transition-all"
                  >
                    Send Feedback
                  </button>
                </div>
              )}
            </>
          )}
        </div>
      )}
    </div>
  );
}
