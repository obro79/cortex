export type ApiFailure = { detail?: string };

export async function cortexApi<T>(path: string, init?: RequestInit): Promise<T> {
  const response = await fetch(`/api/cortex/${path.replace(/^\//, "")}`, {
    ...init,
    headers: { "content-type": "application/json", ...init?.headers },
    cache: "no-store",
  });
  const payload = (await response.json().catch(() => ({}))) as T & ApiFailure;
  if (!response.ok) throw new Error(payload.detail ?? `Request failed (${response.status})`);
  return payload;
}
