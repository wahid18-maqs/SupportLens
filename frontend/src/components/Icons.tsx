interface IconProps {
  size?: number;
  className?: string;
}

export function LogoIcon({ size = 28, className }: IconProps) {
  return (
    <svg width={size} height={size} viewBox="0 0 28 28" fill="none" className={className} aria-hidden="true">
      <rect width="28" height="28" rx="8" fill="url(#logo-gradient)" />
      <path
        d="M8 13.5c0-3 2.5-5.5 6-5.5s6 2.5 6 5.5-2.5 5.5-6 5.5c-.8 0-1.6-.15-2.3-.45L9 19.5l.7-2.9C8.6 15.7 8 14.65 8 13.5Z"
        stroke="white"
        strokeWidth="1.4"
        strokeLinejoin="round"
      />
      <path d="M11.3 13.5l1.7 1.7 3-3.2" stroke="white" strokeWidth="1.4" strokeLinecap="round" strokeLinejoin="round" />
      <defs>
        <linearGradient id="logo-gradient" x1="0" y1="0" x2="28" y2="28" gradientUnits="userSpaceOnUse">
          <stop stopColor="#7c6cf6" />
          <stop offset="1" stopColor="#4f7dfb" />
        </linearGradient>
      </defs>
    </svg>
  );
}


export function SendIcon({ size = 18, className }: IconProps) {
  return (
    <svg width={size} height={size} viewBox="0 0 20 20" fill="none" className={className} aria-hidden="true">
      <path
        d="M17.5 2.5 2.5 8.75l5.5 2.25 2.25 5.5L17.5 2.5Z"
        stroke="currentColor"
        strokeWidth="1.5"
        strokeLinecap="round"
        strokeLinejoin="round"
      />
      <path d="M17.5 2.5 8.5 11.5" stroke="currentColor" strokeWidth="1.5" strokeLinecap="round" />
    </svg>
  );
}


export function CopyIcon({ size = 14, className }: IconProps) {
  return (
    <svg width={size} height={size} viewBox="0 0 16 16" fill="none" className={className} aria-hidden="true">
      <rect x="5.5" y="5.5" width="8" height="8" rx="1.5" stroke="currentColor" strokeWidth="1.3" />
      <path d="M3.5 10V3.5a1 1 0 0 1 1-1H10" stroke="currentColor" strokeWidth="1.3" strokeLinecap="round" />
    </svg>
  );
}


export function CheckCircleIcon({ size = 16, className }: IconProps) {
  return (
    <svg width={size} height={size} viewBox="0 0 16 16" fill="none" className={className} aria-hidden="true">
      <circle cx="8" cy="8" r="7" fill="currentColor" fillOpacity="0.15" />
      <path d="M5 8.2 7.1 10.3 11 6" stroke="currentColor" strokeWidth="1.5" strokeLinecap="round" strokeLinejoin="round" />
    </svg>
  );
}

export function WarningIcon({ size = 16, className }: IconProps) {
  return (
    <svg width={size} height={size} viewBox="0 0 16 16" fill="none" className={className} aria-hidden="true">
      <path
        d="M8 2.2 14.5 13.5h-13L8 2.2Z"
        fill="currentColor"
        fillOpacity="0.15"
        stroke="currentColor"
        strokeWidth="1.3"
        strokeLinejoin="round"
      />
      <path d="M8 6.5v3" stroke="currentColor" strokeWidth="1.4" strokeLinecap="round" />
      <circle cx="8" cy="11.3" r="0.9" fill="currentColor" />
    </svg>
  );
}


export function ChevronIcon({ size = 16, className }: IconProps) {
  return (
    <svg width={size} height={size} viewBox="0 0 16 16" fill="none" className={className} aria-hidden="true">
      <path d="M4 6.5 8 10l4-3.5" stroke="currentColor" strokeWidth="1.5" strokeLinecap="round" strokeLinejoin="round" />
    </svg>
  );
}
