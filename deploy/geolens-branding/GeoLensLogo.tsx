import { cn } from '@/lib/utils';

interface GeoLensLogoProps {
  variant?: 'full' | 'icon';
  size?: 'sm' | 'md' | 'lg';
  className?: string;
}

const sizes = {
  sm: { icon: 'h-5 w-5', wordmark: 'w-24', text: 'text-[10px]' },
  md: { icon: 'h-6 w-6', wordmark: 'w-32', text: 'text-xs' },
  lg: { icon: 'h-8 w-8', wordmark: 'w-52', text: 'text-sm' },
};

export function GeoLensLogo({ variant = 'full', size = 'md', className }: GeoLensLogoProps) {
  const s = sizes[size];
  if (variant === 'icon') {
    return <img src="/nexorus-icon.png" alt="Nexorus Atlas Catalog" className={cn(s.icon, 'object-contain', className)} />;
  }
  return (
    <span role="img" aria-label="Nexorus Atlas Catalog" className={cn('inline-flex flex-col items-start gap-1', className)}>
      <img src="/nexorus-wordmark.png" alt="Nexorus" className={cn(s.wordmark, 'h-auto')} />
      <span className={cn(s.text, 'font-medium tracking-wide text-slate-200')}>Atlas Catalog</span>
    </span>
  );
}
