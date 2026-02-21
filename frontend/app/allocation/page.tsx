"use client";

import { useEffect, useState } from "react";
import {
    PieChart, Pie, Cell, Tooltip, ResponsiveContainer, Treemap, Legend
} from "recharts";
import { Activity, Layers, Tag, Globe } from "lucide-react";
import { API_BASE_URL } from "@/lib/api";
import { usePortfolio } from "@/lib/PortfolioContext";

interface Holding {
    Symbol: string;
    Sector: string;
    Country?: string;
    Market_Value: number;
    PnL: number;
    [key: string]: any;
}


interface PortfolioData {
    summary: { total_value: number };
    holdings: Holding[];
}

const COLORS = ['#0088FE', '#00C49F', '#FFBB28', '#FF8042', '#AF19FF', '#FF1919', '#10B981', '#6366F1'];

const CustomizedTreemapContent = (props: any) => {
    const { root, depth, x, y, width, height, index, name, value, colors } = props;

    return (
        <g>
            <rect
                x={x}
                y={y}
                width={width}
                height={height}
                style={{
                    fill: colors[index % colors.length],
                    stroke: '#fff',
                    strokeWidth: 2 / (depth + 1e-10),
                    strokeOpacity: 1 / (depth + 1e-10),
                }}
            />
            {width > 50 && height > 30 && (
                <text
                    x={x + width / 2}
                    y={y + height / 2}
                    textAnchor="middle"
                    fill="#fff"
                    fontSize={12}
                    fontWeight="bold"
                    style={{ pointerEvents: "none" }}
                >
                    {name}
                </text>
            )}
            {width > 50 && height > 30 && (
                <text
                    x={x + width / 2}
                    y={y + height / 2 + 14}
                    textAnchor="middle"
                    fill="#rgba(255,255,255,0.8)"
                    fontSize={10}
                    style={{ pointerEvents: "none" }}
                >
                    {((value / root.value) * 100).toFixed(1)}%
                </text>
            )}
        </g>
    );
};

