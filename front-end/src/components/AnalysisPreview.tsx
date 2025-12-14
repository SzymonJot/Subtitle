import { useState } from 'react';
import { ChevronDown, ChevronUp, Copy, Check } from 'lucide-react';
import { cn } from '@/lib/utils';

// Define loose types for analysis data since we don't have the full schema yet
interface AnalysisData {
    words?: unknown[];
    phrases?: unknown[];
    sentences?: unknown[];
    [key: string]: any;
}

interface AnalysisPreviewProps {
    data: AnalysisData | null;
}

export default function AnalysisPreview({ data }: AnalysisPreviewProps) {
    const [expanded, setExpanded] = useState(false);
    const [copied, setCopied] = useState(false);

    if (!data) return null;

    const jsonString = JSON.stringify(data, null, 2);
    const previewLines = jsonString.split('\n').slice(0, 10).join('\n');
    const hasMore = jsonString.split('\n').length > 10;

    const handleCopy = async () => {
        await navigator.clipboard.writeText(jsonString);
        setCopied(true);
        setTimeout(() => setCopied(false), 2000);
    };

    // Extract some stats if available
    const stats = [];
    if (data?.words?.length) stats.push({ label: 'Words', value: data.words.length });
    if (data?.phrases?.length) stats.push({ label: 'Phrases', value: data.phrases.length });
    if (data?.sentences?.length) stats.push({ label: 'Sentences', value: data.sentences.length });

    return (
        <div className="rounded-xl border border-zinc-800 bg-zinc-950/50 overflow-hidden">
            {stats.length > 0 && (
                <div className="px-4 py-3 border-b border-zinc-800/50 flex items-center gap-6">
                    {stats.map((stat, i) => (
                        <div key={i} className="flex items-center gap-2">
                            <span className="text-xs text-zinc-500">{stat.label}</span>
                            <span className="text-sm font-semibold text-violet-400">{String(stat.value)}</span>
                        </div>
                    ))}
                </div>
            )}

            <div className="relative">
                <div className="absolute top-2 right-2 z-10">
                    <button
                        onClick={handleCopy}
                        className="p-2 rounded-lg bg-zinc-800/80 hover:bg-zinc-700 transition-colors"
                    >
                        {copied ? (
                            <Check className="w-4 h-4 text-emerald-500" />
                        ) : (
                            <Copy className="w-4 h-4 text-zinc-400" />
                        )}
                    </button>
                </div>

                <pre className={cn(
                    "p-4 text-xs text-zinc-400 overflow-x-auto font-mono",
                    !expanded && hasMore && "max-h-64"
                )}>
                    <code>
                        {expanded ? jsonString : previewLines}
                        {!expanded && hasMore && '\n...'}
                    </code>
                </pre>

                {hasMore && (
                    <div className="px-4 py-2 border-t border-zinc-800/50">
                        <button
                            onClick={() => setExpanded(!expanded)}
                            className="flex items-center gap-1.5 text-xs text-zinc-500 hover:text-zinc-300 transition-colors"
                        >
                            {expanded ? (
                                <>
                                    <ChevronUp className="w-3 h-3" />
                                    Show less
                                </>
                            ) : (
                                <>
                                    <ChevronDown className="w-3 h-3" />
                                    Show all ({jsonString.split('\n').length} lines)
                                </>
                            )}
                        </button>
                    </div>
                )}
            </div>
        </div>
    );
}