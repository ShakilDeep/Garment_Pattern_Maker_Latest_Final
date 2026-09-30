/** Command helper: block navigation when measurement drafts are dirty. */

export function confirmLeaveIfDirty(dirty: boolean, confirmFn = window.confirm): boolean {
  if (!dirty) return true;
  return confirmFn('You have unsaved measurement edits. Leave this page anyway?');
}

export function guardedGo(
  dirty: boolean,
  page: string,
  go: (page: string) => void,
  confirmFn = window.confirm,
): boolean {
  if (!confirmLeaveIfDirty(dirty, confirmFn)) return false;
  go(page);
  return true;
}
