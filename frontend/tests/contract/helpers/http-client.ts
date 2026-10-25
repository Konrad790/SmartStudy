export async function apiFetch(path: string, init?: RequestInit) {
  return fetch(`http://localhost:3000${path}`, init);
}
