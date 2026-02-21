"use client";

import { useEffect, useState } from "react";
import {
    BarChart, Bar, XAxis, YAxis, Tooltip, ResponsiveContainer, CartesianGrid, Cell
} from "recharts";
import { DollarSign, Calendar, TrendingUp } from "lucide-react";
import { API_BASE_URL } from "@/lib/api";

interface MonthlyData {
    month: string;
    month_index: number;
    total: number;
    breakdown: { symbol: string; amount: number }[];
}

interface SummaryData {
    total_annual_cad: number;
    monthly_average_cad: number;
}

interface DividendData {
    summary: SummaryData;
    calendar: MonthlyData[];
}

export default function DividendsPage() {
    const [data, setData] = useState<DividendData | null>(null);
    const [loading, setLoading] = useState(true);
    const [selectedMonth, setSelectedMonth] = useState<string | null>(null);

    useEffect(() => {
        const fetchDividends = async () => {
            try {
                const res = await fetch(`${API_BASE_URL}/api/dividends`);
                if (!res.ok) throw new Error("Failed to fetch");
                const json = await res.json();
                setData(json);
            } catch (err) {
                console.error(err);
            } finally {
                setLoading(false);
            }
        };
        fetchDividends();
    }, []);

    const handleBarClick = (month: string) => {
        setSelectedMonth(month);
        // Scroll to the corresponding row in the table
        const rowElement = document.getElementById(`month-row-${month}`);
        if (rowElement) {
            rowElement.scrollIntoView({ behavior: 'smooth', block: 'center' });
        }
    };

    if (loading) return <div className="p-10 text-center animate-pulse">Loading Dividend Data...</div>;
    if (!data) return <div className="p-10 text-center text-red-500">Failed to load data.</div>;

    // Find Max for Y-Axis
    const maxVal = Math.max(...data.calendar.map(d => d.total));

    return (
        <div className="p-8 max-w-[1600px] mx-auto space-y-8">
            <h1 className="text-3xl font-bold bg-clip-text text-transparent bg-gradient-to-r from-emerald-400 to-cyan-500">
                Projected Dividends
            </h1>

            {/* Summary Cards */}
            <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 gap-6">
                <div className="glass-panel p-6 rounded-2xl flex items-center gap-4">
                    <div className="w-12 h-12 rounded-full bg-emerald-500/20 flex items-center justify-center text-emerald-400">
                        <DollarSign className="w-6 h-6" />
                    </div>
                    <div>
                        <p className="text-gray-400 text-sm">Target Annual Income (CAD)</p>
                        <p className="text-2xl font-bold">${data.summary.total_annual_cad.toFixed(2)}</p>
                    </div>
                </div>

                <div className="glass-panel p-6 rounded-2xl flex items-center gap-4">
                    <div className="w-12 h-12 rounded-full bg-blue-500/20 flex items-center justify-center text-blue-400">
                        <Calendar className="w-6 h-6" />
                    </div>
                    <div>
                        <p className="text-gray-400 text-sm">Monthly Average</p>
                        <p className="text-2xl font-bold">${data.summary.monthly_average_cad.toFixed(2)}</p>
                    </div>
                </div>

                <div className="glass-panel p-6 rounded-2xl flex items-center gap-4">
                    <div className="w-12 h-12 rounded-full bg-purple-500/20 flex items-center justify-center text-purple-400">
                        <TrendingUp className="w-6 h-6" />
                    </div>
                    <div>
                        <p className="text-gray-400 text-sm">Est. Daily Income</p>
                        <p className="text-2xl font-bold">${(data.summary.total_annual_cad / 365).toFixed(2)}</p>
                    </div>
                </div>
            </div>

            {/* Calendar Chart */}
            <div className="glass-panel p-6 rounded-2xl h-[450px] relative">
                <h3 className="text-lg font-semibold mb-6">Income Calendar</h3>
                <div className="flex-1 min-h-0 relative h-[350px]">
                    <ResponsiveContainer width="100%" height="100%">
                        <BarChart data={data.calendar} margin={{ top: 20, right: 30, left: 0, bottom: 5 }}>
                            <CartesianGrid strokeDasharray="3 3" stroke="#333" vertical={false} />
                            <XAxis dataKey="month" stroke="#9ca3af" fontSize={12} tickLine={false} axisLine={false} />
                            <YAxis
                                stroke="#9ca3af"
                                fontSize={12}
                                tickLine={false}
                                axisLine={false}
                                tickFormatter={(val) => `$${val}`}
                            />
                            <Tooltip
                                cursor={{ fill: 'rgba(255,255,255,0.05)' }}
                                contentStyle={{ borderRadius: '8px', border: 'none', boxShadow: '0 4px 6px -1px rgba(0, 0, 0, 0.1)' }}
                                formatter={(val: any) => [`$${val.toFixed(2)}`, 'Income']}
                            />
                            <Bar dataKey="total" radius={[6, 6, 0, 0]} maxBarSize={60} onClick={(data: any) => handleBarClick(data.month)}>
                                {data.calendar.map((entry, index) => (
                                    <Cell
                                        key={`cell-${index}`}
                                        fill={entry.total > data.summary.monthly_average_cad ? '#10B981' : '#3b82f6'}
                                        fillOpacity={0.8}
                                        cursor="pointer"
                                    />
                                ))}
                            </Bar>
                        </BarChart>
                    </ResponsiveContainer>
                </div>
            </div>

            {/* Future Enhancement: Detailed Payout Table by Symbol */}
            <div className="glass-panel rounded-2xl overflow-hidden">
                <div className="p-6 border-b border-white/10">
                    <h3 className="text-lg font-bold">Payouts by Month</h3>
                </div>
                <div className="overflow-x-auto">
                    <table className="w-full text-left text-sm">
                        <thead className="glass-table-header text-gray-400 uppercase text-xs font-semibold">
                            <tr>
                                <th className="p-4">Month</th>
                                <th className="p-4">Paying Stocks</th>
                                <th className="p-4 text-right">Total (CAD)</th>
                            </tr>
                        </thead>
                        <tbody className="divide-y divide-white/5">
                            {data.calendar.map((m) => (
                                <tr
                                    key={m.month}
                                    id={`month-row-${m.month}`}
                                    className={`transition-all duration-300 ${selectedMonth === m.month
                                        ? 'bg-blue-500/20 border-l-4 border-blue-500'
                                        : 'hover:bg-white/5'
                                        }`}
                                >
                                    <td className="p-4 font-medium">{m.month}</td>
                                    <td className="p-4 text-gray-400">
                                        {m.breakdown.length > 0 ? (
                                            <div className="flex flex-wrap gap-2">
                                                {m.breakdown.map((b, i) => (
                                                    <span key={i} className="px-2 py-1 bg-white/5 dark:bg-white/5 rounded text-xs text-blue-700 dark:text-blue-300">
                                                        {b.symbol} (${b.amount.toFixed(0)})
                                                    </span>
                                                ))}
                                            </div>
                                        ) : (
                                            <span className="italic opacity-50">No payouts</span>
                                        )}
                                    </td>
                                    <td className="p-4 text-right font-mono text-emerald-400">
                                        {m.total > 0 ? `$${m.total.toFixed(2)}` : '-'}
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
