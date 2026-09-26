'use client';

import { forwardRef } from 'react';
import { cn } from '@/lib/utils';

interface LabButtonProps extends React.ButtonHTMLAttributes<HTMLButtonElement> {
  variant?: 'primary' | 'secondary' | 'ghost';
  size?: 'sm' | 'md' | 'lg';
}

export const LabButton = forwardRef<HTMLButtonElement, LabButtonProps>(
  ({ className, variant = 'primary', size = 'md', children, ...props }, ref) => {
    const base =
      'group relative inline-flex items-center justify-center font-medium tracking-wide transition-all duration-300 overflow-hidden select-none';

    const variants = {
      primary:
        'bg-yellow-500 text-black hover:bg-yellow-400 border border-yellow-500',
      secondary:
        'bg-transparent text-foreground border border-border hover:border-yellow-500/50 hover:text-yellow-500',
      ghost:
        'bg-transparent text-muted-foreground hover:text-yellow-500 border border-transparent',
    };

    const sizes = {
      sm: 'px-4 py-2 text-xs rounded-md',
      md: 'px-6 py-3 text-sm rounded-lg',
      lg: 'px-8 py-4 text-base rounded-lg',
    };

    return (
      <button
        ref={ref}
        className={cn(base, variants[variant], sizes[size], className)}
        {...props}
      >
        {variant === 'primary' && (
          <span className="absolute inset-0 bg-yellow-300 translate-y-full group-hover:translate-y-0 transition-transform duration-300 ease-out" />
        )}
        <span className="relative flex items-center gap-2 z-10">{children}</span>
      </button>
    );
  }
);
LabButton.displayName = 'LabButton';
