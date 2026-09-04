import { useState, useEffect } from 'react';
import { api } from '../api';

interface Meeting {
  id: string;
  title: string;
  description: string;
  created_by: string;
  start_time: string;
  end_time: string;
  location: string;
  meeting_url: string;
  attendee_count: number;
  created_at: string;
}

export function MeetingScheduler() {
  const [meetings, setMeetings] = useState<Meeting[]>([]);
  const [loading, setLoading] = useState(true);
  const [showCreate, setShowCreate] = useState(false);
  const [form, setForm] = useState({
    title: '',
    description: '',
    start_time: '',
    end_time: '',
    location: '',
    meeting_url: '' });

  useEffect(() => {
    loadMeetings();
  }, []);

  const loadMeetings = async () => {
    try {
      const data = await api.request('/meetings?limit=100');
      setMeetings(data);
    } catch (e) {
      console.error('Failed to load meetings', e);
    }
    setLoading(false);
  };

  const createMeeting = async () => {
    if (!form.title || !form.start_time || !form.end_time) return;
    try {
      await api.request('/meetings', {
        method: 'POST',
        body: JSON.stringify(form) });
      setForm({ title: '', description: '', start_time: '', end_time: '', location: '', meeting_url: '' });
      setShowCreate(false);
      loadMeetings();
    } catch (e) {
      console.error('Failed to create meeting', e);
    }
  };

  const deleteMeeting = async (id: string) => {
    try {
      await api.request(`/meetings/${id}`, { method: 'DELETE' });
      setMeetings(prev => prev.filter(m => m.id !== id));
    } catch (e) {
      console.error('Failed to delete meeting', e);
    }
  };

  const formatTime = (iso: string) => {
    try {
      const d = new Date(iso);
      return d.toLocaleString([], { month: 'short', day: 'numeric', hour: '2-digit', minute: '2-digit' });
    } catch {
      return iso;
    }
  };

  const isUpcoming = (iso: string) => new Date(iso) > new Date();

  if (loading) return <div className="text-gray-400 py-8 text-center">Loading meetings...</div>;

  return (
    <div className="space-y-6">
      <div className="flex items-center justify-between">
        <h1 className="text-2xl font-bold text-white">Meetings</h1>
        <button
          onClick={() => setShowCreate(!showCreate)}
          className="px-4 py-2 bg-indigo-600 hover:bg-indigo-500 text-white rounded-lg text-sm font-medium transition-colors"
        >
          + Schedule Meeting
        </button>
      </div>

      {showCreate && (
        <div className="p-4 bg-white/[0.05] rounded-xl border border-white/10 space-y-3">
          <input
            type="text"
            placeholder="Meeting title..."
            value={form.title}
            onChange={e => setForm(f => ({ ...f, title: e.target.value }))}
            className="w-full px-3 py-2 bg-white/5 border border-white/10 rounded-lg text-sm text-white placeholder-gray-500"
            autoFocus
          />
          <textarea
            placeholder="Description (optional)"
            value={form.description}
            onChange={e => setForm(f => ({ ...f, description: e.target.value }))}
            className="w-full px-3 py-2 bg-white/5 border border-white/10 rounded-lg text-sm text-white placeholder-gray-500 h-20 resize-none"
          />
          <div className="grid grid-cols-2 gap-3">
            <div>
              <label className="text-xs text-gray-400 mb-1 block">Start</label>
              <input
                type="datetime-local"
                value={form.start_time}
                onChange={e => setForm(f => ({ ...f, start_time: e.target.value }))}
                className="w-full px-3 py-2 bg-white/5 border border-white/10 rounded-lg text-sm text-white"
              />
            </div>
            <div>
              <label className="text-xs text-gray-400 mb-1 block">End</label>
              <input
                type="datetime-local"
                value={form.end_time}
                onChange={e => setForm(f => ({ ...f, end_time: e.target.value }))}
                className="w-full px-3 py-2 bg-white/5 border border-white/10 rounded-lg text-sm text-white"
              />
            </div>
          </div>
          <div className="grid grid-cols-2 gap-3">
            <input
              type="text"
              placeholder="Location"
              value={form.location}
              onChange={e => setForm(f => ({ ...f, location: e.target.value }))}
              className="px-3 py-2 bg-white/5 border border-white/10 rounded-lg text-sm text-white placeholder-gray-500"
            />
            <input
              type="text"
              placeholder="Meeting URL"
              value={form.meeting_url}
              onChange={e => setForm(f => ({ ...f, meeting_url: e.target.value }))}
              className="px-3 py-2 bg-white/5 border border-white/10 rounded-lg text-sm text-white placeholder-gray-500"
            />
          </div>
          <div className="flex gap-2">
            <button onClick={createMeeting} className="px-4 py-2 bg-green-600 hover:bg-green-500 text-white rounded-lg text-sm">
              Schedule
            </button>
            <button onClick={() => setShowCreate(false)} className="px-4 py-2 text-gray-400 hover:text-white text-sm">
              Cancel
            </button>
          </div>
        </div>
      )}

      <div className="space-y-3">
        {meetings.map(meeting => (
          <div
            key={meeting.id}
            className={`p-4 rounded-xl border transition-colors ${
              isUpcoming(meeting.start_time)
                ? 'bg-white/[0.05] border-white/10'
                : 'bg-white/[0.02] border-white/5 opacity-60'
            }`}
          >
            <div className="flex items-start justify-between">
              <div className="flex-1">
                <div className="flex items-center gap-2">
                  <h3 className="text-sm font-medium text-white">{meeting.title}</h3>
                  {isUpcoming(meeting.start_time) && (
                    <span className="px-2 py-0.5 bg-green-500/20 text-green-400 rounded-full text-[10px]">Upcoming</span>
                  )}
                </div>
                <p className="text-xs text-gray-400 mt-1">
                  {formatTime(meeting.start_time)} - {formatTime(meeting.end_time)}
                </p>
                {meeting.location && (
                  <p className="text-xs text-gray-500 mt-1">Location: {meeting.location}</p>
                )}
                {meeting.meeting_url && (
                  <a href={meeting.meeting_url} target="_blank" rel="noopener noreferrer" className="text-xs text-indigo-400 hover:text-indigo-300 mt-1 inline-block">
                    Join Meeting
                  </a>
                )}
                <p className="text-[10px] text-gray-600 mt-2">{meeting.attendee_count} attendee(s)</p>
              </div>
              <button onClick={() => deleteMeeting(meeting.id)} className="text-gray-600 hover:text-red-400 text-xs">
                Delete
              </button>
            </div>
          </div>
        ))}
        {meetings.length === 0 && (
          <div className="text-center text-gray-400 py-8">No meetings scheduled</div>
        )}
      </div>
    </div>
  );
}
