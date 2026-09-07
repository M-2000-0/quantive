import { useState } from 'react';
import { Card } from './ui';
import { Badge } from './ui';

interface Goal {
 id: string;
 name: string;
 target: number;
 current: number;
 unit: string;
 direction: 'up' | 'down' | 'equal';
 deadline?: string;
}

const MOCK_GOALS: Goal[] = [
 { id: '1', name: 'Reduce Weighted Coupon', target: 3.5, current: 3.82, unit: '%', direction: 'down', deadline: '2026-12-31' },
 { id: '2', name: 'Increase Green Bond Ratio', target: 25, current: 18, unit: '%', direction: 'up', deadline: '2027-06-30' },
 { id: '3', name: 'Maturity Spread (Max-Min)', target: 5, current: 7.2, unit: 'years', direction: 'down', deadline: '2026-12-31' },
 { id: '4', name: 'Average Credit Rating', target: 7.5, current: 7.1, unit: '/10', direction: 'up', deadline: '2027-12-31' },
];

export default function GoalTracker() {
 const [goals, setGoals] = useState<Goal[]>(MOCK_GOALS);

 const getProgress = (goal: Goal) => {
 if (goal.direction === 'down') {
 const range = goal.current - goal.target;
 const initial = goal.current + range; // assume starting point
 return Math.min(Math.max(((initial - goal.current) / (initial - goal.target)) * 100, 0), 100);
 }
 return Math.min((goal.current / goal.target) * 100, 100);
 };

 const getStatus = (goal: Goal): 'on-track' | 'at-risk' | 'achieved' => {
 const progress = getProgress(goal);
 if (goal.direction === 'down' && goal.current <= goal.target) return 'achieved';
 if (goal.direction === 'up' && goal.current >= goal.target) return 'achieved';
 if (progress >= 70) return 'on-track';
 return 'at-risk';
 };

 const statusColors = { 'on-track': 'success', 'at-risk': 'warning', 'achieved': 'success' };

 return (
 <div className="space-y-3">
 <h3 className="text-sm font-semibold text-white/80">Portfolio Goals</h3>
 {goals.map((goal) => {
 const progress = getProgress(goal);
 const status = getStatus(goal);
 return (
 <Card key={goal.id} className="p-4">
 <div className="flex items-center justify-between mb-2">
 <div className="flex items-center gap-2">
 <span className="text-sm font-medium text-white">{goal.name}</span>
 <Badge variant={statusColors[status] as 'success'}>
 {status === 'achieved' ? ' <CheckCircle className="w-4 h-4 inline" /> Achieved' : status === 'on-track' ? ' <TrendingUp className="w-4 h-4 inline" /> On Track' : ' <AlertTriangle className="w-4 h-4 inline" /> At Risk'}
 </Badge>
 </div>
 {goal.deadline && <span className="text-[10px] text-white/30">Due: {goal.deadline}</span>}
 </div>
 <div className="flex items-center gap-3">
 <div className="flex-1 bg-white/10 rounded-full h-2.5 overflow-hidden">
 <div
 className={`h-full rounded-full transition-all duration-500 ${
 status === 'achieved' ? 'bg-green-500' : status === 'on-track' ? 'bg-blue-500' : 'bg-yellow-500'
 }`}
 style={{ width: `${progress}%` }}
 />
 </div>
 <span className="text-xs text-white/60 min-w-[60px] text-right">
 {goal.current}{goal.unit} / {goal.target}{goal.unit}
 </span>
 </div>
 </Card>
 );
 })}
 </div>
 );
}
