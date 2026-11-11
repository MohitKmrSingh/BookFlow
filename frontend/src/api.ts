const API = (import.meta.env.VITE_API_URL || "http://127.0.0.1:8000").replace(/\/$/, "");
export function getToken() { return localStorage.getItem("bookflow_token"); }
export function setToken(token:string|null) { token ? localStorage.setItem("bookflow_token", token) : localStorage.removeItem("bookflow_token"); }
export async function request<T>(path:string, options:RequestInit = {}):Promise<T> {
  const token = getToken();
  const headers = new Headers(options.headers);
  if (
  options.body &&
  !(options.body instanceof FormData) &&
  !(options.body instanceof URLSearchParams) &&
  !headers.has("Content-Type")
) {
  headers.set("Content-Type", "application/json");
}
  if (token) headers.set("Authorization", `Bearer ${token}`);
  let response:Response;
  try { response = await fetch(`${API}${path}`, { ...options, headers }); }
  catch { throw new Error("Cannot reach BookFlow API. Check that the backend is running and VITE_API_URL is correct."); }
  if (!response.ok) {
    let message = `Request failed (${response.status})`;
    try { const body = await response.json(); message = body.detail || message; } catch { /* no JSON response */ }
    throw new Error(typeof message === "string" ? message : JSON.stringify(message));
  }
  if (response.status === 204) return undefined as T;
  return response.json() as Promise<T>;
}
export const json = (method:string, data?:unknown):RequestInit => ({ method, body: data === undefined ? undefined : JSON.stringify(data) });
