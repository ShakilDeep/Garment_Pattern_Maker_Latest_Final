import {useEffect, useState} from 'react';

const DEFAULT_PAGE = 'Measurements';

const pageFromHash = () => decodeURIComponent(location.hash.slice(1)) || DEFAULT_PAGE;

/** Current page kept in sync with the URL hash (back/forward and deep links). */
export function useHashPage() {
  const [page, setPage] = useState(pageFromHash);
  useEffect(() => {
    const listener = () => setPage(pageFromHash());
    window.addEventListener('hashchange', listener);
    return () => window.removeEventListener('hashchange', listener);
  }, []);
  return [page, setPage] as const;
}
