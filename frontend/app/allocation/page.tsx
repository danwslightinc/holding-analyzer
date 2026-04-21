"use client";

import { useEffect, useState } from "react";
import {
    PieChart, Pie, Cell, Tooltip, ResponsiveContainer, Legend
} from "recharts";
import { Activity, Layers, Tag, Globe, Briefcase, CreditCard } from "lucide-react";
import { API_BASE_URL } from "@/lib/api";
import { usePortfolio } from "@/lib/PortfolioContext";

interface Holding {
    Symbol: string;
    Sector: string;
    Country?: string;
    Market_Value: number;
    Market_Value_CAD?: number;
    PnL: number;
    [key: string]: any;
}

const COLORS = ['#3b82f6', '#10b981', '#f59e0b', '#ef4444', '#8b5cf6', '#ec4899', '#06b6d4', '#84cc16'];

const CustomTooltip = ({ active, payload, totalValue }: any) => {
    if (active && payload && payload.length) {
        const data = payload[0];
        const percent = totalValue ? ((data.value / totalValue) * 100).toFixed(1) : '0.0';

        return (
            <div className="bg-white/90 dark:bg-zinc-900/95 p-3 rounded-lg shadow-xl border border-gray-200 dark:border-white/10 backdrop-blur-md">
                <p className="font-bold text-gray-900 dark:text-white mb-1">{data.name}</p>
                <div className="flex items-center gap-2">
                    <span className="text-sm font-mono text-gray-700 dark:text-gray-300">
                        ${data.value.toLocaleString(undefined, { minimumFractionDigits: 2, maximumFractionDigits: 2 })} CAD
                    </span>
                    <span className="text-xs font-medium px-1.5 py-0.5 rounded bg-blue-500/10 text-blue-600 dark:text-blue-400">
                        {percent}%
                    </span>
                </div>
            </div>
        );
    }
    return null;
};

