export async function api<T>(path: string, method = 'GET', data?: unknown): Promise<T> {
  const form = data instanceof FormData;
  const response = await fetch('/api/v1' + path, {
    method,
    headers: form ? undefined : {'Content-Type': 'application/json'},
    body: data === undefined ? undefined : form ? data : JSON.stringify(data),
  });
  if (!response.ok) {
    const error = await response.json().catch(() => ({message: 'The server could not complete this request.'}));
    throw new Error(error.message || 'Request failed');
  }
  return response.json() as Promise<T>;
}

/** Adapter: turn a Blob into a reliable browser file save across Chromium/Safari. */
export function saveBlobAsFile(blob: Blob, name: string) {
  const url = URL.createObjectURL(blob);
  const link = document.createElement('a');
  link.href = url;
  link.download = name;
  link.rel = 'noopener';
  link.style.display = 'none';
  document.body.appendChild(link);
  link.click();
  // Deferred cleanup — synchronous remove cancels the download in some browsers.
  window.setTimeout(() => {
    link.remove();
    URL.revokeObjectURL(url);
  }, 1500);
}

export async function download(path: string, name: string) {
  const response = await fetch('/api/v1' + path);
  if (!response.ok) {
    const error = await response.json().catch(() => ({message: 'Download failed.'}));
    throw new Error(error.message || 'Download failed.');
  }
  saveBlobAsFile(await response.blob(), name);
}
