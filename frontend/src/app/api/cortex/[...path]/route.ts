import { NextRequest, NextResponse } from "next/server";

const LOCAL_API_ORIGIN = process.env.CORTEX_LOCAL_API_ORIGIN ?? "http://127.0.0.1:8000";
type RouteRule = { method: "GET" | "POST"; path: RegExp };

// This is intentionally a small, same-origin BFF allowlist. The browser never
// receives connector, database, vector-store, or provider credentials.
const ALLOWED_ROUTES: RouteRule[] = [
  { method: "GET", path: /^health\/(live|ready)$/ },
  { method: "POST", path: /^v1\/task-context$/ },
  { method: "GET", path: /^v1\/task-context\/evidence\/[A-Za-z0-9_-]+$/ },
  { method: "GET", path: /^dev\/state$/ },
];

function isAllowed(method: string, path: string) {
  return ALLOWED_ROUTES.some((rule) => rule.method === method && rule.path.test(path));
}

async function proxy(request: NextRequest, params: Promise<{ path: string[] }>) {
  const { path: parts } = await params;
  const path = parts.join("/");
  const method = request.method as RouteRule["method"];
  if (!isAllowed(method, path)) return NextResponse.json({ detail: "Cortex local route is not allowed." }, { status: 404 });

  let target: URL;
  try { target = new URL(`/${path}`, LOCAL_API_ORIGIN); }
  catch { return NextResponse.json({ detail: "CORTEX_LOCAL_API_ORIGIN is invalid." }, { status: 500 }); }

  try {
    const body = method === "POST" ? await request.text() : undefined;
    const response = await fetch(target, {
      method,
      headers: body ? { "content-type": request.headers.get("content-type") ?? "application/json" } : undefined,
      body,
      cache: "no-store",
      signal: AbortSignal.timeout(8_000),
    });
    return new NextResponse(await response.text(), {
      status: response.status,
      headers: { "cache-control": "no-store", "content-type": response.headers.get("content-type") ?? "application/json; charset=utf-8" },
    });
  } catch {
    return NextResponse.json({ detail: "Local Cortex API is unavailable. Start it and retry." }, { status: 503, headers: { "cache-control": "no-store" } });
  }
}

export async function GET(request: NextRequest, context: { params: Promise<{ path: string[] }> }) { return proxy(request, context.params); }
export async function POST(request: NextRequest, context: { params: Promise<{ path: string[] }> }) { return proxy(request, context.params); }
