// ── Quantive Icon System ─────────────────────────────────────────────
// Replaces all emojis with Lucide icons. Government software should
// look like Bloomberg, not a crypto dashboard.

import {
 LayoutDashboard, Layers, Briefcase, Settings, List,
 TrendingUp, Shield, TriangleAlert as AlertTriangle, Globe, ChartColumn as BarChart3,
 Activity, Brain, Lightbulb, Cpu, Network, GitBranch,
 Clock, FileText, Star, Search, Zap, Bell,
 Leaf, Award, BookOpen, Database, Eye, Lock,
 Users, UserCheck, FileCheck, ClipboardList, Target,
 CircleCheck as CheckCircle, CircleX as XCircle, ArrowUpRight, ArrowDownRight,
 Minus, ChevronRight, AlertCircle, Info, ShieldAlert,
 User, CreditCard, Landmark, Scale, Handshake,
 Timer, RefreshCw, Download, Upload, Filter,
 Server, Wifi, WifiOff, CloudOff, Monitor,
 PieChart, LineChart, AreaChart, TrendingDown,
 DollarSign, Percent, Hash, Calendar, CalendarClock,
 MapPin, Flag, Crosshair, Radar, Scan,
 BookMarked, Archive, BookmarkPlus, History,
 ShieldCheck, ShieldX, ShieldAlert as ShieldAlertIcon,
 Key, Fingerprint, ScanLine,
 Building2, Building, School,
 Gavel, ScrollText, FileSignature,
 MessageSquare, Send, Reply,
 FolderOpen, Folder, Paperclip,
  Play, Pause, SkipForward, RotateCcw,
  CircleDot, Circle, Dot,
  Keyboard, Sun, Moon, PencilLine as EditIcon, Square, Hexagon,
  type LucideIcon,
} from 'lucide-react';

// ── Category Icons ───────────────────────────────────────────────────

export const CategoryIcons = {
 // Core
 dashboard: LayoutDashboard,
 portfolio: Briefcase,
 optimization: Settings,
 execution: ClipboardList,
 adaptive: Layers,

 // Market
 market: TrendingUp,
 risk: Shield,
 alert: AlertTriangle,
 globe: Globe,
 chart: BarChart3,
 activity: Activity,
 event: Zap,

 // Analytics
 ai: Brain,
 insight: Lightbulb,
 cpu: Cpu,
 network: Network,
 compare: GitBranch,
 peer: Users,

 // Operations
 clock: Clock,
 document: FileText,
 star: Star,
 search: Search,
 notification: Bell,

 // ESG
 esg: Leaf,
 rating: Award,
 report: BookOpen,
 data: Database,

 // Security
 visibility: Eye,
 lock: Lock,
 shield: Shield,
 audit: FileCheck,
 compliance: Scale,
 approval: FileSignature,

  // Government
  institution: Landmark,
  building: Building2,
  policy: ScrollText,
  minister: User,
  handshake: Handshake,
  gavel: Gavel,
  scale: Scale,

 // System
 server: Server,
 wifi: Wifi,
 wifiOff: WifiOff,
 cloudOff: CloudOff,
 monitor: Monitor,
 refresh: RefreshCw,
 download: Download,
 upload: Upload,
 filter: Filter,

 // Status
 check: CheckCircle,
 x: XCircle,
 info: Info,
 warning: AlertCircle,
 arrowUp: ArrowUpRight,
 arrowDown: ArrowDownRight,
 neutral: Minus,

 // Charts
 pie: PieChart,
 line: LineChart,
 area: AreaChart,
 trendingDown: TrendingDown,
 trendingUp: TrendingUp,

 // Financial
 dollar: DollarSign,
 percent: Percent,
 hash: Hash,
 calendar: Calendar,
 calendarClock: CalendarClock,

 // Map / Geo
 pin: MapPin,
 flag: Flag,
 crosshair: Crosshair,
 radar: Radar,
 scan: Scan,

 // Memory
 bookmark: BookMarked,
 archive: Archive,
 bookmarkPlus: BookmarkPlus,
 history: History,

 // Auth
 key: Key,
 fingerprint: Fingerprint,

 // Collaboration
 message: MessageSquare,
 send: Send,
 reply: Reply,

 // File
 folder: FolderOpen,
 folderClosed: Folder,
 paperclip: Paperclip,

 // Playback
 play: Play,
 pause: Pause,
 skip: SkipForward,
 rotate: RotateCcw,

  // State
  dot: CircleDot,
  circle: Circle,
  dotFilled: Dot,

  // Editor / theme / shapes
  zap: Zap,
  edit: EditIcon,
  keyboard: Keyboard,
  sun: Sun,
  moon: Moon,
  square: Square,
  hexagon: Hexagon,
} as const;

export type IconName = keyof typeof CategoryIcons;

// ── Helper ───────────────────────────────────────────────────────────

export function getIcon(name: IconName, className = 'h-4 w-4'): React.ReactNode {
 const Icon = CategoryIcons[name];
 return <Icon className={className} />;
}

// ── Emoji → Icon Mapping ─────────────────────────────────────────────
// Maps the 181 emoji instances to their Lucide equivalents.

export const EMOJI_MAP: Record<string, IconName> = {
 'TrendingUp': 'trendingUp',
 'DollarSign': 'dollar',
 'Flame': 'alert',
 'Rocket': 'arrowUp',
 'Zap': 'zap',
 'Globe': 'globe',
 'BarChart3': 'chart',
 'Users': 'peer',
 'Shield': 'shield',
 'Lightbulb': 'insight',
 'Settings': 'cpu',
 'FileText': 'document',
 'CheckCircle': 'check',
 'XCircle': 'x',
 'AlertTriangle': 'warning',
 'Lock': 'lock',
 'Unlock': 'key',
 'Paperclip': 'paperclip',
 'MessageSquare': 'message',
 'Target': 'crosshair',
 'Tag': 'bookmark',
 '🎮': 'play',
 'Scale': 'scale',
 'Building2': 'institution',
 '⌨️': 'keyboard',
 '☀️': 'sun',
 '🌙': 'moon',
 '💻': 'monitor',
 '🕵️': 'search',
 '⏱️': 'clock',
 '📅': 'calendar',
 '📆': 'calendarClock',
 '✏️': 'edit',
  '👁️': 'visibility',
  '🎖️': 'award',
 '⚔️': 'gavel',
 '➡️': 'neutral',
 '↗️': 'arrowUp',
 '↘️': 'arrowDown',
 'RefreshCw': 'refresh',
 ' <Play className="w-4 h-4 inline" /> ': 'play',
 '↩️': 'rotate',
 'Info': 'info',
 '✓': 'check',
 '⚠': 'warning',
 '✗': 'x',
 'Square': 'square',
 'Hexagon': 'hexagon',
 'LayoutGrid': 'square',
 '■': 'square',
};

// Quick lookup: get icon name from emoji, returns 'info' as fallback
export function emojiToIcon(emoji: string): IconName {
 return EMOJI_MAP[emoji] || 'info';
}
