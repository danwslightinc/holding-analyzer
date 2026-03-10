import { NextResponse } from 'next/server';

export async function GET() {
  const apiUrl = process.env.NEXT_PUBLIC_API_URL || "http://127.0.0.1:8000";
  let backendHealth = {};
  
  try {
    const res = await fetch(`${apiUrl}/api/health`, { next: { revalidate: 0 } });
    if (res.ok) {
      backendHealth = await res.json();
    } else {
      backendHealth = { status: "error", code: res.status };
    }
  } catch (e: any) {
    backendHealth = { status: "unavailable", error: e.message };
  }

  return NextResponse.json(
    { 
      status: 'ok', 
      timestamp: new Date().toISOString(),
      service: 'holding-analyzer-frontend',
      backend: backendHealth
    },
    { status: 200 }
  );
}
