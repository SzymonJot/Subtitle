import React from 'react';
import { Check, Circle, Loader2 } from 'lucide-react';
import { cn } from '@/lib/utils';

export default function StepCard({ 
  stepNumber, 
  title, 
  description,
  status = 'pending', // pending | active | completed | loading
  disabled = false,
  children 
}) {
  const statusIcon = {
    pending: <Circle className="w-5 h-5 text-zinc-600" />,
    active: <Circle className="w-5 h-5 text-violet-500 fill-violet-500/20" />,
    loading: <Loader2 className="w-5 h-5 text-violet-500 animate-spin" />,
    completed: <Check className="w-5 h-5 text-emerald-500" />
  };

  return (
    <div 
      className={cn(
        "relative rounded-2xl border transition-all duration-300",
        disabled ? "opacity-40 pointer-events-none" : "",
        status === 'active' || status === 'loading' 
          ? "border-violet-500/30 bg-zinc-900/80" 
          : status === 'completed'
            ? "border-emerald-500/20 bg-zinc-900/50"
            : "border-zinc-800/50 bg-zinc-900/30"
      )}
    >
      <div className="p-6">
        <div className="flex items-start gap-4 mb-4">
          <div className={cn(
            "flex items-center justify-center w-10 h-10 rounded-xl border transition-colors",
            status === 'completed' 
              ? "border-emerald-500/30 bg-emerald-500/10" 
              : status === 'active' || status === 'loading'
                ? "border-violet-500/30 bg-violet-500/10"
                : "border-zinc-700 bg-zinc-800/50"
          )}>
            {statusIcon[status]}
          </div>
          <div className="flex-1 min-w-0">
            <div className="flex items-center gap-3">
              <span className="text-xs font-medium text-zinc-500 uppercase tracking-wider">
                Step {stepNumber}
              </span>
            </div>
            <h3 className="text-lg font-semibold text-zinc-100 mt-1">
              {title}
            </h3>
            {description && (
              <p className="text-sm text-zinc-500 mt-1">
                {description}
              </p>
            )}
          </div>
        </div>
        
        <div className="pl-14">
          {children}
        </div>
      </div>
    </div>
  );
}