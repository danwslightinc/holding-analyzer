"use client";

import React, { createContext, useContext, useState, useEffect, useCallback } from 'react';
import { API_BASE_URL } from './api';

interface PortfolioContextType {
    data: any;
    dividends: any;
    tickerPerf: any;
    history: any;
    symbolAccounts: any;
    loading: boolean;
    error: any;
    refresh: (forceRefresh?: boolean) => Promise<void>;
}

const PortfolioContext = createContext<PortfolioContextType | undefined>(undefined);

export function PortfolioProvider({ children }: { children: React.ReactNode }) {
    const [data, setData] = useState<any>(null);
    const [dividends, setDividends] = useState<any>(null);
    const [tickerPerf, setTickerPerf] = useState<any>(null);
    const [history, setHistory] = useState<any>(null);
    const [symbolAccounts, setSymbolAccounts] = useState<any>(null);
    const [loading, setLoading] = useState(true);
    const [error, setError] = useState<any>(null);

    const fetchData = useCallback(async (forceRefresh = false) => {
        try {
            setLoading(true);

            if (forceRefresh) {
                await fetch(`${API_BASE_URL}/api/sync`, { method: "POST" });
            }

            const [portRes, divRes, perfRes, histRes, accRes] = await Promise.all([
                fetch(`${API_BASE_URL}/api/portfolio`),
                fetch(`${API_BASE_URL}/api/dividends`),
                fetch(`${API_BASE_URL}/api/ticker-performance`),
                fetch(`${API_BASE_URL}/api/performance`),
                fetch(`${API_BASE_URL}/api/symbol-accounts`)
            ]);

            if (!portRes.ok) throw new Error("Failed to fetch portfolio");

            const [p, d, t, h, a] = await Promise.all([
                portRes.json(),
                divRes.json(),
                perfRes.json(),
                histRes.json(),
                accRes.json()
            ]);

            setData(p);
            setDividends(d);
            setTickerPerf(t);
            setHistory(h);
            setSymbolAccounts(a);
            setError(null);
        } catch (err) {
            console.error("Context fetch error:", err);
            setError(err);
        } finally {
            setLoading(false);
        }
    }, []);

    useEffect(() => {
        fetchData(false);
    }, [fetchData]);

    return (
        <PortfolioContext.Provider value={{ data, dividends, tickerPerf, history, symbolAccounts, loading, error, refresh: fetchData }}>
            {children}
        </PortfolioContext.Provider>
    );
}

export function usePortfolio() {
    const context = useContext(PortfolioContext);
    if (context === undefined) {
        throw new Error('usePortfolio must be used within a PortfolioProvider');
    }
    return context;
}
