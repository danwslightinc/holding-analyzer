"use client";

import Link from "next/link";
import { usePathname } from "next/navigation";
import { usePortfolio } from "@/lib/PortfolioContext";
import { useTheme } from "./ThemeProvider";
import { useSession, signOut } from "next-auth/react";

const NAV_ITEMS = [
    { name: "Home", href: "/", icon: "⌂" },
    { name: "Performance", href: "/performance", icon: "↗" },
    { name: "P&L", href: "/pnl", icon: "₿" },
    { name: "Trade Analysis", href: "/trade-analysis", icon: "⟡" },
    { name: "Allocation", href: "/allocation", icon: "◔" },
    { name: "Dividends", href: "/dividends", icon: "$" },
    { name: "Quant-mental", href: "/quantmental", icon: "⊕" },
    { name: "Transactions", href: "/transactions", icon: "☰" },
];

export default function TopNav() {
    const pathname = usePathname();
    const { refresh, loading } = usePortfolio();
    const { theme, toggleTheme } = useTheme();
    const { data: session } = useSession();

    // Don't render on the home page on desktop — Sidebar handles it.
    // On mobile, we NEED it for navigation.
    // Note: Since we can't easily detect screen width in a server component (or before mount),
    // we let it render and handle visibility in the JSX using Tailwind classes.
    if (pathname === "/login") return null;

    return (
        <nav className={`md:hidden sticky top-0 z-50 backdrop-blur-xl border-b px-6 py-2 ${theme === 'dark'
            ? 'bg-zinc-950/80 border-white/10'
            : 'bg-white/80 border-black/10'
            }`}>
            <div className="max-w-[1800px] mx-auto flex items-center justify-between gap-4">
                {/* Brand / Logo - Only visible on Mobile TopNav */}
                <div className="flex md:hidden items-center gap-2">
                    <span className="text-sm font-black tracking-tighter text-blue-500">DL</span>
                </div>

                {/* Mobile Navigation - Horizontal Scrollable Bar */}
                <div className="flex flex-1 md:hidden items-center gap-1 overflow-x-auto no-scrollbar py-1">
                    {NAV_ITEMS.map((item) => {
                        const isActive = pathname === item.href;
                        return (
                            <Link
                                key={item.href}
                                href={item.href}
                                className={`px-3 py-1.5 rounded-lg text-[10px] font-black tracking-widest transition-all whitespace-nowrap ${isActive
                                    ? "bg-blue-500/20 text-blue-400 border border-blue-500/30"
                                    : "text-zinc-500 hover:text-zinc-200"
                                    }`}
                            >
                                {item.icon} {item.name.toUpperCase()}
                            </Link>
                        );
                    })}
                </div>

                {/* Right side: sync + theme + user */}
                <div className="flex items-center gap-3 ml-auto">
                    <button
                        onClick={() => refresh(true)}
                        disabled={loading}
                        className={`px-3 py-1.5 rounded-lg text-xs font-bold tracking-wider transition-all border ${loading
                            ? "bg-zinc-800/50 border-zinc-700 text-zinc-600 cursor-not-allowed"
                            : "bg-emerald-500/10 border-emerald-500/30 text-emerald-400 hover:bg-emerald-500/20"
                            }`}
                    >
                        {loading ? "⟳ SYNCING..." : "⟳ FORCE SYNC"}
                    </button>

                    <button
                        onClick={toggleTheme}
                        className="px-3 py-1.5 rounded-lg text-xs font-bold tracking-wider text-zinc-500 hover:text-zinc-200 hover:bg-white/5 transition-all"
                    >
                        {theme === "dark" ? "☀" : "☾"}
                    </button>

                    {session && (
                        <div className="flex items-center gap-2">
                            <span className="text-xs text-zinc-500 truncate max-w-[100px]">{session.user?.name}</span>
                            <button
                                onClick={() => signOut({ callbackUrl: "/login" })}
                                className="px-2 py-1 rounded-md text-xs font-bold bg-red-500/10 text-red-400 border border-red-500/20 hover:bg-red-500/20 transition-all"
                            >
                                ⏻
                            </button>
                        </div>
                    )}
                </div>
            </div>
        </nav>
    );
}
