/** First-paint startup: always land on the Projects picker. */
export function bootProjectsDialog(): string {
  return 'projects';
}

export function shouldRestoreLastProject(): boolean {
  return false;
}
