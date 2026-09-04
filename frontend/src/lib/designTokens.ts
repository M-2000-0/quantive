// ── Quantive Design Rulebook — Premium Minimal ────────────────────────
// Dark, clean, subtle depth. Linear/Stripe-level polish.

// ── Surfaces (4 levels) ──────────────────────────────────────────────

export const SURFACES = {
  0: 'Background — #08090c, no glass, flat',
  1: 'Subtle — cards, panels. 4% white opacity.',
  2: 'Interactive — controls, inputs. 6.5% white opacity.',
  3: 'Elevated — modals, dropdowns. 9.5% white opacity + blur.',
} as const;

// ── Spacing (8 values) ───────────────────────────────────────────────

export const SPACING = {
  1: '4px',
  2: '8px',
  3: '12px',
  4: '16px',
  5: '20px',
  6: '24px',
  8: '32px',
  10: '40px',
} as const;

// ── Icon Sizes (3) ───────────────────────────────────────────────────

export const ICON_SIZES = {
  sm: 'h-3.5 w-3.5',
  md: 'h-4 w-4',
  lg: 'h-5 w-5',
} as const;

// ── Colors ───────────────────────────────────────────────────────────

export const COLORS = {
  accent: {
    primary: '#c8a951',    // Amber gold — brand, emphasis, active states
    secondary: '#08090c',  // Near-black — backgrounds
  },
  semantic: {
    success: '#34d399',
    warning: '#fbbf24',
    danger: '#f87171',
    info: '#60a5fa',
  },
  surface: {
    0: '#08090c',
    1: 'rgba(255,255,255,0.04)',
    2: 'rgba(255,255,255,0.065)',
    3: 'rgba(255,255,255,0.095)',
  },
  text: {
    primary: '#ececef',
    secondary: '#8b8b96',
    tertiary: '#55555e',
  },
} as const;

// ── Animation Patterns (5) ───────────────────────────────────────────

export const ANIMATIONS = {
  enter: '180ms cubic-bezier(0.16, 1, 0.3, 1)',
  exit: '120ms ease',
  hover: '100ms cubic-bezier(0.16, 1, 0.3, 1)',
  drag: 'physics-based (spring)',
  transition: '200ms cubic-bezier(0.16, 1, 0.3, 1)',
} as const;

// ── Typography ───────────────────────────────────────────────────────

export const TYPOGRAPHY = {
  weights: [500, 600, 700] as const,
  sizes: {
    label: '10px',
    body: '13px',
    heading: '15px',
    data: '13px',
    stat: '22px',
  },
} as const;

// ── Border Radius ────────────────────────────────────────────────────

export const RADIUS = {
  button: '8px',
  input: '8px',
  badge: '100px',
  panel: '12px',
  modal: '16px',
} as const;

// ── Elevation (3 levels, dark mode) ──────────────────────────────────

export const ELEVATION = {
  none: 'none',
  subtle: '0 1px 2px rgba(0,0,0,0.15)',
  medium: '0 4px 16px rgba(0,0,0,0.25)',
  high: '0 12px 40px rgba(0,0,0,0.4)',
} as const;

export const DARK_ELEVATION = {
  none: 'none',
  subtle: '0 1px 2px rgba(0,0,0,0.2)',
  medium: '0 4px 16px rgba(0,0,0,0.3)',
  high: '0 12px 40px rgba(0,0,0,0.5)',
} as const;

// ── Context Modes ────────────────────────────────────────────────────

export type ContextMode = 'analyst' | 'executive' | 'crisis';

export const MODE_CONFIG: Record<ContextMode, {
  label: string;
  description: string;
  density: 'compact' | 'comfortable' | 'spacious';
  showCharts: boolean;
  showTables: boolean;
  showMetadata: boolean;
  maxCardsVisible: number;
}> = {
  analyst: {
    label: 'Analyst Mode',
    description: 'Dense tables, full metadata, all models visible',
    density: 'compact',
    showCharts: true,
    showTables: true,
    showMetadata: true,
    maxCardsVisible: 99,
  },
  executive: {
    label: 'Executive Mode',
    description: 'Key decisions, risk summary, recommended actions only',
    density: 'comfortable',
    showCharts: true,
    showTables: false,
    showMetadata: false,
    maxCardsVisible: 3,
  },
  crisis: {
    label: 'Crisis Mode',
    description: 'High contrast, minimal glass, all critical data visible',
    density: 'compact',
    showCharts: true,
    showTables: true,
    showMetadata: true,
    maxCardsVisible: 99,
  },
};

// ── Microcopy ────────────────────────────────────────────────────────

export const COPY = {
  actions: {
    run: 'Evaluate Strategy',
    create: 'Create Portfolio',
    optimize: 'Compare Outcomes',
    approve: 'Review Recommendation',
    export: 'Generate Report',
    import: 'Import Data',
    save: 'Save Configuration',
    cancel: 'Discard Changes',
    delete: 'Remove',
    search: 'Search',
    filter: 'Filter',
    sort: 'Sort',
    refresh: 'Update Data',
    undo: 'Revert',
    redo: 'Reapply',
  },
  status: {
    loading: 'Processing...',
    success: 'Complete',
    error: 'Failed',
    warning: 'Needs Review',
    pending: 'Awaiting Approval',
    approved: 'Approved',
    rejected: 'Rejected',
    running: 'In Progress',
  },
  empty: {
    portfolio: 'Create your first debt portfolio to begin analysis',
    optimization: 'Run your first optimization to compare strategies',
    decisions: 'No decisions recorded yet. Run an optimization to begin.',
    simulation: 'Create a scenario to simulate market conditions',
    import: 'Drag and drop your spreadsheet here',
  },
  confidence: {
    high: 'High confidence',
    medium: 'Moderate confidence',
    low: 'Limited confidence',
  },
} as const;
