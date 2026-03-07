import { useEffect, useRef, useState } from 'react';
import { useAgentStore } from '../../stores/agentStore';
import { useProjectStore } from '../../stores/projectStore';
import ReactMarkdown from 'react-markdown';
import { API_BASE_URL } from '../../lib/constants';
import { Check, X, BookmarkPlus } from 'lucide-react';

export function ConversationView() {
    const { messages, isProcessing } = useAgentStore();
    const { saveAsset, rejectAsset, savedAssets, rejectedAssets, activeProject, projects } = useProjectStore();
    const [imageLayouts, setImageLayouts] = useState<Record<string, 'landscape' | 'portrait' | 'square'>>({});

    const escapeRegex = (value: string) => value.replace(/[.*+?^${}()|[\]\\]/g, '\\$&');

    const formatProjectNames = (content: string) => {
        if (!content || projects.length === 0) return content;
        const linkPattern = /!\[[^\]]*\]\([^\)]+\)|\[[^\]]*\]\([^\)]+\)/g;
        const segments: Array<{ text: string; isLink: boolean }> = [];
        let lastIndex = 0;
        let match: RegExpExecArray | null;

        while ((match = linkPattern.exec(content)) !== null) {
            segments.push({ text: content.slice(lastIndex, match.index), isLink: false });
            segments.push({ text: match[0], isLink: true });
            lastIndex = match.index + match[0].length;
        }
        segments.push({ text: content.slice(lastIndex), isLink: false });

        return segments
            .map((segment) => {
                if (segment.isLink) return segment.text;
                return projects.reduce((acc, project) => {
                    const escapedId = escapeRegex(project.id);
                    const codePattern = new RegExp('`' + escapedId + '`', 'g');
                    const plainPattern = new RegExp(`(?<![A-Za-z0-9-])${escapedId}(?![A-Za-z0-9-])`, 'g');
                    const withName = `*${project.name}*`;
                    return acc.replace(codePattern, withName).replace(plainPattern, withName);
                }, segment.text);
            })
            .join('');
    };

    const stripSystemReminders = (content: string) => {
        return content.replace(/<system-reminder>[\s\S]*?<\/system-reminder>/gi, '').trim();
    };

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

    const [phraseIndex, setPhraseIndex] = useState(0);
    const endRef = useRef<HTMLDivElement | null>(null);
    const phrases = [
        "AWAITING INPUT",
        "STANDING BY",
        "READY TO DEPLOY",
        "BRIEF WHEN READY",
        "BUILD YOUR DIRECTION",
        "CREATE ATTACK PLAN",
        "READY TO COMMENCE",
        "AWAITING DIRECTIVE",
        "PATIENTLY READY",
        "PIECE OF CAKE"
    ];

    useEffect(() => {
        if (messages.length > 0 || isProcessing) return;
        const interval = setInterval(() => {
            setPhraseIndex((prev) => (prev + 1) % phrases.length);
        }, 3000);
        return () => clearInterval(interval);
    }, [messages.length, isProcessing, phrases.length]);

    useEffect(() => {
        if (!endRef.current) return;
        endRef.current.scrollIntoView({ behavior: 'smooth', block: 'end' });
    }, [messages.length, isProcessing]);

    if (messages.length === 0 && !isProcessing) {
        return (
            <div className="flex-1 flex items-center justify-center relative z-10">
                <div key={phraseIndex} className="animate-phrase">
                    <p className="font-doto text-3xl sm:text-4xl md:text-6xl font-black tracking-[-0.05em] text-[#E8825A] uppercase text-center px-6">
                        {phrases[phraseIndex]}
                    </p>
                </div>
            </div>
        );
    }

    return (
        <div className="flex-1 overflow-y-auto p-6 md:p-12 space-y-8 md:space-y-10 relative z-10">
            {messages.map((msg: any) => (
                <div
                    key={msg.id}
                    className={`flex flex-col w-full max-w-6xl mx-auto rounded-[32px] md:rounded-[40px] p-8 md:p-12 animate-message-in ${msg.role === 'user'
                        ? 'bg-zinc-50/80 self-end ml-auto text-zinc-700 max-w-full md:max-w-3xl shadow-md border border-zinc-100 backdrop-blur-sm'
                        : 'bg-white/80 border border-zinc-200 text-zinc-950 shadow-2xl backdrop-blur-sm'
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
                                p: ({ children, ...props }: any) => {
                                    const allImages = props.node?.children?.every((c: any) => c.tagName === 'img' || (c.type === 'text' && !c.value.trim()));
                                    if (allImages) {
                                        return (
                                            <div className="grid grid-cols-1 sm:grid-cols-2 gap-4 mt-6 mb-8">
                                                {children}
                                            </div>
                                        );
                                    }

                                    const hasImage = props.node?.children?.some((c: any) => c.tagName === 'img');
                                    if (hasImage) return <div className="mb-6">{children}</div>;

                                    return <p className="mb-6 last:mb-0 text-2xl font-bold leading-relaxed text-zinc-900" {...props}>{children}</p>;
                                },
                                a: ({ href, ...props }: any) => {
                                    const fullHref = href?.startsWith('/api/') ? `${API_BASE_URL}${href}` : href;
                                    return (
                                        <a href={fullHref} className="text-accent underline underline-offset-8 decoration-2 hover:text-accent-hover transition-all font-black break-all" target={fullHref?.includes('download') ? "_blank" : "_self"} rel="noreferrer" {...props} />
                                    );
                                },
                                img: ({ src, alt }: any) => {
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
                                ul: ({ ...props }: any) => <ul className="list-disc pl-10 mb-8 space-y-4 text-zinc-800 text-2xl font-bold" {...props} />,
                                ol: ({ ...props }: any) => <ol className="list-decimal pl-10 mb-8 space-y-4 text-zinc-800 text-2xl font-bold" {...props} />,
                                li: ({ ...props }: any) => <li className="pl-2" {...props} />,
                                em: ({ ...props }: any) => <em className="font-['Instrument_Serif'] italic text-zinc-900" {...props} />,
                                strong: ({ ...props }: any) => <strong className="font-['Instrument_Serif'] italic font-normal text-zinc-900" {...props} />,
                                code: ({ inline, children, ...props }: any) => {
                                    if (inline) {
                                        return (
                                            <span className="font-['Instrument_Serif'] italic text-zinc-900" {...props}>
                                                {children}
                                            </span>
                                        );
                                    }
                                    return (
                                        <code className="block font-mono text-sm text-zinc-800 bg-zinc-100/80 border border-zinc-200 rounded-xl p-4" {...props}>
                                            {children}
                                        </code>
                                    );
                                }
                            }}
                        >
                            {formatProjectNames(stripSystemReminders(msg.content))}
                        </ReactMarkdown>
                    </div>
                </div>
            ))}

            {isProcessing && (
                <div className="max-w-5xl mx-auto animate-message-in">
                    <div className="flex items-center justify-center py-8">
                        <img
                            src="/load.gif"
                            alt="Loading"
                            className="w-[36px] h-[36px] mix-blend-multiply"
                        />
                    </div>
                </div>
            )}
            <div ref={endRef} />
        </div>
    );
}