const CustomTooltip = ({ active, payload, totalValue }: any) => {
    if (active && payload && payload.length) {
        const data = payload[0];
        const percent = totalValue ? ((data.value / totalValue) * 100).toFixed(1) : '0.0';

        return (
            <div className="bg-white/90 dark:bg-zinc-900/95 p-3 rounded-lg shadow-xl border border-gray-200 dark:border-white/10 backdrop-blur-md">
                <p className="font-bold text-gray-900 dark:text-white mb-1">{data.name}</p>
                <div className="flex items-center gap-2">
                    <span className="text-sm font-mono text-gray-700 dark:text-gray-300">
                        ${data.value.toLocaleString()}
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

    // Process Data into Groups (Sector & Geo)
    const sectorMap: Record<string, number> = {};
    const geoMap: Record<string, number> = {};

    data.holdings.forEach(h => {
        const s = h.Sector || "Unknown";
        sectorMap[s] = (sectorMap[s] || 0) + h.Market_Value;

        const g = h.Country || "Unknown";
        geoMap[g] = (geoMap[g] || 0) + h.Market_Value;
    });

    const sectorData = Object.keys(sectorMap)
        .map(key => ({ name: key, value: sectorMap[key] }))
        .sort((a, b) => b.value - a.value);

    const geoData = Object.keys(geoMap)
        .map(key => ({ name: key, value: geoMap[key] }))
        .sort((a, b) => b.value - a.value);

    // Treemap Data Structure (Flat for simpler visualization or Nested if needed)
    // Recharts Treemap takes a flat list or tree. Let's do flat tickers for now, but grouped visually would be better.
    // Actually, Recharts Treemap is simple. Let's just mapping tickers as children of a root.
    const treemapData = [
        {
            name: 'Portfolio',
            children: data.holdings.map(h => ({
                name: h.Symbol,
                value: h.Market_Value,
                sector: h.Sector
            }))
        }
    ];

    return (
        <div className="p-8 max-w-[1600px] mx-auto space-y-8">
            <h1 className="text-3xl font-bold bg-clip-text text-transparent bg-gradient-to-r from-blue-400 to-purple-500">
                Asset Allocation
            </h1>

            <div className="grid grid-cols-1 lg:grid-cols-2 gap-8">
                {/* Sector Breakout (Donut) */}
                <div className="glass-panel p-6 rounded-2xl h-[400px] flex flex-col">
                    <h3 className="text-lg font-semibold mb-4 flex items-center gap-2">
                        <Activity className="w-5 h-5 text-blue-400" /> By Sector
                    </h3>
                    <div className="flex-1 min-h-0 relative">
                        <div className="absolute inset-0">
                            <ResponsiveContainer width="100%" height="100%">
                                <PieChart>
                                    <Pie
                                        data={sectorData}
                                        dataKey="value"
                                        nameKey="name"
                                        cx="50%"
                                        cy="50%"
                                        innerRadius={80}
                                        outerRadius={120}
                                        paddingAngle={2}
                                    >
                                        {sectorData.map((entry, index) => (
                                            <Cell key={`cell-${index}`} fill={COLORS[index % COLORS.length]} />
                                        ))}
                                    </Pie>
                                    <Tooltip content={<CustomTooltip totalValue={data.summary.total_value} />} />
                                </PieChart>
                            </ResponsiveContainer>
                        </div>
                    </div>
                </div>


                {/* Geographic Allocation (Donut) */}
                <div className="glass-panel p-6 rounded-2xl h-[400px] flex flex-col">
                    <h3 className="text-lg font-semibold mb-4 flex items-center gap-2">
                        <Globe className="w-5 h-5 text-emerald-400" /> By Geography
                    </h3>
                    <div className="flex-1 min-h-0 relative">
                        <div className="absolute inset-0">
                            <ResponsiveContainer width="100%" height="100%">
                                <PieChart>
                                    <Pie
                                        data={geoData}
                                        dataKey="value"
                                        nameKey="name"
                                        cx="50%"
                                        cy="50%"
                                        innerRadius={80}
                                        outerRadius={120}
                                        paddingAngle={2}
                                    >
                                        {geoData.map((entry, index) => (
                                            <Cell key={`cell-${index}`} fill={COLORS[index % COLORS.length]} />
                                        ))}
                                    </Pie>
                                    <Tooltip content={<CustomTooltip totalValue={data.summary.total_value} />} />
                                </PieChart>
                            </ResponsiveContainer>
                        </div>
                    </div>
                </div>

            </div>

            {/* Holdings Treemap */}
            <div className="glass-panel p-6 rounded-2xl h-[500px] flex flex-col">
                <h3 className="text-lg font-semibold mb-4 flex items-center gap-2">
                    <Layers className="w-5 h-5 text-purple-400" /> Holdings Weight
                </h3>
                <div className="flex-1 min-h-0 relative">
                    <div className="absolute inset-0">
                        <ResponsiveContainer width="100%" height="100%">
                            <Treemap
                                data={treemapData}
                                dataKey="value"
                                aspectRatio={4 / 3}
                                stroke="#fff"
                                content={<CustomizedTreemapContent colors={COLORS} />}
                            >
                                <Tooltip content={<CustomTooltip totalValue={data.summary.total_value} />} />
                            </Treemap>
                        </ResponsiveContainer>
                    </div>
                </div>
            </div>

            {/* Detailed Allocation Table */}
            <div className="glass-panel rounded-2xl overflow-hidden">
                <div className="p-6 border-b border-white/10">
                    <h3 className="text-lg font-bold">Sector Details</h3>
                </div>
                <div className="overflow-x-auto">
                    <table className="w-full text-left text-sm">
                        <thead className="glass-table-header text-gray-400 uppercase text-xs font-semibold">
                            <tr>
                                <th className="p-4">Sector</th>
                                <th className="p-4 text-right">Value (CAD)</th>
                                <th className="p-4 text-right">Weight</th>
                                <th className="p-4">Top Holding</th>
                            </tr>
                        </thead>
                        <tbody className="divide-y divide-white/5">
                            {sectorData.map((s, idx) => {
                                const sectorHoldings = data.holdings
                                    .filter(h => h.Sector === s.name)
                                    .sort((a, b) => b.Market_Value - a.Market_Value);
                                const top = sectorHoldings[0];
                                const weight = (s.value / data.summary.total_value) * 100;

                                return (
                                    <tr key={s.name} className="hover:bg-white/5 transition-colors">
                                        <td className="p-4 font-medium flex items-center gap-2">
                                            <span className="w-3 h-3 rounded-full" style={{ backgroundColor: COLORS[idx % COLORS.length] }}></span>
                                            {s.name}
                                        </td>
                                        <td className="p-4 text-right font-mono">${s.value.toLocaleString()}</td>
                                        <td className="p-4 text-right">{weight.toFixed(1)}%</td>
                                        <td className="p-4 text-gray-400">
                                            {top ? `${top.Symbol} (${((top.Market_Value / s.value) * 100).toFixed(0)}%)` : '-'}
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
