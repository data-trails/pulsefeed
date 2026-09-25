import { useState, useEffect, useCallback } from 'react';

async function readJson(name, signal) {
  const response = await fetch(`${import.meta.env.BASE_URL}${name}`, { signal, cache: 'no-store' });
  if (!response.ok) throw new Error(`${name} unavailable`);
  return response.json();
}

export function useFeed() {
  const [items, setItems] = useState([]);
  const [sourceStatus, setSourceStatus] = useState(null);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState(false);
  const [status, setStatus] = useState('Loading updates…');
  const [revision, setRevision] = useState(0);

  useEffect(() => {
    const controller = new AbortController();
    readJson('feed.json', controller.signal).then(data => {
      if (!Array.isArray(data) || data.some(item => !item || typeof item.id !== 'string' || typeof item.source !== 'string')) {
        throw new Error('Invalid feed');
      }
      if (controller.signal.aborted) return;
      const records = data.filter(item => !item.manual);
      setItems(records);
      setError(false);
      setStatus(records.length ? `${records.length} updates loaded.` : 'No updates available. Check Sources for collection results.');
    }).catch(() => {
      if (controller.signal.aborted) return;
      setError(true);
      setStatus('Could not refresh the feed. Previously loaded updates, if any, remain visible.');
    }).finally(() => {
      if (!controller.signal.aborted) setLoading(false);
    });
    readJson('source-status.json', controller.signal).then(data => {
      if (!controller.signal.aborted && Array.isArray(data?.sources)) setSourceStatus(data);
    }).catch(() => {
      if (!controller.signal.aborted) setSourceStatus(null);
    });
    return () => controller.abort();
  }, [revision]);

  const refresh = useCallback(() => {
    setLoading(true);
    setStatus('Refreshing updates…');
    setRevision(value => value + 1);
  }, []);

  return { items, loading, status, error, sourceStatus, refresh };
}
