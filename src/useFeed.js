import { useState, useEffect, useCallback } from 'react';

const SAMPLE_ITEMS = [
  {
    id: 'sample-1',
    county: 'Ottawa',
    source: 'Georgetown Charter Township Planning Commission',
    title: 'Public hearing scheduled at Georgetown Charter Township Planning Commission',
    date: '2026-05-20',
    dateDisplay: 'Wed, May 20',
    time: '7:00 PM',
    summary: 'Public hearing notice & legal review. Staff presentation.',
    details: '',
    link: 'https://www.gtwp.com/155/Planning-Commission',
    tag: 'Upcoming',
  },
  {
    id: 'sample-2',
    county: 'Ottawa',
    source: 'Holland Charter Township Planning Commission',
    title: 'Planning Commission agenda posted',
    date: '',
    dateDisplay: '',
    time: '',
    summary: 'A new agenda or packet may be available. Open the source to check for the latest meeting materials.',
    details: '',
    link: 'https://www.hct.holland.mi.us/agendas-minutes/planning-commission',
    tag: 'New',
  },
];

export function useFeed() {
  const [items, setItems] = useState([]);
  const [loading, setLoading] = useState(true);
  const [status, setStatus] = useState('Loading...');

  const load = useCallback(async () => {
    setLoading(true);
    setStatus('Refreshing updates...');
    try {
      const res = await fetch(`${import.meta.env.BASE_URL}feed.json`);
      if (!res.ok) throw new Error('Feed unavailable');
      const data = await res.json();
      if (Array.isArray(data) && data.length > 0) {
        setItems(data);
        setStatus(`${data.length} update${data.length === 1 ? '' : 's'} loaded.`);
      } else {
        setItems(SAMPLE_ITEMS);
        setStatus('No live updates yet — showing sample cards.');
      }
    } catch {
      setItems(SAMPLE_ITEMS);
      setStatus('Could not load feed — showing sample cards.');
    }
    setLoading(false);
  }, []);

  useEffect(() => { load(); }, [load]);

  return { items, loading, status, refresh: load };
}
