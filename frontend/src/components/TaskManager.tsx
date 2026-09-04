import { useState, useEffect } from 'react';
import { api } from '../api';

interface Task {
  id: string;
  title: string;
  description: string;
  status: string;
  priority: string;
  created_by: string;
  assigned_to: string | null;
  due_date: string | null;
  comment_count: number;
  created_at: string;
}

const PRIORITY_COLORS: Record<string, string> = {
  urgent: 'bg-red-500/20 text-red-400 border-red-500/30',
  high: 'bg-orange-500/20 text-orange-400 border-orange-500/30',
  medium: 'bg-yellow-500/20 text-yellow-400 border-yellow-500/30',
  low: 'bg-green-500/20 text-green-400 border-green-500/30' };

const STATUS_COLUMNS = [
  { key: 'todo', label: 'To Do', color: '#6b7280' },
  { key: 'in_progress', label: 'In Progress', color: '#3b82f6' },
  { key: 'done', label: 'Done', color: '#22c55e' },
];

export function TaskManager() {
  const [tasks, setTasks] = useState<Task[]>([]);
  const [loading, setLoading] = useState(true);
  const [showCreate, setShowCreate] = useState(false);
  const [newTitle, setNewTitle] = useState('');
  const [newPriority, setNewPriority] = useState('medium');

  useEffect(() => {
    loadTasks();
  }, []);

  const loadTasks = async () => {
    try {
      const data = await api.request('/tasks?limit=200');
      setTasks(data);
    } catch (e) {
      console.error('Failed to load tasks', e);
    }
    setLoading(false);
  };

  const createTask = async () => {
    if (!newTitle.trim()) return;
    try {
      await api.request('/tasks', {
        method: 'POST',
        body: JSON.stringify({ title: newTitle, priority: newPriority }) });
      setNewTitle('');
      setShowCreate(false);
      loadTasks();
    } catch (e) {
      console.error('Failed to create task', e);
    }
  };

  const updateStatus = async (taskId: string, newStatus: string) => {
    try {
      await api.request(`/tasks/${taskId}`, {
        method: 'PUT',
        body: JSON.stringify({ status: newStatus }) });
      setTasks(prev => prev.map(t => t.id === taskId ? { ...t, status: newStatus } : t));
    } catch (e) {
      console.error('Failed to update task', e);
    }
  };

  const deleteTask = async (taskId: string) => {
    try {
      await api.request(`/tasks/${taskId}`, { method: 'DELETE' });
      setTasks(prev => prev.filter(t => t.id !== taskId));
    } catch (e) {
      console.error('Failed to delete task', e);
    }
  };

  if (loading) return <div className="text-gray-400 py-8 text-center">Loading tasks...</div>;

  return (
    <div className="space-y-6">
      <div className="flex items-center justify-between">
        <h1 className="text-2xl font-bold text-white">Tasks</h1>
        <button
          onClick={() => setShowCreate(!showCreate)}
          className="px-4 py-2 bg-indigo-600 hover:bg-indigo-500 text-white rounded-lg text-sm font-medium transition-colors"
        >
          + New Task
        </button>
      </div>

      {showCreate && (
        <div className="p-4 bg-white/[0.05] rounded-xl border border-white/10 space-y-3">
          <input
            type="text"
            placeholder="Task title..."
            value={newTitle}
            onChange={e => setNewTitle(e.target.value)}
            onKeyDown={e => e.key === 'Enter' && createTask()}
            className="w-full px-3 py-2 bg-white/5 border border-white/10 rounded-lg text-sm text-white placeholder-gray-500"
            autoFocus
          />
          <div className="flex items-center gap-3">
            <select
              value={newPriority}
              onChange={e => setNewPriority(e.target.value)}
              className="px-3 py-2 bg-white/5 border border-white/10 rounded-lg text-sm text-white"
            >
              <option value="low">Low</option>
              <option value="medium">Medium</option>
              <option value="high">High</option>
              <option value="urgent">Urgent</option>
            </select>
            <button onClick={createTask} className="px-4 py-2 bg-green-600 hover:bg-green-500 text-white rounded-lg text-sm">
              Create
            </button>
            <button onClick={() => setShowCreate(false)} className="px-4 py-2 text-gray-400 hover:text-white text-sm">
              Cancel
            </button>
          </div>
        </div>
      )}

      <div className="grid grid-cols-1 md:grid-cols-3 gap-4">
        {STATUS_COLUMNS.map(col => {
          const colTasks = tasks.filter(t => t.status === col.key);
          return (
            <div key={col.key} className="space-y-3">
              <div className="flex items-center gap-2 mb-2">
                <span className="w-2 h-2 rounded-full" style={{ backgroundColor: col.color }} />
                <h3 className="text-sm font-medium text-gray-300">
                  {col.label} ({colTasks.length})
                </h3>
              </div>
              {colTasks.map(task => (
                <div key={task.id} className="p-3 bg-white/[0.03] rounded-lg border border-white/5 hover:bg-white/[0.06] transition-colors">
                  <div className="flex items-start justify-between gap-2">
                    <p className="text-sm text-white font-medium">{task.title}</p>
                    <button onClick={() => deleteTask(task.id)} className="text-gray-600 hover:text-red-400 text-xs">x</button>
                  </div>
                  {task.description && (
                    <p className="text-xs text-gray-500 mt-1 line-clamp-2">{task.description}</p>
                  )}
                  <div className="flex items-center gap-2 mt-2">
                    <span className={`px-2 py-0.5 rounded-full text-[10px] font-medium border ${PRIORITY_COLORS[task.priority] || PRIORITY_COLORS.medium}`}>
                      {task.priority}
                    </span>
                    {task.due_date && (
                      <span className="text-[10px] text-gray-500">Due {new Date(task.due_date).toLocaleDateString()}</span>
                    )}
                  </div>
                  <div className="flex gap-1 mt-2">
                    {STATUS_COLUMNS.filter(s => s.key !== task.status).map(s => (
                      <button
                        key={s.key}
                        onClick={() => updateStatus(task.id, s.key)}
                        className="px-2 py-1 bg-white/5 hover:bg-white/10 rounded text-[10px] text-gray-400 transition-colors"
                      >
                        Move to {s.label}
                      </button>
                    ))}
                  </div>
                </div>
              ))}
              {colTasks.length === 0 && (
                <p className="text-xs text-gray-600 text-center py-4">No tasks</p>
              )}
            </div>
          );
        })}
      </div>
    </div>
  );
}
