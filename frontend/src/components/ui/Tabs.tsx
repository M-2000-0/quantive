import type { ReactNode } from 'react';

interface Tab {
  id: string;
  label: string;
  disabled?: boolean;
}

interface TabsProps {
  tabs: Tab[];
  activeTab: string;
  onChange: (id: string) => void;
  children: ReactNode;
}

export default function Tabs({ tabs, activeTab, onChange, children }: TabsProps) {
  return (
    <div>
      <nav className="flex gap-1.5 p-1.5 glass-subtle rounded-2xl w-fit max-w-full overflow-x-auto" role="tablist">
        {tabs.map((tab) => {
          const isActive = tab.id === activeTab;
          return (
            <button
              key={tab.id}
              role="tab"
              aria-selected={isActive}
              disabled={tab.disabled}
              onClick={() => onChange(tab.id)}
              className={`
                px-4 py-2 text-[13px] font-semibold rounded-xl whitespace-nowrap
                transition-all duration-200
                focus:outline-none focus:ring-2 focus:ring-blue-500/20
                disabled:opacity-40 disabled:cursor-not-allowed
                ${isActive
                  ? 'bg-white/85 text-slate-900 shadow-sm border border-white/70 backdrop-blur-xl'
                  : 'text-slate-600 hover:text-slate-900 hover:bg-white/45 border border-transparent hover:border-white/40'
                }
              `}
            >
              {tab.label}
            </button>
          );
        })}
      </nav>
      <div className="py-5">{children}</div>
    </div>
  );
}
