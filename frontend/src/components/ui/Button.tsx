import type { ReactNode, ButtonHTMLAttributes } from 'react';

type ButtonVariant = 'primary' | 'secondary' | 'danger' | 'ghost';
type ButtonSize = 'sm' | 'md' | 'lg';

const variantStyles: Record<ButtonVariant, string> = {
  primary: 'glass-button-primary text-white hover:text-white',
  secondary: 'glass-button-secondary text-slate-700 hover:text-slate-900',
  danger: 'bg-gradient-to-br from-red-600 to-red-700 text-white border border-white/15 shadow-[0_4px_16px_rgba(220,38,38,0.28),inset_0_1px_0_rgba(255,255,255,0.2)] hover:from-red-700 hover:to-red-800',
  ghost: 'text-slate-600 hover:bg-white/60 hover:text-slate-900 border border-transparent hover:border-white/50 hover:shadow-sm backdrop-blur-md',
};

const sizeStyles: Record<ButtonSize, string> = {
  sm: 'px-3 py-1.5 text-xs gap-1.5 rounded-xl',
  md: 'px-4 py-2 text-sm gap-2 rounded-xl',
  lg: 'px-5 py-2.5 text-[15px] gap-2 rounded-2xl',
};

interface ButtonProps extends ButtonHTMLAttributes<HTMLButtonElement> {
  children: ReactNode;
  variant?: ButtonVariant;
  size?: ButtonSize;
  loading?: boolean;
  leftIcon?: ReactNode;
  rightIcon?: ReactNode;
  fullWidth?: boolean;
}

function Spinner() {
  return (
    <svg className="animate-spin h-4 w-4" viewBox="0 0 24 24" fill="none">
      <circle className="opacity-25" cx="12" cy="12" r="10" stroke="currentColor" strokeWidth="4" />
      <path
        className="opacity-75"
        fill="currentColor"
        d="M4 12a8 8 0 018-8V0C5.373 0 0 5.373 0 12h4z"
      />
    </svg>
  );
}

export default function Button({
  children,
  variant = 'primary',
  size = 'md',
  loading = false,
  leftIcon,
  rightIcon,
  fullWidth = false,
  disabled,
  className = '',
  ...props
}: ButtonProps) {
  const isDisabled = disabled || loading;

  return (
    <button
      className={`
        inline-flex items-center justify-center font-semibold
        transition-all duration-200 ease-[cubic-bezier(0.2,0.8,0.2,1)]
        focus:outline-none focus:ring-2 focus:ring-blue-500/30 focus:ring-offset-0
        disabled:opacity-50 disabled:cursor-not-allowed
        active:scale-[0.99]
        ${variantStyles[variant]}
        ${sizeStyles[size]}
        ${fullWidth ? 'w-full' : ''}
        ${className}
      `}
      disabled={isDisabled}
      {...props}
    >
      {loading ? <Spinner /> : leftIcon}
      {children}
      {!loading && rightIcon}
    </button>
  );
}
