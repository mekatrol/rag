const base =
  import.meta.env.VITE_API_BASE?.replace(/\/$/, "") || "http://localhost:8000";

async function http(method, path, body) {
  const res = await fetch(`${base}${path}`, {
    method,
    headers: body ? { "Content-Type": "application/json" } : undefined,
    body: body ? JSON.stringify(body) : undefined,
  });
  if (!res.ok) {
    const t = await res.text().catch(() => "");
    throw new Error(`${res.status} ${res.statusText} ${t}`);
  }
  const ct = res.headers.get("content-type") || "";
  return ct.includes("application/json") ? res.json() : res.text();
}

export const api = {
  health: () => http("GET", "/health"),
  ingest: (collection = "docs") =>
    http("POST", `/ingest?collection=${encodeURIComponent(collection)}`),
  query: (query, top_k = 4, collection = "docs") =>
    http("POST", "/query", { query, top_k, collection }),
};
