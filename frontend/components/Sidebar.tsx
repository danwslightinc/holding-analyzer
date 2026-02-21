"use client";

import { Home, TrendingUp, PieChart, DollarSign, Sun, Moon, Brain, List, RefreshCw } from "lucide-react";
import Link from "next/link";
import { usePathname } from "next/navigation";
import { useTheme } from "./ThemeProvider";
import { usePortfolio } from "@/lib/PortfolioContext";

const NAV_ITEMS = [
    { name: "Home", icon: Home, href: "/" },
    { name: "Performance", icon: TrendingUp, href: "/performance" },
    { name: "Allocation", icon: PieChart, href: "/allocation" },
    { name: "Dividends", icon: DollarSign, href: "/dividends" },
    { name: "Quant-mental", icon: Brain, href: "/quantmental" },
    { name: "Transactions", icon: List, href: "/transactions" },
];

export default function Sidebar() {
    const pathname = usePathname();
    const { theme, toggleTheme } = useTheme();
    const { refresh, loading } = usePortfolio();

    return (
        <aside className="w-64 h-full glass-panel border-r border-white/10 flex flex-col hidden md:flex">
            {/* Logo area */}
            <div className="p-6 border-b border-white/10">
                <h1
                    className="text-2xl font-bold bg-clip-text text-transparent bg-gradient-to-r from-blue-400 to-purple-500"
                    suppressHydrationWarning
                >
                    Dawn's Light Inc
                </h1>
                <p className="text-xs text-gray-400 mt-1">Portfolio Tracker</p>
            </div>

            {/* Navigation */}
            <nav className="flex-1 p-4 space-y-2">
                {NAV_ITEMS.map((item) => {
                    const isActive = pathname === item.href;
                    return (
                        <Link
                            key={item.href}
                            href={item.href}
                            className={`flex items-center gap-3 px-4 py-3 rounded-xl transition-all duration-200 group ${isActive
                                ? "bg-blue-500/20 text-blue-400 border border-blue-500/30 shadow-[0_0_15px_rgba(59,130,246,0.3)]"
                                : "text-gray-400 hover:text-foreground hover:bg-black/5 dark:hover:bg-white/5"
                                }`}
                        >
                            <item.icon className={`w-5 h-5 transition-colors ${isActive ? "text-blue-400" : "group-hover:text-blue-400"}`} />
                            <span className="font-medium">{item.name}</span>
                        </Link>
                    );
                })}
            </nav>

            {/* Footer / Theme Toggle & Refresh */}
            <div className="p-4 border-t border-white/10 space-y-2">
                <button
                    onClick={() => refresh()}
                    disabled={loading}
                    className="flex items-center gap-3 px-4 py-3 w-full rounded-xl text-gray-400 hover:text-foreground hover:bg-black/5 dark:hover:bg-white/5 transition-colors group disabled:opacity-50"
                >
                    <RefreshCw className={`w-5 h-5 group-hover:text-blue-400 transition-all ${loading ? 'animate-spin' : ''}`} />
                    <span className="font-medium">{loading ? 'Syncing...' : 'Sync Data'}</span>
                </button>

                <button
                    onClick={toggleTheme}
                    className="flex items-center gap-3 px-4 py-3 w-full rounded-xl text-gray-400 hover:text-foreground hover:bg-black/5 dark:hover:bg-white/5 transition-colors group"
                >
                    {theme === 'dark' ? (
                        <Sun className="w-5 h-5 group-hover:text-amber-400 transition-colors" />
                    ) : (
                        <Moon className="w-5 h-5 group-hover:text-blue-600 transition-colors" />
                    )}
                    <span className="font-medium">{theme === 'dark' ? 'Light Mode' : 'Dark Mode'}</span>
                </button>
            </div>
        </aside>
    );
}
