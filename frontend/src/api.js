// One small helper that talks to the backend and attaches the login token.
// Dev (npm run dev): backend on localhost:8000.
// Production build (served by the backend container itself): same origin, so no URL needed.
// Set VITE_API_URL only if you host the frontend somewhere else.
const BASE = import.meta.env.VITE_API_URL ?? (import.meta.env.DEV ? "http://localhost:8000" : "");

// NOTE: localStorage is simple but readable by any script on the page (XSS risk).
// Fine for a student project; mention this trade-off in your report.
export const getToken = () => localStorage.getItem("token");
export const setToken = (t) => localStorage.setItem("token", t);
export const clearToken = () => localStorage.removeItem("token");

export async function api(path, { method = "GET", body, auth = true } = {}) {
  const headers = { "Content-Type": "application/json" };
  const token = getToken();
  if (auth && token) headers.Authorization = `Bearer ${token}`;

  let res;
  try {
    res = await fetch(BASE + path, {
      method,
      headers,
      body: body ? JSON.stringify(body) : undefined,
    });
  } catch {
    throw Object.assign(new Error("Cannot reach the server. Is the backend running?"), { status: 0 });
  }

  const data = await res.json().catch(() => null);
  if (!res.ok) {
    const detail = data?.detail;
    const message =
      typeof detail === "string"
        ? detail
        : Array.isArray(detail)
        ? detail.map((d) => d.msg).join(", ")
        : "Request failed";
    throw Object.assign(new Error(message), { status: res.status });
  }
  return data;
}
