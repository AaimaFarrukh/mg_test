const API = process.env.NEXT_PUBLIC_API_URL || "http://localhost:8000";

export async function api(path: string, options: RequestInit = {}) {
  const token = typeof window !== "undefined" ? localStorage.getItem("mg_token") : null;
  const response = await fetch(`${API}${path}`, {
    ...options,
    headers: { "Content-Type": "application/json", ...(token ? { Authorization: `Bearer ${token}` } : {}), ...options.headers }
  });
  if (!response.ok) throw new Error((await response.json().catch(() => null))?.detail || "Request failed");
  return response.json();
}

