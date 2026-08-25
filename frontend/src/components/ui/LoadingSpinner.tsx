interface LoadingSpinnerProps {
  message?: string;
  fullPage?: boolean;
}

export default function LoadingSpinner({ message = 'Loading…', fullPage = true }: LoadingSpinnerProps) {
  const spinner = (
    <div className="flex flex-col items-center gap-3">
      <div className="relative">
        <div className="absolute inset-0 rounded-full bg-blue-500/15 blur-xl" />
        <svg className="relative animate-spin h-8 w-8 text-blue-600" viewBox="0 0 24 24" fill="none">
          <circle className="opacity-20" cx="12" cy="12" r="10" stroke="currentColor" strokeWidth="4" />
          <path
            className="opacity-90"
            fill="currentColor"
            d="M4 12a8 8 0 018-8V0C5.373 0 0 5.373 0 12h4z"
          />
        </svg>
      </div>
      {message && (
        <p className="text-[13px] font-medium tracking-wide text-slate-500">{message}</p>
      )}
    </div>
  );

  if (fullPage) {
    return (
      <div className="flex items-center justify-center min-h-[400px]">
        <div className="glass-card px-10 py-8 flex items-center justify-center">
          {spinner}
        </div>
      </div>
    );
  }

  return spinner;
}
