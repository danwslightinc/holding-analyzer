"use client";

import { useEffect, useState, useMemo } from "react";
import {
    Plus, Trash2, Search, X, History, TrendingUp, ArrowRight,
    Filter, DollarSign, Calendar, Briefcase, CreditCard
} from "lucide-react";
import { motion, AnimatePresence } from "framer-motion";
import { API_BASE_URL } from "@/lib/api";

interface Transaction {
    id: number;
    Symbol: string;
    "Purchase Price": number;
    Quantity: number;
    Commission: number;
    "Trade Date": string;
    "Transaction Type": string;
    Broker: string;
    "Account Type": string;
    Comment: string;
}

/** Official bank brand colors for consistency across app */
const BROKER_COLORS: Record<string, { bg: string; text: string; border: string }> = {
    TD: { bg: "rgba(0,138,0,0.15)", text: "#00b300", border: "rgba(0,138,0,0.40)" },
    CIBC: { bg: "rgba(196,31,62,0.15)", text: "#e84464", border: "rgba(196,31,62,0.40)" },
    RBC: { bg: "rgba(0,106,195,0.15)", text: "#3da5ff", border: "rgba(0,106,195,0.40)" },
    Questrade: { bg: "rgba(255,187,0,0.15)", text: "#ffbb00", border: "rgba(255,187,0,0.40)" },
    Manual: { bg: "rgba(255,255,255,0.08)", text: "#a1a1aa", border: "rgba(255,255,255,0.15)" },
};

const ACCOUNT_COLORS: Record<string, { bg: string; text: string; border: string }> = {
    TFSA: { bg: "rgba(20,184,166,0.15)", text: "#2dd4bf", border: "rgba(20,184,166,0.40)" },
    RRSP: { bg: "rgba(139,92,246,0.15)", text: "#a78bfa", border: "rgba(139,92,246,0.40)" },
    FHSA: { bg: "rgba(59,130,246,0.15)", text: "#60a5fa", border: "rgba(59,130,246,0.40)" },
    Open: { bg: "rgba(249,115,22,0.15)", text: "#fb923c", border: "rgba(249,115,22,0.40)" },
};

