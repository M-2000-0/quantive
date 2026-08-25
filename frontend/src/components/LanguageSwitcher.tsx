import { useI18n, type Locale } from '../i18n';

const LABELS: Record<Locale, string> = {
  en: 'EN',
  es: 'ES',
  fr: 'FR',
  pt: 'PT',
};

const FULL_NAMES: Record<Locale, string> = {
  en: 'English',
  es: 'Espanol',
  fr: 'Francais',
  pt: 'Portugues',
};

export default function LanguageSwitcher() {
  const { locale, setLocale, availableLocales } = useI18n();

  return (
    <div className="relative group">
      <button className="flex items-center gap-1 px-2 py-1 text-xs font-medium text-slate-400 hover:text-white rounded transition-colors">
        <svg className="h-3.5 w-3.5" fill="none" viewBox="0 0 24 24" strokeWidth={1.5} stroke="currentColor">
          <path strokeLinecap="round" strokeLinejoin="round" d="M12 21a9.004 9.004 0 008.716-6.747M12 21a9.004 9.004 0 01-8.716-6.747M12 21c2.485 0 4.5-4.03 4.5-9S14.485 3 12 3m0 18c-2.485 0-4.5-4.03-4.5-9S9.515 3 12 3m0 0a8.997 8.997 0 017.843 4.582M12 3a8.997 8.997 0 00-7.843 4.582m15.686 0A11.953 11.953 0 0112 10.5c-2.998 0-5.74-1.1-7.843-2.918m15.686 0A8.959 8.959 0 0121 12c0 .778-.099 1.533-.284 2.253m0 0A17.919 17.919 0 0112 16.5c-3.162 0-6.133-.815-8.716-2.247m0 0A9.015 9.015 0 013 12c0-1.605.42-3.113 1.157-4.418" />
        </svg>
        {LABELS[locale]}
      </button>

      <div className="absolute bottom-full left-0 mb-1 hidden group-hover:block z-50">
        <div className="bg-white rounded-lg shadow-lg border py-1 min-w-[120px]">
          {availableLocales.map(l => (
            <button
              key={l}
              onClick={() => setLocale(l)}
              className={`w-full text-left px-3 py-1.5 text-sm transition-colors ${
                l === locale
                  ? 'bg-blue-50 text-blue-700 font-medium'
                  : 'text-gray-700 hover:bg-gray-50'
              }`}
            >
              {FULL_NAMES[l]}
            </button>
          ))}
        </div>
      </div>
    </div>
  );
}
