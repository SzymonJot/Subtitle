import React from 'react';
import { Loader2 } from 'lucide-react';
import { cn } from '@/lib/utils';

export default function ActionButton({
    children,
    onClick,
    disabled = false,
    loading = false,
    variant = 'primary', // primary | secondary | ghost
    size = 'md', // sm | md | lg
    icon: Icon,
    className,
    ...props
}) {
    const variants = {
        primary: "bg-violet-600 hover:bg-violet-500 text-white shadow-lg shadow-violet-500/20",
        secondary: "bg-zinc-800 hover:bg-zinc-700 text-zinc-100 border border-zinc-700",
        ghost: "bg-transparent hover:bg-zinc-800/50 text-zinc-400 hover:text-zinc-200"
    };

    const sizes = {
        sm: "px-3 py-1.5 text-sm gap-1.5",
        md: "px-4 py-2.5 text-sm gap-2",
        lg: "px-6 py-3 text-base gap-2.5"
    };

    return (
        <button
            onClick={onClick}
            disabled={disabled || loading}
            className={cn(
                "inline-flex items-center justify-center font-medium rounded-xl transition-all duration-200",
                "disabled:opacity-50 disabled:cursor-not-allowed disabled:shadow-none",
                "focus:outline-none focus:ring-2 focus:ring-violet-500/50 focus:ring-offset-2 focus:ring-offset-zinc-900",
                variants[variant],
                sizes[size],
                className
            )}
            {...props}
        >
            {loading ? (
                <Loader2 className="w-4 h-4 animate-spin" />
            ) : Icon ? (
                <Icon className="w-4 h-4" />
            ) : null}
            {children}
        </button>
    );
}