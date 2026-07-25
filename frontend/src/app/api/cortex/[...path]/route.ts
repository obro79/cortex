import { NextRequest, NextResponse } from "next/server";

const LOCAL_API_ORIGIN = process.env.CORTEX_LOCAL_API_ORIGIN ?? "http://127.0.0.1:8000";
const MAX_POST_BODY_BYTES = 64 * 1024;
type RouteRule = { method: "GET" | "POST"; path: RegExp };

// This is intentionally a small, same-origin BFF allowlist. The browser never
// receives connector, database, vector-store, or provider credentials.
const ALLOWED_ROUTES: RouteRule[] = [
  { method: "GET", path: /^health\/(live|ready)$/ },
  { method: "POST", path: /^v1\/context\/task-context$/ },
  { method: "GET", path: /^v1\/context\/evidence\/[A-Za-z0-9_-]+$/ },
  { method: "GET", path: /^dev\/state$/ },
  { method: "GET", path: /^dev\/pipeline\/runs\/[A-Za-z0-9_-]+$/ },
  { method: "GET", path: /^dev\/evidence-packs\/[A-Za-z0-9_-]+$/ },
];

// Keep the browser-to-backend boundary deliberately narrow. In particular, do
// not forward internal actor headers or the browser's entire cookie jar.
const FORWARDED_HEADERS = [
  "authorization",
  "x-cortex-workspace-id",
  "x-cortex-auth-email",
  "x-cortex-auth-display-name",
  "x-cortex-public-session-id",
  "x-request-id",
] as const;

function isAllowed(method: string, path: string) {
  return ALLOWED_ROUTES.some((rule) => rule.method === method && rule.path.test(path));
}

function requestHeaders(request: NextRequest, includeBody: boolean) {
  const headers = new Headers();
  if (includeBody) headers.set("content-type", request.headers.get("content-type") ?? "application/json");
  for (const name of FORWARDED_HEADERS) {
    const value = request.headers.get(name);
    if (value) headers.set(name, value);
  }
  return headers;
}

function boundedBody(stream: ReadableStream<Uint8Array> | null) {
  let exceeded = false;
  let size = 0;
  return {
    exceeded: () => exceeded,
    body: stream?.pipeThrough(new TransformStream<Uint8Array, Uint8Array>({
      transform(chunk, controller) {
        size += chunk.byteLength;
        if (size > MAX_POST_BODY_BYTES) {
          exceeded = true;
          controller.error(new Error("request body too large"));
          return;
        }
        controller.enqueue(chunk);
      },
    })),
  };
}

async function proxy(request: NextRequest, params: Promise<{ path: string[] }>) {
  const { path: parts } = await params;
  const path = parts.join("/");
  const method = request.method as RouteRule["method"];
  if (!isAllowed(method, path)) return NextResponse.json({ detail: "Cortex local route is not allowed." }, { status: 404 });

  let target: URL;
  try { target = new URL(`/${path}`, LOCAL_API_ORIGIN); }
  catch { return NextResponse.json({ detail: "CORTEX_LOCAL_API_ORIGIN is invalid." }, { status: 500 }); }

  const declaredLength = Number(request.headers.get("content-length"));
  if (method === "POST" && Number.isFinite(declaredLength) && declaredLength > MAX_POST_BODY_BYTES) {
    return NextResponse.json({ detail: "Cortex request body is too large." }, { status: 413 });
  }

  const forwarded = method === "POST" ? boundedBody(request.body) : undefined;

  try {
    const response = await fetch(target, {
      method,
      headers: requestHeaders(request, method === "POST"),
      body: forwarded?.body,
      // Undici requires this when the request body is a ReadableStream.
      duplex: "half",
      cache: "no-store",
      signal: AbortSignal.timeout(8_000),
    } as RequestInit & { duplex: "half" });
    return new NextResponse(await response.text(), {
      status: response.status,
      headers: { "cache-control": "no-store", "content-type": response.headers.get("content-type") ?? "application/json; charset=utf-8" },
    });
  } catch {
    if (forwarded?.exceeded()) return NextResponse.json({ detail: "Cortex request body is too large." }, { status: 413 });
    return NextResponse.json({ detail: "Local Cortex API is unavailable. Start it and retry." }, { status: 503, headers: { "cache-control": "no-store" } });
  }
}

export async function GET(request: NextRequest, context: { params: Promise<{ path: string[] }> }) { return proxy(request, context.params); }
export async function POST(request: NextRequest, context: { params: Promise<{ path: string[] }> }) { return proxy(request, context.params); }
