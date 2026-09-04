import { useState } from 'react';
import { useAuth } from '../stores/auth';
import { Button } from './ui';

interface Comment {
  id: string;
  author: string;
  authorEmail: string;
  text: string;
  createdAt: string;
  replies?: Comment[];
}

interface CommentThreadProps {
  resourceId: string;
  resourceType: string;
}

const MOCK_COMMENTS: Comment[] = [
  { id: '1', author: 'Sarah Chen', authorEmail: 'sarah@treasury.gov', text: 'The refinancing risk on this strategy looks elevated. Can we run additional scenarios with higher rate sensitivity?', createdAt: '2h ago', replies: [
    { id: '1-1', author: 'James Park', authorEmail: 'james@treasury.gov', text: 'Agreed. I\'ve added 3 more scenarios to the sensitivity analysis. Results should be ready in ~5 minutes.', createdAt: '1h ago' },
  ]},
  { id: '2', author: 'Maria Rodriguez', authorEmail: 'maria@treasury.gov', text: 'The currency exposure to EUR is at 34% — above our internal limit of 30%. Should we hedge?', createdAt: '45m ago' },
];

export default function CommentThread({ resourceId, resourceType }: CommentThreadProps) {
  const { user } = useAuth();
  const [comments, setComments] = useState<Comment[]>(MOCK_COMMENTS);
  const [newComment, setNewComment] = useState('');
  const [replyTo, setReplyTo] = useState<string | null>(null);

  const handleSubmit = () => {
    if (!newComment.trim()) return;
    const comment: Comment = {
      id: String(Date.now()),
      author: user?.email?.split('@')[0] || 'You',
      authorEmail: user?.email || '',
      text: newComment,
      createdAt: 'Just now' };

    if (replyTo) {
      setComments((prev) =>
        prev.map((c) =>
          c.id === replyTo
            ? { ...c, replies: [...(c.replies || []), comment] }
            : c
        )
      );
    } else {
      setComments((prev) => [...prev, comment]);
    }
    setNewComment('');
    setReplyTo(null);
  };

  return (
    <div className="glass-card p-4">
      <h3 className="text-sm font-semibold text-white/80 mb-3">
        Comments ({comments.reduce((acc, c) => acc + 1 + (c.replies?.length || 0), 0)})
      </h3>

      <div className="space-y-3 max-h-80 overflow-y-auto">
        {comments.map((comment) => (
          <div key={comment.id}>
            <div className="p-3 rounded-xl bg-white/[0.03] border border-white/5">
              <div className="flex items-center justify-between mb-1">
                <span className="text-xs font-medium text-white/80">{comment.author}</span>
                <span className="text-[10px] text-white/30">{comment.createdAt}</span>
              </div>
              <p className="text-sm text-white/60">{comment.text}</p>
              <button
                onClick={() => setReplyTo(replyTo === comment.id ? null : comment.id)}
                className="text-[10px] text-blue-400/70 hover:text-blue-400 mt-1"
              >
                Reply
              </button>
            </div>

            {comment.replies?.map((reply) => (
              <div key={reply.id} className="ml-6 mt-2 p-3 rounded-xl bg-white/[0.02] border border-white/5">
                <div className="flex items-center justify-between mb-1">
                  <span className="text-xs font-medium text-white/70">{reply.author}</span>
                  <span className="text-[10px] text-white/30">{reply.createdAt}</span>
                </div>
                <p className="text-sm text-white/50">{reply.text}</p>
              </div>
            ))}
          </div>
        ))}
      </div>

      {replyTo && (
        <div className="flex items-center gap-2 mt-2 text-xs text-white/40">
          <span>Replying to thread</span>
          <button onClick={() => setReplyTo(null)} className="text-red-400/60 hover:text-red-400">✕</button>
        </div>
      )}

      <div className="flex gap-2 mt-3">
        <input
          type="text"
          value={newComment}
          onChange={(e) => setNewComment(e.target.value)}
          onKeyDown={(e) => e.key === 'Enter' && handleSubmit()}
          placeholder="Add a comment..."
          className="flex-1 bg-white/5 border border-white/10 rounded-xl px-3 py-2 text-sm text-white placeholder:text-white/30 focus:outline-none focus:ring-2 focus:ring-blue-500/50"
        />
        <Button variant="primary" size="sm" onClick={handleSubmit}>Post</Button>
      </div>
    </div>
  );
}
