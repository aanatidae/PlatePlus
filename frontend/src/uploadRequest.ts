// Keep only a content hash and random event key in this browser session, never
// the image or filename. An uncertain response can be retried after a refresh.
export const UPLOAD_REQUEST_TIMEOUT_MS = 150_000;

export type UploadRequestKey = { key: string; storageKey: string };

export async function uploadRequestKey(file: File, locationId: string): Promise<UploadRequestKey> {
  const bytes = await new Promise<ArrayBuffer>((resolve, reject) => {
    const reader = new FileReader();
    reader.onerror = () => reject(new Error("The selected image could not be read. Choose it again."));
    reader.onload = () => resolve(reader.result as ArrayBuffer);
    reader.readAsArrayBuffer(file);
  });
  const digest = await crypto.subtle.digest("SHA-256", bytes);
  const fingerprint = Array.from(new Uint8Array(digest), value => value.toString(16).padStart(2, "0")).join("");
  const storageKey = `plateplus.pending-upload.v1:${locationId}:${fingerprint}`;
  const key = crypto.randomUUID();
  try {
    const previous = sessionStorage.getItem(storageKey);
    if (previous) return { storageKey, key: previous };
    sessionStorage.setItem(storageKey, key);
  } catch { /* In-memory component state still protects retries when storage is disabled. */ }
  return { storageKey, key };
}

export function completeUploadRequest({ storageKey, key }: UploadRequestKey) {
  try {
    if (sessionStorage.getItem(storageKey) === key) sessionStorage.removeItem(storageKey);
  } catch { /* Private browsing may deny storage access. */ }
}
