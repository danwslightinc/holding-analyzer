"use client";

import { useEffect, useState } from "react";
import { Plus, Trash2, Calendar, DollarSign, Hash, Tag, FileText } from "lucide-react";
import { API_BASE_URL } from "@/lib/api";

interface Transaction {
    id: number;
    Symbol: string;
    "Purchase Price": number;
    Quantity: number;
    Commission: number;
    "Trade Date": string;
    "Transaction Type": string;
    Comment: string;
}

export default function TransactionsPage() {
    const [transactions, setTransactions] = useState<Transaction[]>([]);
    const [loading, setLoading] = useState(true);
    const [showForm, setShowForm] = useState(false);

    // Form state
    const [form, setForm] = useState({
        Symbol: "",
        Purchase_Price: "",
        Quantity: "",
        Commission: "0",
        Trade_Date: new Date().toISOString().split('T')[0].replace(/-/g, '/'), // YYYY/MM/DD
        Transaction_Type: "Buy",
        Comment: ""
    });

    const fetchTransactions = async () => {
        try {
            const res = await fetch(`${API_BASE_URL}/api/transactions`);
            const data = await res.json();
            setTransactions(data);
        } catch (err) {
            console.error("Failed to fetch transactions", err);
        } finally {
            setLoading(false);
        }
    };

    useEffect(() => {
        fetchTransactions();
    }, []);

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
                    Transaction_Type: "Buy",
                    Comment: ""
                });
                fetchTransactions();
            }
        } catch (err) {
            console.error("Failed to add transaction", err);
        }
    };

    const handleDelete = async (id: number) => {
        if (!confirm("Are you sure you want to delete this transaction?")) return;
        try {
            const res = await fetch(`${API_BASE_URL}/api/transactions/${id}`, {
                method: "DELETE"
            });
            if (res.ok) fetchTransactions();
        } catch (err) {
            console.error("Failed to delete", err);
        }
    };

    if (loading) return <div className="p-10 text-center animate-pulse text-zinc-400">Loading Transactions...</div>;

    return (
        <div className="p-8 max-w-[1400px] mx-auto space-y-8">
            <div className="flex items-center justify-between">
                <div>
                    <h1 className="text-3xl font-bold bg-clip-text text-transparent bg-gradient-to-r from-blue-400 to-purple-500">
                        Transactions
                    </h1>
                    <p className="text-zinc-400 mt-2">Add, remove, and track all portfolio movements</p>
                </div>
                <button
                    onClick={() => setShowForm(!showForm)}
                    className="flex items-center gap-2 bg-blue-600 hover:bg-blue-700 text-white px-5 py-2.5 rounded-xl transition-all font-semibold shadow-lg shadow-blue-900/20"
                >
                    <Plus className="w-5 h-5" />
                    New Transaction
                </button>
            </div>

            {showForm && (
                <div className="glass-panel p-8 rounded-2xl animate-in fade-in slide-in-from-top-4 duration-300">
                    <form onSubmit={handleAdd} className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-4 gap-6">
                        <div className="space-y-2">
                            <label className="text-sm font-semibold text-zinc-300 flex items-center gap-2">
                                <Tag className="w-4 h-4" /> Symbol
                            </label>
                            <input
                                required
                                value={form.Symbol}
                                onChange={e => setForm({ ...form, Symbol: e.target.value.toUpperCase() })}
                                className="w-full bg-black/40 border border-white/10 rounded-xl px-4 py-2.5 text-white focus:border-blue-500 outline-none transition-all"
                                placeholder="e.g. QQQ"
                            />
                        </div>
                        <div className="space-y-2">
                            <label className="text-sm font-semibold text-zinc-300 flex items-center gap-2">
                                <DollarSign className="w-4 h-4" /> Price
                            </label>
                            <input
                                required
                                type="number"
                                step="0.01"
                                value={form.Purchase_Price}
                                onChange={e => setForm({ ...form, Purchase_Price: e.target.value })}
                                className="w-full bg-black/40 border border-white/10 rounded-xl px-4 py-2.5 text-white focus:border-blue-500 outline-none transition-all"
                                placeholder="0.00"
                            />
                        </div>
                        <div className="space-y-2">
                            <label className="text-sm font-semibold text-zinc-300 flex items-center gap-2">
                                <Hash className="w-4 h-4" /> Quantity
                            </label>
                            <input
                                required
                                type="number"
                                step="0.01"
                                value={form.Quantity}
                                onChange={e => setForm({ ...form, Quantity: e.target.value })}
                                className="w-full bg-black/40 border border-white/10 rounded-xl px-4 py-2.5 text-white focus:border-blue-500 outline-none transition-all"
                                placeholder="0.00"
                            />
                        </div>
                        <div className="space-y-2">
                            <label className="text-sm font-semibold text-zinc-300 flex items-center gap-2">
                                <Calendar className="w-4 h-4" /> Date (YYYY/MM/DD)
                            </label>
                            <input
                                required
                                value={form.Trade_Date}
                                onChange={e => setForm({ ...form, Trade_Date: e.target.value })}
                                className="w-full bg-black/40 border border-white/10 rounded-xl px-4 py-2.5 text-white focus:border-blue-500 outline-none transition-all"
                                placeholder="2025/01/01"
                            />
                        </div>
                        <div className="space-y-2">
                            <label className="text-sm font-semibold text-zinc-300">Type</label>
                            <select
                                value={form.Transaction_Type}
                                onChange={e => setForm({ ...form, Transaction_Type: e.target.value })}
                                className="w-full bg-black/40 border border-white/10 rounded-xl px-4 py-2.5 text-white focus:border-blue-500 outline-none transition-all"
                            >
                                <option value="Buy">Buy</option>
                                <option value="Sell">Sell</option>
                            </select>
                        </div>
                        <div className="space-y-2">
                            <label className="text-sm font-semibold text-zinc-300 flex items-center gap-2">
                                <DollarSign className="w-4 h-4" /> Commission
                            </label>
                            <input
                                type="number"
                                step="0.01"
                                value={form.Commission}
                                onChange={e => setForm({ ...form, Commission: e.target.value })}
                                className="w-full bg-black/40 border border-white/10 rounded-xl px-4 py-2.5 text-white focus:border-blue-500 outline-none transition-all"
                            />
                        </div>
                        <div className="md:col-span-2 space-y-2">
                            <label className="text-sm font-semibold text-zinc-300 flex items-center gap-2">
                                <FileText className="w-4 h-4" /> Comment
                            </label>
                            <input
                                value={form.Comment}
                                onChange={e => setForm({ ...form, Comment: e.target.value })}
                                className="w-full bg-black/40 border border-white/10 rounded-xl px-4 py-2.5 text-white focus:border-blue-500 outline-none transition-all"
                                placeholder="Optional"
                            />
                        </div>
                        <div className="md:col-span-4 flex justify-end gap-3 mt-4">
                            <button
                                type="button"
                                onClick={() => setShowForm(false)}
                                className="px-6 py-2.5 rounded-xl border border-white/10 text-zinc-400 hover:bg-white/5 transition-all"
                            >
                                Cancel
                            </button>
                            <button
                                type="submit"
                                className="px-8 py-2.5 rounded-xl bg-blue-600 hover:bg-blue-700 text-white font-bold transition-all"
                            >
                                Save Transaction
                            </button>
                        </div>
                    </form>
                </div>
            )}

            <div className="glass-panel rounded-2xl overflow-hidden">
                <div className="overflow-x-auto">
                    <table className="w-full border-collapse">
                        <thead>
                            <tr className="bg-white/5 text-left">
                                <th className="p-4 font-semibold text-zinc-300">Symbol</th>
                                <th className="p-4 font-semibold text-zinc-300">Date</th>
                                <th className="p-4 font-semibold text-zinc-300">Type</th>
                                <th className="p-4 font-semibold text-zinc-300 text-right">Price</th>
                                <th className="p-4 font-semibold text-zinc-300 text-right">Qty</th>
                                <th className="p-4 font-semibold text-zinc-300 text-right">Commission</th>
                                <th className="p-4 font-semibold text-zinc-300">Comment</th>
                                <th className="p-4 font-semibold text-zinc-300 text-center">Actions</th>
                            </tr>
                        </thead>
                        <tbody>
                            {transactions.map((tx) => (
                                <tr key={tx.id} className="border-b border-white/5 hover:bg-white/5 transition-colors">
                                    <td className="p-4 font-bold text-blue-400">{tx.Symbol}</td>
                                    <td className="p-4 text-zinc-400">{tx["Trade Date"]}</td>
                                    <td className="p-4">
                                        <span className={`px-2 py-1 rounded text-xs font-bold ${tx["Transaction Type"] === 'Sell' ? 'bg-rose-500/20 text-rose-400' : 'bg-emerald-500/20 text-emerald-400'}`}>
                                            {tx["Transaction Type"] || 'Buy'}
                                        </span>
                                    </td>
                                    <td className="p-4 text-right text-zinc-200">${Number(tx["Purchase Price"] || 0).toFixed(2)}</td>
                                    <td className="p-4 text-right text-zinc-200">{Number(tx.Quantity || 0)}</td>
                                    <td className="p-4 text-right text-zinc-200">${Number(tx.Commission || 0).toFixed(2)}</td>
                                    <td className="p-4 text-zinc-400 text-sm italic">{tx.Comment || "--"}</td>
                                    <td className="p-4 text-center">
                                        <button
                                            onClick={() => handleDelete(tx.id)}
                                            className="p-2 text-zinc-500 hover:text-rose-500 transition-colors"
                                            title="Delete Transaction"
                                        >
                                            <Trash2 className="w-5 h-5" />
                                        </button>
                                    </td>
                                </tr>
                            ))}
                        </tbody>
                    </table>
                </div>
            </div>
        </div>
    );
}