export default function TransactionsPage() {
    const [transactions, setTransactions] = useState<Transaction[]>([]);
    const [loading, setLoading] = useState(true);
    const [showForm, setShowForm] = useState(false);
    const [searchQuery, setSearchQuery] = useState("");
    const [filterType, setFilterType] = useState<string>("All");

    const [form, setForm] = useState({
        Symbol: "",
        Purchase_Price: "",
        Quantity: "",
        Commission: "0",
        Trade_Date: new Date().toISOString().split('T')[0].replace(/-/g, '/'),
        Transaction_Type: "BUY",
        Broker: "RBC",
        Account_Type: "TFSA",
        Comment: ""
    });

    const fetchTransactions = async () => {
        try {
            const res = await fetch(`${API_BASE_URL}/api/transactions`);
            const data = await res.json();
            setTransactions(data);
        } catch (err) {
            console.error("Failed to fetch", err);
        } finally {
            setLoading(false);
        }
    };

    useEffect(() => {
        fetchTransactions();
    }, []);

    const filteredTransactions = useMemo(() => {
        return transactions.filter(tx => {
            const matchesSearch = (tx.Symbol || "").toLowerCase().includes(searchQuery.toLowerCase()) ||
                (tx.Broker || "").toLowerCase().includes(searchQuery.toLowerCase());
            const matchesFilter = filterType === "All" || (tx["Transaction Type"] || "").toUpperCase() === filterType.toUpperCase();
            return matchesSearch && matchesFilter;
        });
    }, [transactions, searchQuery, filterType]);

    const handleAdd = async (e: React.FormEvent) => {
        e.preventDefault();
        try {
            const res = await fetch(`${API_BASE_URL}/api/transactions`, {
                method: "POST",
                headers: { "Content-Type": "application/json" },
                body: JSON.stringify({
                    ...form,
                    Purchase_Price: parseFloat(form.Purchase_Price),
                    Quantity: parseFloat(form.Quantity),
                    Commission: parseFloat(form.Commission)
                })
            });
            if (res.ok) {
                setShowForm(false);
                setForm({
                    Symbol: "",
                    Purchase_Price: "",
                    Quantity: "",
                    Commission: "0",
                    Trade_Date: new Date().toISOString().split('T')[0].replace(/-/g, '/'),
                    Transaction_Type: "BUY",
                    Broker: "RBC",
                    Account_Type: "TFSA",
                    Comment: ""
                });
                fetchTransactions();
            }
        } catch (err) {
            console.error("Failed to add", err);
        }
    };

    const handleDelete = async (id: number) => {
        if (!confirm("Are you sure you want to purge this record?")) return;
        try {
            const res = await fetch(`${API_BASE_URL}/api/transactions/${id}`, { method: "DELETE" });
            if (res.ok) fetchTransactions();
        } catch (err) {
            console.error("Delete failed", err);
        }
    };

    if (loading) return (
        <div className="p-20 text-center animate-pulse text-gray-400 font-medium">
            Syncing Institution Records...
        </div>
    );

    return (
        <div className="p-8 max-w-[1600px] mx-auto space-y-8 font-sans">

            {/* Header: Institutional Grade */}
            <div className="flex flex-col md:flex-row md:items-end justify-between gap-6 pb-2">
                <div className="space-y-2">
                    <div className="flex items-center gap-2 text-blue-500 font-bold uppercase tracking-wider text-xs">
                        <History className="w-4 h-4" />
                        Execution Archive
                    </div>
                    <h1 className="text-4xl md:text-5xl font-bold text-foreground tracking-tight">
                        Transaction Ledger
                    </h1>
                    <p className="text-gray-500 max-w-xl">
                        A definitive record of capital allocation, security execution, and account history.
                    </p>
                </div>

                <button
                    onClick={() => setShowForm(!showForm)}
                    className={`inline-flex items-center gap-2 px-6 py-3 rounded-xl font-bold transition-all shadow-lg active:scale-95 ${showForm
                        ? "bg-gray-100 dark:bg-white/10 text-foreground hover:bg-gray-200 dark:hover:bg-white/20"
                        : "bg-blue-600 hover:bg-blue-700 text-white shadow-blue-900/10"
                        }`}
                >
                    {showForm ? <X className="w-5 h-5" /> : <Plus className="w-5 h-5" />}
                    {showForm ? "Cancel Entry" : "Record Entry"}
                </button>
            </div>

            {/* Inline Form: Appears "Right under Add button" as requested */}
            {showForm && (
                <div>
                    <div className="glass-panel rounded-2xl shadow-2xl p-8 mb-8 border border-blue-500/20 bg-blue-500/5">
                        <div className="flex items-center justify-between mb-8">
                            <div>
                                <h2 className="text-2xl font-bold text-foreground flex items-center gap-2">
                                    <History className="w-6 h-6 text-blue-500" />
                                    Manual Trade Entry
                                </h2>
                                <p className="text-sm text-gray-500">Document a new security execution for your portfolio history.</p>
                            </div>
                        </div>

                        <form onSubmit={handleAdd} className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-4 gap-6">
                            <div className="space-y-1.5 lg:col-span-1">
                                <label className="text-[10px] font-bold text-gray-500 uppercase tracking-widest ml-4">Asset Symbol</label>
                                <input
                                    required
                                    value={form.Symbol}
                                    onChange={e => setForm({ ...form, Symbol: e.target.value.toUpperCase() })}
                                    className="w-full h-[56px] bg-slate-100 dark:bg-white/5 border border-slate-200 dark:border-white/10 text-foreground text-xl font-bold uppercase rounded-xl px-4 focus:ring-2 focus:ring-blue-500 outline-none transition-colors"
                                />
                            </div>

                            <div className="space-y-1.5">
                                <label className="text-[10px] font-bold text-gray-500 uppercase tracking-widest ml-4">Execution Price</label>
                                <input
                                    required
                                    type="number"
                                    step="0.0001"
                                    value={form.Purchase_Price}
                                    onChange={e => setForm({ ...form, Purchase_Price: e.target.value })}
                                    className="w-full h-[56px] bg-slate-100 dark:bg-white/5 border border-slate-200 dark:border-white/10 text-foreground font-bold rounded-xl px-4 focus:ring-2 focus:ring-blue-500 outline-none transition-colors"
                                />
                            </div>

                            <div className="space-y-1.5">
                                <label className="text-[10px] font-bold text-gray-500 uppercase tracking-widest ml-4">Volume (Qty)</label>
                                <input
                                    required
                                    type="number"
                                    step="0.000001"
                                    value={form.Quantity}
                                    onChange={e => setForm({ ...form, Quantity: e.target.value })}
                                    className="w-full h-[56px] bg-slate-100 dark:bg-white/5 border border-slate-200 dark:border-white/10 text-foreground font-bold rounded-xl px-4 focus:ring-2 focus:ring-blue-500 outline-none transition-colors"
                                />
                            </div>

                            <div className="space-y-1.5">
                                <label className="text-[10px] font-bold text-gray-500 uppercase tracking-widest ml-4">Trade Date</label>
                                <input
                                    required
                                    type="date"
                                    value={form.Trade_Date.replace(/\//g, "-")}
                                    onChange={e => setForm({ ...form, Trade_Date: e.target.value.replace(/-/g, "/") })}
                                    className="w-full h-[56px] bg-slate-100 dark:bg-white/5 border border-slate-200 dark:border-white/10 text-foreground font-bold rounded-xl px-4 outline-none focus:ring-2 focus:ring-blue-500 [color-scheme:light] dark:[color-scheme:dark] transition-colors"
                                />
                            </div>

                            <div className="space-y-1.5">
                                <label className="text-[10px] font-bold text-gray-500 uppercase tracking-widest ml-4">Brokerage</label>
                                <select
                                    value={form.Broker}
                                    onChange={e => setForm({ ...form, Broker: e.target.value })}
                                    className="w-full h-[56px] bg-slate-100 dark:bg-white/5 border border-slate-200 dark:border-white/10 text-foreground font-bold rounded-xl px-4 outline-none appearance-none cursor-pointer hover:bg-slate-200 dark:hover:bg-white/10 transition-colors"
                                >
                                    <option value="RBC">RBC Direct</option>
                                    <option value="CIBC">CIBC Edge</option>
                                    <option value="TD">TD Direct</option>
                                    <option value="Questrade">Questrade</option>
                                    <option value="Manual">Manual</option>
                                </select>
                            </div>

                            <div className="space-y-1.5">
                                <label className="text-[10px] font-bold text-gray-500 uppercase tracking-widest ml-4">Account Type</label>
                                <select
                                    value={form.Account_Type}
                                    onChange={e => setForm({ ...form, Account_Type: e.target.value })}
                                    className="w-full h-[56px] bg-slate-100 dark:bg-white/5 border border-slate-200 dark:border-white/10 text-foreground font-bold rounded-xl px-4 outline-none appearance-none cursor-pointer hover:bg-slate-200 dark:hover:bg-white/10 transition-colors"
                                >
                                    <option value="TFSA">TFSA</option>
                                    <option value="RRSP">RRSP</option>
                                    <option value="FHSA">FHSA</option>
                                    <option value="Open">Margin / Open</option>
                                </select>
                            </div>

                            <div className="space-y-1.5 lg:col-span-1">
                                <label className="text-[10px] font-bold text-gray-500 uppercase tracking-widest ml-4">Action</label>
                                <div className="flex bg-slate-100 dark:bg-white/5 p-1 rounded-xl border border-slate-200 dark:border-white/10 h-[56px] items-center">
                                    {["BUY", "SELL", "DRIP"].map((t) => {
                                        const isActive = form.Transaction_Type === t;
                                        return (
                                            <button
                                                key={t}
                                                type="button"
                                                onClick={() => setForm({ ...form, Transaction_Type: t })}
                                                className={`flex-1 h-full rounded-lg text-xs font-bold transition-all ${isActive
                                                        ? (t === 'SELL' ? "bg-rose-500 text-white shadow-md" : "bg-emerald-500 text-white shadow-md")
                                                        : "text-gray-500 hover:text-foreground"
                                                    }`}
                                            >
                                                {t}
                                            </button>
                                        );
                                    })}
                                </div>
                            </div>

                            <div className="flex items-end justify-end lg:col-span-1">
                                <button
                                    type="submit"
                                    className={`h-[56px] px-8 w-full rounded-xl font-bold flex items-center justify-center gap-2 transition-all shadow-lg text-white ${form.Transaction_Type === 'SELL'
                                            ? "bg-rose-600 hover:bg-rose-700 shadow-rose-900/20"
                                            : form.Transaction_Type === 'BUY'
                                                ? "bg-emerald-600 hover:bg-emerald-700 shadow-emerald-900/20"
                                                : "bg-blue-600 hover:bg-blue-700 shadow-blue-900/20"
                                        } border border-transparent dark:border-white/10 group`}
                                >
                                    <span>Confirm Entry</span>
                                    <ArrowRight className="w-5 h-5 transition-transform group-hover:translate-x-1" />
                                </button>
                            </div>
                        </form>
                    </div>
                </div>
            )}

            {/* Sub-Header: Search & Intelligence */}
            <div className="grid grid-cols-1 lg:grid-cols-4 gap-4">
                <div className="lg:col-span-3 relative flex items-center">
                    <Search className="absolute left-4 w-4 h-4 text-gray-500 pointer-events-none" />
                    <input
                        type="text"
                        placeholder="Search by ticker, broker, or notes..."
                        value={searchQuery}
                        onChange={(e) => setSearchQuery(e.target.value)}
                        className="w-full h-[46px] bg-white border border-gray-200 dark:bg-white/5 dark:border-white/10 text-foreground text-sm rounded-xl block pl-11 focus:ring-blue-500 focus:border-blue-500 outline-none transition-all hover:bg-gray-50 dark:hover:bg-white/10"
                    />
                </div>

                <div className="flex h-[46px] p-1 bg-white/5 rounded-xl border border-white/10">
                    {["All", "Buy", "Sell", "DRIP"].map((t) => (
                        <button
                            key={t}
                            onClick={() => setFilterType(t)}
                            className={`flex-1 rounded-lg text-xs font-bold transition-all ${filterType === t
                                ? "bg-blue-600 text-white shadow-md"
                                : "text-gray-500 hover:text-foreground"
                                }`}
                        >
                            {t}
                        </button>
                    ))}
                </div>
            </div>

            {/* Main Ledger: High-Density Table */}
            <div className="glass-panel rounded-2xl overflow-hidden shadow-2xl">
                <div className="overflow-x-auto">
                    <table className="w-full text-left text-sm">
                        <thead className="text-gray-400 bg-white/5 uppercase text-[10px] font-bold tracking-widest">
                            <tr>
                                <th className="px-6 py-4">Asset</th>
                                <th className="px-6 py-4">Execution Date</th>
                                <th className="px-6 py-4">Action</th>
                                <th className="px-6 py-4 text-right">Unit Price</th>
                                <th className="px-6 py-4 text-right">Volume</th>
                                <th className="px-6 py-4 text-right">Total (CAD)</th>
                                <th className="px-6 py-4 text-center">Purge</th>
                            </tr>
                        </thead>
                        <tbody className="divide-y divide-white/5">
                            {filteredTransactions.map((tx) => {
                                const bStyle = BROKER_COLORS[tx.Broker] ?? BROKER_COLORS.Manual;
                                const aStyle = ACCOUNT_COLORS[tx["Account Type"]] ?? BROKER_COLORS.Manual;
                                const txType = (tx["Transaction Type"] || "").toUpperCase();
                                const isSell = txType === 'SELL';

                                return (
                                    <tr key={tx.id} className="hover:bg-white/5 transition-colors group">
                                        <td className="px-6 py-5">
                                            <div className="font-bold text-base text-foreground">{tx.Symbol}</div>
                                            <div className="mt-1 flex gap-1">
                                                <span style={{ background: bStyle.bg, color: bStyle.text, border: `1px solid ${bStyle.border}` }}
                                                    className="px-1.5 py-0.5 rounded text-[10px] font-bold uppercase">
                                                    {tx.Broker}
                                                </span>
                                            </div>
                                        </td>
                                        <td className="px-6 py-5">
                                            <div className="font-medium text-foreground">{tx["Trade Date"]}</div>
                                            <div className="mt-1 flex gap-1">
                                                <span style={{ background: aStyle.bg, color: aStyle.text, border: `1px solid ${aStyle.border}` }}
                                                    className="px-1.5 py-0.5 rounded text-[10px] font-bold uppercase">
                                                    {tx["Account Type"]}
                                                </span>
                                            </div>
                                        </td>
                                        <td className="px-6 py-5">
                                            <span className={`px-2 py-0.5 rounded text-[10px] font-bold uppercase tracking-wider ${isSell
                                                ? 'bg-red-500/10 text-red-400 border border-red-500/20'
                                                : 'bg-emerald-500/10 text-emerald-400 border border-emerald-500/20'
                                                }`}>
                                                {tx["Transaction Type"] || 'BUY'}
                                            </span>
                                        </td>
                                        <td className="px-6 py-5 text-right font-semibold tabular-nums text-foreground">
                                            ${Number(tx["Purchase Price"] || 0).toLocaleString(undefined, { minimumFractionDigits: 2, maximumFractionDigits: 2 })}
                                        </td>
                                        <td className="px-6 py-5 text-right font-medium text-gray-500 tabular-nums uppercase">
                                            {tx.Quantity} <span className="text-[10px] opacity-40">units</span>
                                        </td>
                                        <td className="px-6 py-5 text-right font-bold text-foreground tabular-nums">
                                            ${(Number(tx["Purchase Price"] || 0) * Number(tx.Quantity || 0) + Number(tx.Commission || 0)).toLocaleString(undefined, { minimumFractionDigits: 2, maximumFractionDigits: 2 })}
                                        </td>
                                        <td className="px-6 py-5 text-center">
                                            <button
                                                onClick={() => handleDelete(tx.id)}
                                                className="p-2 text-gray-600 hover:text-rose-500 hover:bg-rose-500/10 rounded-lg transition-all"
                                            >
                                                <Trash2 className="w-4 h-4" />
                                            </button>
                                        </td>
                                    </tr>
                                );
                            })}
                            {filteredTransactions.length === 0 && (
                                <tr>
                                    <td colSpan={7} className="px-6 py-20 text-center text-gray-500">
                                        No execution records found matching your filters.
                                    </td>
                                </tr>
                            )}
                        </tbody>
                    </table>
                </div>
            </div>

        </div>
    );
}
