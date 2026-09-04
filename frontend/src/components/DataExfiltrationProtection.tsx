import React, { useState } from 'react';
import { Shield, TriangleAlert as AlertTriangle } from 'lucide-react';

interface DLPEvent {
 id: string;
 user: string;
 action: string;
 type: 'export' | 'screenshot' | 'usb' | 'download' | 'print';
 records: number;
 timestamp: string;
 status: 'approved' | 'blocked' | 'pending' | 'flagged';
 reason?: string;
}

const EVENTS: DLPEvent[] = [
 { id: 'dlp-001', user: 'James Morrison', action: 'Export to USB', type: 'usb', records: 847, timestamp: '2026-08-24T11:15:00Z', status: 'flagged', reason: 'Mass export exceeds daily limit (100 records)' },
 { id: 'dlp-002', user: 'Sarah Chen', action: 'CSV Export', type: 'export', records: 45, timestamp: '2026-08-24T09:30:00Z', status: 'approved' },
 { id: 'dlp-003', user: 'Unknown', action: 'Screenshot detected', type: 'screenshot', records: 1, timestamp: '2026-08-24T10:00:00Z', status: 'blocked', reason: 'Screenshots disabled for classified data' },
 { id: 'dlp-004', user: 'Michael Torres', action: 'PDF Download', type: 'download', records: 12, timestamp: '2026-08-24T08:45:00Z', status: 'approved' },
 { id: 'dlp-005', user: 'Lisa Wang', action: 'Print request', type: 'print', records: 5, timestamp: '2026-08-24T14:00:00Z', status: 'pending', reason: 'Awaiting manager approval for printed copies' },
];

const TYPE_ICONS: Record<string, string> = {
 export: 'Upload',
 screenshot: '📸',
 usb: '🔌',
 download: '⬇️',
 print: '🖨️' };

const STATUS_COLORS: Record<string, string> = {
 approved: 'bg-green-500/20 text-green-400',
 blocked: 'bg-red-500/20 text-red-400',
 pending: 'bg-yellow-500/20 text-yellow-400',
 flagged: 'bg-orange-500/20 text-orange-400' };

export default function DataExfiltrationProtection() {
 const [events] = useState(EVENTS);
 const [selectedEvent, setSelectedEvent] = useState<DLPEvent | null>(null);

 return (
 <div className="space-y-6 animate-glass-in">
 <div className="flex items-center gap-3">
 <div className="w-10 h-10 bg-gradient-to-br from-slate-500 to-gray-600 rounded-xl flex items-center justify-center">
 <Shield className="w-5 h-5" />
 </div>
 <div>
 <h2 className="text-xl font-bold text-white">Data Exfiltration Protection</h2>
 <p className="text-sm text-slate-400">Watermarking, export approval, download limits, and DLP controls</p>
 </div>
 </div>

 {/* DLP Controls */}
 <div className="grid grid-cols-4 gap-4">
 {[
 { label: 'Exports Today', value: '142', limit: '500/day', status: 'normal' },
 { label: 'USB Transfers', value: '2', limit: '5/day', status: 'normal' },
 { label: 'Screenshots', value: '0', limit: 'BLOCKED', status: 'blocked' },
 { label: 'Print Requests', value: '1', limit: '10/day', status: 'normal' },
 ].map((ctrl, i) => (
 <div key={i} className="glass rounded-xl p-4 text-center">
 <p className="text-xs text-slate-500 mb-1">{ctrl.label}</p>
 <p className="text-2xl font-bold text-white">{ctrl.value}</p>
 <p className="text-xs text-slate-400">Limit: {ctrl.limit}</p>
 </div>
 ))}
 </div>

 {/* Watermarking Info */}
 <div className="glass rounded-2xl p-5">
 <h3 className="text-sm font-medium text-slate-400 mb-3">ACTIVE WATERMARKING</h3>
 <div className="grid grid-cols-3 gap-4 text-sm">
 <div className="bg-white/5 rounded-xl p-3">
 <p className="text-slate-500 text-xs mb-1">Export Watermark</p>
 <p className="text-white">User + Timestamp + Device ID</p>
 </div>
 <div className="bg-white/5 rounded-xl p-3">
 <p className="text-slate-500 text-xs mb-1">PDF Watermark</p>
 <p className="text-white">Invisible + Visible header</p>
 </div>
 <div className="bg-white/5 rounded-xl p-3">
 <p className="text-slate-500 text-xs mb-1">Screenshot Prevention</p>
 <p className="text-red-400">Active for classified data</p>
 </div>
 </div>
 </div>

 {/* Events */}
 <div className="glass rounded-2xl p-6">
 <h3 className="text-sm font-medium text-slate-400 mb-4">RECENT DLP EVENTS</h3>
 <div className="space-y-2">
 {events.map(event => (
 <button
 key={event.id}
 onClick={() => setSelectedEvent(event)}
 className={`w-full text-left flex items-center gap-4 p-3 rounded-xl transition-all ${
 selectedEvent?.id === event.id ? 'bg-white/10' : 'hover:bg-white/5'
 }`}
 >
 <span className="text-lg">{TYPE_ICONS[event.type]}</span>
 <div className="flex-1">
 <p className="text-sm text-white">{event.action}</p>
 <p className="text-xs text-slate-400">{event.user} • {event.records} records • {event.timestamp.split('T')[1].slice(0, 5)}</p>
 </div>
 <span className={`px-2 py-0.5 rounded text-xs font-medium ${STATUS_COLORS[event.status]}`}>
 {event.status}
 </span>
 </button>
 ))}
 </div>
 </div>

 {/* Detail */}
 {selectedEvent && (
 <div className="glass rounded-2xl p-6 space-y-4">
 <div className="flex items-center justify-between">
 <h3 className="text-lg font-bold text-white">{selectedEvent.action}</h3>
 <span className={`px-3 py-1 rounded-lg text-xs font-medium ${STATUS_COLORS[selectedEvent.status]}`}>
 {selectedEvent.status.toUpperCase()}
 </span>
 </div>
 <div className="grid grid-cols-3 gap-4">
 <div className="bg-white/5 rounded-xl p-3 text-center">
 <p className="text-xs text-slate-500">User</p>
 <p className="text-white font-medium">{selectedEvent.user}</p>
 </div>
 <div className="bg-white/5 rounded-xl p-3 text-center">
 <p className="text-xs text-slate-500">Records</p>
 <p className="text-white font-medium">{selectedEvent.records}</p>
 </div>
 <div className="bg-white/5 rounded-xl p-3 text-center">
 <p className="text-xs text-slate-500">Time</p>
 <p className="text-white font-medium">{selectedEvent.timestamp.split('T')[1].slice(0, 8)}</p>
 </div>
 </div>
 {selectedEvent.reason && (
 <div className="p-4 bg-amber-500/10 border border-amber-500/20 rounded-xl">
 <p className="text-sm text-amber-300"> <AlertTriangle className="w-4 h-4 inline" /> {selectedEvent.reason}</p>
 </div>
 )}
 </div>
 )}
 </div>
 );
}
