"use client";

import React, { createContext, useContext, useState, useEffect, useCallback } from 'react';
import { API_BASE_URL } from './api';

interface PortfolioContextType {
    data: any;
    dividends: any;
    tickerPerf: any;
    history: any;
    symbolAccounts: any;
    allTransactions: any;
    allRealized: any;
    allClosedTrades: any;
    fileStatus: { portfolio_csv: boolean; portfolio_resp_csv: boolean };
    loading: boolean;
    error: any;
    category: string;
    setCategory: (cat: string) => void;
    refresh: (forceRefresh?: boolean) => Promise<void>;
}

const PortfolioContext = createContext<PortfolioContextType | undefined>(undefined);

export function PortfolioProvider({ children }: { children: React.ReactNode }) {
    const [data, setData] = useState<any>(null);
    const [dividends, setDividends] = useState<any>(null);
    const [tickerPerf, setTickerPerf] = useState<any>(null);
    const [history, setHistory] = useState<any>(null);
    const [symbolAccounts, setSymbolAccounts] = useState<any>(null);
    const [allTransactions, setAllTransactions] = useState<any>(null);
    const [allRealized, setAllRealized] = useState<any>(null);
    const [allClosedTrades, setAllClosedTrades] = useState<any>(null);
    const [fileStatus, setFileStatus] = useState<any>({ portfolio_csv: true, portfolio_resp_csv: true });
    const [loading, setLoading] = useState(true);
    const [error, setError] = useState<any>(null);
    const [category, setCategory] = useState("ALL");

    const fetchData = useCallback(async (forceRefresh = false) => {
        try {
            setLoading(true);

            if (forceRefresh) {
                await fetch(`${API_BASE_URL}/api/sync`, { method: "POST" });
            }

            // Fetch ALL data once
            const [portRes, divRes, perfRes, histRes, accRes, txRes, realRes, closedRes, healthRes] = await Promise.all([
                fetch(`${API_BASE_URL}/api/portfolio`),
                fetch(`${API_BASE_URL}/api/dividends`),
                fetch(`${API_BASE_URL}/api/ticker-performance`),
                fetch(`${API_BASE_URL}/api/performance`),
                fetch(`${API_BASE_URL}/api/symbol-accounts`),
                fetch(`${API_BASE_URL}/api/transactions`),
                fetch(`${API_BASE_URL}/api/realized-pnl`),
                fetch(`${API_BASE_URL}/api/closed-trades`),
                fetch(`${API_BASE_URL}/api/health`)
            ]);

            if (!portRes.ok) throw new Error("Failed to fetch portfolio");

            const [p, d, t, h, a, tx, r, c, health] = await Promise.all([
                portRes.json(),
                divRes.json(),
                perfRes.json(),
                histRes.json(),
                accRes.json(),
                txRes.json(),
                realRes.json(),
                closedRes.json(),
                healthRes.json()
            ]);

            setData(p);
            setDividends(d);
            setTickerPerf(t);
            setHistory(h);
            setSymbolAccounts(a);
            setAllTransactions(tx);
            setAllRealized(r);
            setAllClosedTrades(c);
            setFileStatus(health.file_status || { portfolio_csv: true, portfolio_resp_csv: true });
            setError(null);
            console.log("DEBUG: All Portfolio data pre-loaded successfully");
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

    const refresh = (forceRefresh = false) => fetchData(forceRefresh);

    return (
        <PortfolioContext.Provider value={{ 
            data, dividends, tickerPerf, history, symbolAccounts, 
            allTransactions, allRealized, allClosedTrades, fileStatus,
            loading, error, category, setCategory, refresh 
        }}>
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
