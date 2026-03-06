"use client";

import { useEffect, useState } from "react";

interface MeteorsProps {
    number?: number;
}

export const Meteors = ({ number = 30 }: MeteorsProps) => {
    const [meteorStyles, setMeteorStyles] = useState<Array<React.CSSProperties>>([]);

    useEffect(() => {
        const styles = [...new Array(number)].map(() => ({
            top: Math.floor(Math.random() * 100) + "%",
            left: Math.floor(Math.random() * 100) + "%",
            animationDelay: -Math.random() * 10 + "s",
            animationDuration: Math.floor(Math.random() * 8 + 4) + "s",
        }));
        setMeteorStyles(styles);
    }, [number]);

    return (
        <div className="absolute inset-0 pointer-events-none">
            {meteorStyles.map((style, idx) => (
                <span
                    key={"meteor" + idx}
                    style={style}
                    className="animate-meteor absolute h-1 w-1 rounded-full bg-slate-400 shadow-[0_0_12px_rgba(148,163,184,0.65)] pointer-events-none"
                >
                    {/* The Tail - Trailing back towards top-right */}
                    <div className="absolute top-1/2 -translate-y-1/2 left-0 -translate-x-full w-[220px] h-[1px] bg-gradient-to-l from-slate-400/80 via-slate-400/40 to-transparent" />
                </span>
            ))}
        </div>
    );
};
