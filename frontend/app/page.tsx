
"use client";

import dynamic from 'next/dynamic';

const Dashboard = dynamic(() => import("@/components/Dashboard"), { ssr: false });

export default function Home() {
  return (
    <main className="min-h-screen selection:bg-blue-500 selection:text-white">
      <Dashboard />
    </main>
  );
}
