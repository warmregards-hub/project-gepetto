import { useEffect, useState } from 'react';
import { useAgentStore } from '../../stores/agentStore';
import { useProjectStore } from '../../stores/projectStore';
import { SkeletonMessage } from '../shared/LoadingStates';
import ReactMarkdown from 'react-markdown';
import { API_BASE_URL } from '../../lib/constants';
import { Check, X, BookmarkPlus } from 'lucide-react';

export function ConversationView() {
    const { messages, isProcessing } = useAgentStore();
    const { saveAsset, rejectAsset, savedAssets, rejectedAssets, activeProject } = useProjectStore();
    const [imageLayouts, setImageLayouts] = useState<Record<string, 'landscape' | 'portrait' | 'square'>>({});

    const normalizeImageSrc = (rawSrc: string) => {
        const trimmed = rawSrc.trim();
        const withBase = trimmed.startsWith('/api/') ? `${API_BASE_URL}${trimmed}` : trimmed;
        if (withBase.startsWith('data:image')) {
            return withBase.replace(/\s+/g, '');
        }
        return withBase;
    };

    // Handle Keyboard Shortcuts
    useEffect(() => {
        const handleKeyDown = (e: KeyboardEvent) => {
            if (!activeProject) return;

            // Find the last assistant message with images
            const lastAssistantMsg = [...messages].reverse().find(m => m.role === 'assistant' && m.content.includes('!['))
            if (!lastAssistantMsg) return;

            // Extract image URLs
            const imgMatches = lastAssistantMsg.content.match(/!\[.*?\]\((.*?)\)/g);
            if (!imgMatches) return;

            const urls = imgMatches
                .map(m => {
                    const match = m.match(/\((.*?)\)/);
                    const src = match ? match[1] : '';
                    return normalizeImageSrc(src);
                })
                .filter(url => typeof url === 'string' && url.trim().length > 0);

            if (urls.length === 0) return;

            // Focus first un-reviewed image (or last reviewed)
            const firstUnreviewedIdx = urls.findIndex(url => !savedAssets.includes(url) && !rejectedAssets.includes(url));
            const targetIdx = firstUnreviewedIdx !== -1 ? firstUnreviewedIdx : 0;
            const targetUrl = urls[targetIdx];

            if (e.key.toLowerCase() === 'k') {
                saveAsset(targetUrl, activeProject.id);
            } else if (e.key.toLowerCase() === 'r') {
                rejectAsset(targetUrl, activeProject.id);
            }
        };

        window.addEventListener('keydown', handleKeyDown);
        return () => window.removeEventListener('keydown', handleKeyDown);
    }, [messages, savedAssets, rejectedAssets, saveAsset, rejectAsset, activeProject]);

    if (messages.length === 0 && !isProcessing) {
        return (
            <div className="flex-1 flex items-center justify-center text-zinc-300 font-mono text-xl">
                <p>READY_FOR_BRIEF</p>
            </div>
        );
    }

    return (
        <div className="flex-1 overflow-y-auto p-6 md:p-12 space-y-8 md:space-y-10">
            {messages.map((msg: any) => (
                <div
                    key={msg.id}
                    className={`flex flex-col w-full max-w-6xl mx-auto rounded-[32px] md:rounded-[40px] p-8 md:p-12 ${msg.role === 'user'
                        ? 'bg-zinc-50 self-end ml-auto text-zinc-700 max-w-full md:max-w-3xl'
                        : 'bg-white border border-zinc-100 text-zinc-950 shadow-sm'
                        }`}
                >
                    <div className="flex items-center space-x-2 mb-6">
                        <span className="text-[14px] font-black uppercase tracking-widest text-zinc-500">
                            {msg.role === 'user' ? 'USER' : 'GEPETTO'}
                        </span>
                        <span className="text-[14px] text-zinc-400 font-bold">
                            {new Date(msg.timestamp).toLocaleTimeString([], { hour12: false })}
                        </span>
                    </div>

                    <div className="whitespace-pre-wrap flex-1">
                        <ReactMarkdown
                            components={{
                                p: ({ node, children, ...props }: any) => {
                                    // If this paragraph contains only images, render as a 2-column grid
                                    const allImages = node?.children?.every((c: any) => c.tagName === 'img' || (c.type === 'text' && !c.value.trim()));
                                    if (allImages) {
                                        return (
                                            <div className="grid grid-cols-1 sm:grid-cols-2 gap-4 mt-6 mb-8">
                                                {children}
                                            </div>
                                        );
                                    }

                                    // If it contains at least one image but mixed with text
                                    const hasImage = node?.children?.some((c: any) => c.tagName === 'img');
                                    if (hasImage) return <div className="mb-6">{children}</div>;

                                    return <p className="mb-6 last:mb-0 text-3xl font-bold leading-relaxed text-zinc-900" {...props}>{children}</p>;
                                },
                                a: ({ node, href, ...props }: any) => {
                                    const fullHref = href?.startsWith('/api/') ? `${API_BASE_URL}${href}` : href;
                                    return (
                                        <a href={fullHref} className="text-accent underline underline-offset-8 decoration-2 hover:text-accent-hover transition-all font-black break-all" target={fullHref?.includes('download') ? "_blank" : "_self"} rel="noreferrer" {...props} />
                                    );
                                },
                                img: ({ node, src, alt, ...props }: any) => {
                                    if (!src || !src.trim()) return null;
                                    const fullSrc = normalizeImageSrc(src);
                                    const isKept = savedAssets.includes(fullSrc);
                                    const isRejected = rejectedAssets.includes(fullSrc);
                                    const layout = imageLayouts[fullSrc];

                                    const handleLoad = (e: React.SyntheticEvent<HTMLImageElement>) => {
                                        const { naturalWidth, naturalHeight } = e.currentTarget;
                                        if (!naturalWidth || !naturalHeight) return;
                                        const nextLayout: 'landscape' | 'portrait' | 'square' =
                                            naturalWidth > naturalHeight
                                                ? 'landscape'
                                                : naturalWidth < naturalHeight
                                                    ? 'portrait'
                                                    : 'square';
                                        setImageLayouts(prev => (prev[fullSrc] ? prev : { ...prev, [fullSrc]: nextLayout }));
                                    };

                                    return (
                                        <div className={`relative group w-full rounded-2xl overflow-hidden border transition-all duration-300 bg-white shadow-md ${layout === 'landscape' ? 'sm:col-span-2' : ''} ${isKept
                                            ? 'border-accent shadow-accent/10 scale-[1.02]'
                                            : isRejected
                                                ? 'border-zinc-100 opacity-30 grayscale scale-[0.98]'
                                                : 'border-zinc-100 hover:border-zinc-200'
                                            }`}>
                                            <div className="absolute top-4 left-4 z-10 flex gap-2">
                                                <span className="bg-black/60 backdrop-blur-md text-[10px] uppercase font-black tracking-widest text-white px-2 py-1 rounded border border-white/10">
                                                    Variant
                                                </span>
                                                {isKept && (
                                                    <span className="bg-coral-500 text-white text-[10px] uppercase font-black tracking-widest px-2 py-1 rounded shadow-lg">
                                                        KEEP
                                                    </span>
                                                )}
                                            </div>

                                                <img
                                                    src={fullSrc}
                                                    alt={alt || "Output"}
                                                    onLoad={handleLoad}
                                                    className="w-full h-auto object-cover"
                                                    loading="lazy"
                                                />

                                            <div className="absolute inset-x-0 bottom-0 p-4 bg-gradient-to-t from-black via-black/40 to-transparent opacity-0 group-hover:opacity-100 transition-opacity duration-200">
                                                <div className="flex gap-2">
                                                    <button
                                                        disabled={!activeProject}
                                                        onClick={() => activeProject && saveAsset(fullSrc, activeProject.id)}
                                                        className={`flex-1 flex items-center justify-center gap-2 px-6 py-4 rounded-xl text-xs font-black transition-all ${isKept
                                                            ? 'bg-coral-500 text-white shadow-lg'
                                                            : 'bg-white text-zinc-950 hover:bg-zinc-100 border border-zinc-200'
                                                            }`}
                                                    >
                                                        {isKept ? <Check size={20} /> : <BookmarkPlus size={20} />}
                                                        KEEP
                                                    </button>
                                                    <button
                                                        disabled={!activeProject}
                                                        onClick={() => activeProject && rejectAsset(fullSrc, activeProject.id)}
                                                        className={`flex-1 flex items-center justify-center gap-2 px-6 py-4 rounded-xl text-xs font-black transition-all ${isRejected
                                                            ? 'bg-red-600 text-white shadow-lg'
                                                            : 'bg-zinc-900 text-white hover:bg-black border border-black'
                                                            }`}
                                                    >
                                                        <X size={20} />
                                                        REJ
                                                    </button>
                                                </div>
                                            </div>
                                        </div>
                                    );
                                },
                                ul: ({ node, ...props }: any) => <ul className="list-disc pl-10 mb-8 space-y-4 text-zinc-800 text-3xl font-bold" {...props} />,
                                ol: ({ node, ...props }: any) => <ol className="list-decimal pl-10 mb-8 space-y-4 text-zinc-800 text-3xl font-bold" {...props} />,
                                li: ({ node, ...props }: any) => <li className="pl-2" {...props} />,
                                strong: ({ node, ...props }: any) => <strong className="font-black text-black text-4xl" {...props} />
                            }}
                        >
                            {msg.content}
                        </ReactMarkdown>
                    </div>
                </div>
            ))}

            {isProcessing && (
                <div className="max-w-5xl mx-auto">
                    <SkeletonMessage />
                </div>
            )}
        </div>
    );
}