export default function AllocationPage() {
    const { data, loading, error } = usePortfolio();

    if (loading && !data) return <div className="p-10 text-center animate-pulse">Loading Allocation...</div>;
    if (error) return <div className="p-10 text-center text-red-500">Failed to load data.</div>;
    if (!data) return null;

    // Process Data into Groups
    const sectorMap: Record<string, number> = {};
    const geoMap: Record<string, number> = {};
    const holdingMap: Record<string, number> = {};
    const accountMap: Record<string, number> = {};
    const brokerMap: Record<string, number> = {};
    const holdingSectorMap: Record<string, string> = {};

    data.holdings.forEach((h: Holding) => {
        const val = h.Market_Value_CAD || h.Market_Value || 0;
        
        const s = h.Sector || "Unknown";
        sectorMap[s] = (sectorMap[s] || 0) + val;

        const g = h.Country || "Unknown";
        geoMap[g] = (geoMap[g] || 0) + val;
        
        const a = h.Account_Type || h["Account Type"] || h.account || "Unknown";
        accountMap[a] = (accountMap[a] || 0) + val;
        
        const b = h.Broker || h.broker || "Unknown";
        brokerMap[b] = (brokerMap[b] || 0) + val;

        const sym = h.Symbol;
        holdingMap[sym] = (holdingMap[sym] || 0) + val;
        holdingSectorMap[sym] = s;
    });

    const sectorData = Object.keys(sectorMap)
        .map((key: string) => ({ name: key, value: sectorMap[key] }))
        .sort((a: any, b: any) => b.value - a.value);

    const geoData = Object.keys(geoMap)
        .map((key: string) => ({ name: key, value: geoMap[key] }))
        .sort((a: any, b: any) => b.value - a.value);

    const holdingData = Object.keys(holdingMap)
        .map((key: string) => ({ name: key, value: holdingMap[key] }))
        .sort((a: any, b: any) => b.value - a.value);

    const accountData = Object.keys(accountMap)
        .map((key: string) => ({ name: key, value: accountMap[key] }))
        .sort((a: any, b: any) => b.value - a.value);

    const brokerData = Object.keys(brokerMap)
        .map((key: string) => ({ name: key, value: brokerMap[key] }))
        .sort((a: any, b: any) => b.value - a.value);

    const totalVal = data.summary.total_value;

    return (
        <div className="p-4 md:p-8 max-w-[1800px] mx-auto space-y-8">
            <h1 className="text-3xl font-bold bg-clip-text text-transparent bg-gradient-to-r from-blue-400 to-purple-500">
                Asset Allocation
            </h1>

            <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 xl:grid-cols-5 gap-6">
                {[
                    { title: "Sector", data: sectorData, icon: Activity, color: "text-blue-400" },
                    { title: "Geography", data: geoData, icon: Globe, color: "text-emerald-400" },
                    { title: "Account", data: accountData, icon: CreditCard, color: "text-purple-400" },
                    { title: "Broker", data: brokerData, icon: Briefcase, color: "text-rose-400" },
                    { title: "Holding", data: holdingData, icon: Tag, color: "text-orange-400" },
                ].map((chart, i) => (
                    <div key={chart.title} className="glass-panel p-6 rounded-2xl h-[350px] flex flex-col">
                        <h3 className="text-sm font-bold mb-4 flex items-center gap-2 text-gray-400 uppercase tracking-widest">
                            <chart.icon className={`w-4 h-4 ${chart.color}`} /> {chart.title}
                        </h3>
                        <div className="flex-1 min-h-0 relative">
                            <div className="absolute inset-0">
                                <ResponsiveContainer width="100%" height="100%">
                                    <PieChart>
                                        <Pie
                                            data={chart.data}
                                            dataKey="value"
                                            nameKey="name"
                                            cx="50%"
                                            cy="50%"
                                            innerRadius={60}
                                            outerRadius={90}
                                            paddingAngle={2}
                                        >
                                            {chart.data.map((entry: any, index: number) => (
                                                <Cell key={`cell-${index}`} fill={COLORS[index % COLORS.length]} />
                                            ))}
                                        </Pie>
                                        <Tooltip content={<CustomTooltip totalValue={totalVal} />} />
                                    </PieChart>
                                </ResponsiveContainer>
                            </div>
                        </div>
                    </div>
                ))}
            </div>

            {/* Detailed Allocation Table */}
            <div className="glass-panel rounded-2xl overflow-hidden shadow-xl border border-white/5">
                <div className="p-6 border-b border-white/10 bg-white/5">
                    <h3 className="text-lg font-bold">Allocation Breakdown</h3>
                </div>
                <div className="overflow-x-auto">
                    <table className="w-full text-left text-sm">
                        <thead className="bg-white/5 text-gray-400 uppercase text-[10px] font-bold tracking-widest">
                            <tr>
                                <th className="p-4">Group</th>
                                <th className="p-4 text-right">Value (CAD)</th>
                                <th className="p-4 text-right">Weight</th>
                                <th className="p-4">Top Holding</th>
                            </tr>
                        </thead>
                        <tbody className="divide-y divide-white/5">
                            {sectorData.map((s: any, idx: number) => {
                                const sectorHoldings = holdingData
                                    .filter((h: any) => holdingSectorMap[h.name] === s.name)
                                    .sort((a: any, b: any) => b.value - a.value);
                                const top = sectorHoldings[0];
                                const weight = (s.value / totalVal) * 100;

                                return (
                                    <tr key={s.name} className="hover:bg-white/5 transition-colors">
                                        <td className="p-4 font-medium flex items-center gap-2">
                                            <span className="w-2 h-2 rounded-full" style={{ backgroundColor: COLORS[idx % COLORS.length] }}></span>
                                            {s.name}
                                        </td>
                                        <td className="p-4 text-right font-mono">${s.value.toLocaleString(undefined, { minimumFractionDigits: 2, maximumFractionDigits: 2 })}</td>
                                        <td className="p-4 text-right font-bold">{weight.toFixed(1)}%</td>
                                        <td className="p-4 text-gray-400 text-xs">
                                            {top ? `${top.name} (${((top.value / s.value) * 100).toFixed(0)}%)` : '-'}
                                        </td>
                                    </tr>
                                )
                            })}
                        </tbody>
                    </table>
                </div>
            </div >
        </div >
    );
}
