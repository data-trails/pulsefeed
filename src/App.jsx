import React, { useState, useMemo } from 'react';
import {
  Rss, LayoutGrid, Heart, Calendar, Globe,
  X, RotateCcw, ExternalLink,
} from 'lucide-react';
import { useFeed } from './useFeed';
import { SOURCES } from './sources';

// ---------------------------------------------------------------------------
// Color system — deterministic per source name
// ---------------------------------------------------------------------------

const PALETTE = [
  '#3b82f6', '#10b981', '#8b5cf6', '#f59e0b', '#ef4444',
  '#06b6d4', '#f97316', '#84cc16', '#ec4899', '#14b8a6',
  '#6366f1', '#d97706',
];

function sourceColor(name) {
  let h = 0;
  for (let i = 0; i < name.length; i++) h = (h * 31 + name.charCodeAt(i)) & 0xffff;
  return PALETTE[h % PALETTE.length];
}

// ---------------------------------------------------------------------------
// Topic classification (client-side mirror of scraper logic)
// ---------------------------------------------------------------------------

const ZONING_KW = [
  'zoning', 'rezoning', 'rezone', 'variance', 'ordinance', 'conditional use',
  'special use', 'site plan', 'overlay', 'setback', 'land use', 'master plan',
  'special land use', 'text amendment', 'zba', 'zoning board',
];
const HOUSING_KW = [
  'housing', 'residential', 'apartment', 'dwelling', 'affordable', 'subdivision',
  'plat', 'condominium', 'condo', 'single family', 'multifamily', 'multi-family',
  'duplex', 'accessory dwelling', 'adu', 'short-term rental', 'str', 'townhouse',
  'senior housing', 'mixed use',
];
const INDUSTRIAL_KW = [
  'industrial', 'warehouse', 'manufacturing', 'logistics', 'commercial',
  'business park', 'distribution', 'storage', 'factory', 'data center',
  'solar', 'wind', 'energy', 'utility', 'mining', 'gravel', 'aggregate',
  'renewable',
];

function getTopics(item) {
  const scraperTopics = item.topics;
  if (Array.isArray(scraperTopics) && scraperTopics.length > 0) return scraperTopics;
  const t = [item.title, item.summary, item.pdfItems].filter(Boolean).join(' ').toLowerCase();
  return [
    ...(ZONING_KW.some(k => t.includes(k)) ? ['Zoning'] : []),
    ...(HOUSING_KW.some(k => t.includes(k)) ? ['Housing'] : []),
    ...(INDUSTRIAL_KW.some(k => t.includes(k)) ? ['Industrial'] : []),
  ];
}

// Filter pdfItems lines to topic-relevant ones (client-side)
function filterPdfItems(pdfItems) {
  if (!pdfItems) return '';
  const lines = pdfItems.split('\n').filter(Boolean);
  const relevant = lines.filter(l => {
    const t = l.toLowerCase();
    return [...ZONING_KW, ...HOUSING_KW, ...INDUSTRIAL_KW].some(k => t.includes(k));
  });
  return (relevant.length > 0 ? relevant : lines).join('\n');
}

// ---------------------------------------------------------------------------
// Shared small components
// ---------------------------------------------------------------------------

const TOPIC_STYLE = {
  Zoning:   { bg: '#eff6ff', text: '#1d4ed8', border: '#bfdbfe' },
  Housing:  { bg: '#f0fdf4', text: '#166534', border: '#bbf7d0' },
  Industrial:{ bg: '#fffbeb', text: '#92400e', border: '#fde68a' },
};

function TopicTag({ label }) {
  const s = TOPIC_STYLE[label] || { bg: '#f1f5f9', text: '#475569', border: '#e2e8f0' };
  return (
    <span className="text-[10px] font-bold px-2 py-0.5 rounded-full border"
          style={{ background: s.bg, color: s.text, borderColor: s.border }}>
      {label}
    </span>
  );
}

function StatusTag({ label }) {
  const color = label === 'Upcoming' ? 'bg-blue-50 text-blue-700' : 'bg-slate-100 text-slate-500';
  return <span className={`text-[10px] font-bold px-2 py-0.5 rounded-full ${color}`}>{label}</span>;
}

// ---------------------------------------------------------------------------
// FeedCard — scrolling card with save/dismiss
// ---------------------------------------------------------------------------

function FeedCard({ item, onSave, onDismiss, isSaved }) {
  const color = sourceColor(item.source);
  const topics = getTopics(item);
  const pdfLines = filterPdfItems(item.pdfItems).split('\n').filter(Boolean);

  return (
    <div className="bg-white rounded-2xl shadow-sm border border-slate-100 overflow-hidden">
      <div className="h-1" style={{ background: color }} />
      <div className="p-5">
        {/* Header */}
        <div className="flex justify-between items-start mb-2">
          <span className="text-[10px] font-black uppercase tracking-widest text-slate-400">
            {item.county} County
          </span>
          {item.dateDisplay && (
            <span className="text-xs font-semibold" style={{ color }}>{item.dateDisplay}</span>
          )}
        </div>

        {/* Tags */}
        {(item.tag || topics.length > 0) && (
          <div className="flex gap-1.5 flex-wrap mb-3">
            {item.tag && <StatusTag label={item.tag} />}
            {topics.map(t => <TopicTag key={t} label={t} />)}
          </div>
        )}

        {/* Source + title */}
        <p className="text-xs text-slate-400 mb-1">{item.source}</p>
        <h3 className="font-bold text-slate-900 mb-3 leading-snug">{item.title}</h3>

        {/* Summary */}
        {item.summary && (
          <p className="text-sm text-slate-600 leading-relaxed mb-3">{item.summary}</p>
        )}

        {/* PDF agenda items */}
        {pdfLines.length > 0 && (
          <div className="bg-slate-50 rounded-xl p-3 mb-3 border border-slate-100">
            <p className="text-[10px] font-bold uppercase tracking-widest text-slate-400 mb-2">
              Agenda Items
            </p>
            <ul className="space-y-1">
              {pdfLines.map((line, i) => (
                <li key={i} className="text-xs text-slate-600 flex gap-2">
                  <span className="text-slate-300 shrink-0 mt-0.5">•</span>
                  <span>{line}</span>
                </li>
              ))}
            </ul>
          </div>
        )}

        {/* Link */}
        {item.link && item.link !== '#' && (
          <a href={item.link} target="_blank" rel="noopener noreferrer"
             className="text-xs font-medium hover:underline flex items-center gap-1 mb-4"
             style={{ color }}>
            Open source <ExternalLink size={10} />
          </a>
        )}

        {/* Actions */}
        <div className="flex gap-2 pt-3 border-t border-slate-100">
          <button
            onClick={onDismiss}
            className="flex-1 py-2.5 rounded-xl border border-slate-200 text-slate-400 text-sm font-medium hover:bg-red-50 hover:text-red-500 hover:border-red-200 transition-all flex items-center justify-center gap-1.5"
          >
            <X size={14} /> Dismiss
          </button>
          <button
            onClick={onSave}
            className="flex-1 py-2.5 rounded-xl text-sm font-medium flex items-center justify-center gap-1.5 transition-all"
            style={isSaved
              ? { background: '#f0fdfa', color: '#0f766e', border: '1px solid #99f6e4' }
              : { background: color, color: '#fff' }
            }
          >
            <Heart size={14} fill={isSaved ? 'currentColor' : 'none'} />
            {isSaved ? 'Saved' : 'Save'}
          </button>
        </div>
      </div>
    </div>
  );
}

// ---------------------------------------------------------------------------
// Calendar view
// ---------------------------------------------------------------------------

function formatCalendarDate(dateStr) {
  const d = new Date(dateStr + 'T12:00:00');
  const today = new Date();
  today.setHours(0, 0, 0, 0);
  const target = new Date(dateStr + 'T00:00:00');
  const diff = Math.round((target - today) / 86400000);
  if (diff === 0) return 'Today';
  if (diff === 1) return 'Tomorrow';
  if (diff === -1) return 'Yesterday';
  return d.toLocaleDateString('en-US', { weekday: 'short', month: 'short', day: 'numeric' });
}

function CalendarView({ items }) {
  const today = new Date().toISOString().slice(0, 10);
  const datedItems = items.filter(i => i.date).sort((a, b) => a.date.localeCompare(b.date));
  const upcoming = datedItems.filter(i => i.date >= today);
  const recent = [...datedItems.filter(i => i.date < today)].reverse();

  function groupByDate(arr) {
    const map = {};
    arr.forEach(i => { (map[i.date] = map[i.date] || []).push(i); });
    return Object.entries(map);
  }

  function DateGroup({ date, entries }) {
    return (
      <div className="mb-4">
        <p className="text-xs font-bold uppercase tracking-widest text-slate-400 mb-2 px-1">
          {formatCalendarDate(date)}
        </p>
        <div className="space-y-2">
          {entries.map(item => {
            const color = sourceColor(item.source);
            const topics = getTopics(item);
            return (
              <div key={item.id}
                   className="bg-white rounded-xl border border-slate-100 p-3 flex gap-3 items-start">
                <div className="w-2.5 h-2.5 rounded-full shrink-0 mt-1"
                     style={{ background: color }} />
                <div className="min-w-0 flex-1">
                  <p className="text-[10px] text-slate-400 mb-0.5">{item.source}</p>
                  <p className="text-sm font-semibold text-slate-800 leading-snug mb-1.5">
                    {item.title}
                  </p>
                  <div className="flex gap-1 flex-wrap">
                    {item.tag && <StatusTag label={item.tag} />}
                    {topics.map(t => <TopicTag key={t} label={t} />)}
                  </div>
                </div>
                {item.link && item.link !== '#' && (
                  <a href={item.link} target="_blank" rel="noopener noreferrer"
                     className="shrink-0 text-slate-300 hover:text-slate-500 mt-0.5">
                    <ExternalLink size={14} />
                  </a>
                )}
              </div>
            );
          })}
        </div>
      </div>
    );
  }

  return (
    <div>
      {upcoming.length > 0 && (
        <section className="mb-6">
          <h2 className="font-bold text-slate-700 mb-3">Upcoming</h2>
          {groupByDate(upcoming).map(([date, entries]) => (
            <DateGroup key={date} date={date} entries={entries} />
          ))}
        </section>
      )}
      {recent.length > 0 && (
        <section>
          <h2 className="font-bold text-slate-700 mb-3">Recent</h2>
          {groupByDate(recent).map(([date, entries]) => (
            <DateGroup key={date} date={date} entries={entries} />
          ))}
        </section>
      )}
      {upcoming.length === 0 && recent.length === 0 && (
        <div className="bg-white rounded-2xl border border-dashed border-slate-200 p-10 text-center text-slate-400">
          <Calendar size={28} className="mx-auto mb-3 text-slate-300" />
          <p className="font-bold text-slate-600">No dated items found</p>
          <p className="text-sm mt-1">Items with meeting dates will appear here.</p>
        </div>
      )}
    </div>
  );
}

// ---------------------------------------------------------------------------
// Sources view
// ---------------------------------------------------------------------------

function SourcesView() {
  const byCounty = useMemo(() => {
    const map = {};
    SOURCES.forEach(s => { (map[s.county] = map[s.county] || []).push(s); });
    return map;
  }, []);

  return (
    <div>
      <p className="text-sm text-slate-500 mb-4">
        {SOURCES.length} sources scraped daily across Allegan and Ottawa counties.
      </p>
      {Object.entries(byCounty).map(([county, sources]) => (
        <div key={county} className="mb-6">
          <h2 className="font-bold text-slate-700 mb-2">{county} County</h2>
          <div className="bg-white rounded-2xl border border-slate-100 overflow-hidden divide-y divide-slate-100">
            {sources.map(s => (
              <a key={s.name} href={s.url} target="_blank" rel="noopener noreferrer"
                 className="flex items-center gap-3 px-4 py-3 hover:bg-slate-50 transition-colors group">
                <div className="w-2.5 h-2.5 rounded-full shrink-0"
                     style={{ background: sourceColor(s.name) }} />
                <span className="text-sm text-slate-700 flex-1">{s.name}</span>
                <ExternalLink size={12} className="text-slate-300 group-hover:text-slate-400 shrink-0" />
              </a>
            ))}
          </div>
        </div>
      ))}
    </div>
  );
}

// ---------------------------------------------------------------------------
// Saved view
// ---------------------------------------------------------------------------

function SavedView({ items, onUnsave }) {
  if (items.length === 0) {
    return (
      <div className="bg-white rounded-2xl border border-dashed border-slate-200 p-10 text-center text-slate-400">
        <Heart size={28} className="mx-auto mb-3 text-slate-300" />
        <p className="font-bold text-slate-600">No saved items yet</p>
        <p className="text-sm mt-1">Save cards from the feed to find them here.</p>
      </div>
    );
  }
  return (
    <div className="space-y-4">
      {items.map(item => {
        const color = sourceColor(item.source);
        const topics = getTopics(item);
        return (
          <div key={item.id}
               className="bg-white rounded-2xl border border-slate-100 overflow-hidden">
            <div className="h-1" style={{ background: color }} />
            <div className="p-4 flex gap-3 items-start">
              <div className="flex-1 min-w-0">
                <p className="text-[10px] text-slate-400 mb-0.5">{item.source}</p>
                <a href={item.link} target="_blank" rel="noopener noreferrer"
                   className="font-bold text-sm text-slate-900 hover:underline leading-snug block mb-1.5">
                  {item.title}
                </a>
                <div className="flex gap-1 flex-wrap">
                  {item.dateDisplay && (
                    <span className="text-[10px] text-slate-400">{item.dateDisplay}</span>
                  )}
                  {topics.map(t => <TopicTag key={t} label={t} />)}
                </div>
              </div>
              <button onClick={() => onUnsave(item)}
                      className="shrink-0 text-slate-300 hover:text-red-400 transition-colors mt-0.5">
                <X size={16} />
              </button>
            </div>
          </div>
        );
      })}
    </div>
  );
}

// ---------------------------------------------------------------------------
// localStorage helpers
// ---------------------------------------------------------------------------

function getSavedItems() {
  try { return JSON.parse(localStorage.getItem('savedPlanningUpdates')) || []; }
  catch { return []; }
}

// ---------------------------------------------------------------------------
// App
// ---------------------------------------------------------------------------

const TABS = [
  { id: 'feed',     label: 'Feed',     Icon: LayoutGrid },
  { id: 'calendar', label: 'Calendar', Icon: Calendar   },
  { id: 'saved',    label: 'Saved',    Icon: Heart      },
  { id: 'sources',  label: 'Sources',  Icon: Globe      },
];

export default function App() {
  const { items, loading, status, refresh } = useFeed();
  const [dismissedIds, setDismissedIds] = useState(() => new Set());
  const [savedItems, setSavedItems] = useState(getSavedItems);
  const [activeTab, setActiveTab] = useState('feed');

  const savedIds = useMemo(() => new Set(savedItems.map(i => i.id)), [savedItems]);
  const visibleItems = useMemo(
    () => items.filter(i => !dismissedIds.has(i.id)),
    [items, dismissedIds],
  );

  function dismiss(item) {
    setDismissedIds(prev => new Set([...prev, item.id]));
  }

  function save(item) {
    setSavedItems(prev => {
      if (prev.some(s => s.id === item.id)) return prev;
      const next = [item, ...prev];
      localStorage.setItem('savedPlanningUpdates', JSON.stringify(next));
      return next;
    });
    dismiss(item);
  }

  function unsave(item) {
    setSavedItems(prev => {
      const next = prev.filter(s => s.id !== item.id);
      localStorage.setItem('savedPlanningUpdates', JSON.stringify(next));
      return next;
    });
  }

  return (
    <div className="min-h-screen bg-[#f8f7f2] text-slate-900 font-sans">

      {/* Nav */}
      <nav className="sticky top-0 z-10 bg-white border-b border-slate-100 shadow-sm">
        <div className="max-w-2xl mx-auto px-4 py-3 flex items-center justify-between">
          <div className="flex items-center gap-2.5">
            <div className="bg-blue-600 p-1.5 rounded-lg text-white">
              <Rss size={18} />
            </div>
            <div>
              <h1 className="font-bold text-base leading-none text-blue-900">PulseFeed</h1>
              <p className="text-[9px] uppercase tracking-widest text-slate-400">Lakeshore Advantage</p>
            </div>
          </div>
          <div className="flex gap-1">
            {TABS.map(({ id, label, Icon }) => (
              <button
                key={id}
                onClick={() => setActiveTab(id)}
                className={`flex items-center gap-1.5 px-3 py-1.5 rounded-lg text-xs font-semibold transition-colors ${
                  activeTab === id
                    ? 'bg-blue-50 text-blue-700'
                    : 'text-slate-500 hover:text-slate-700 hover:bg-slate-50'
                }`}
              >
                <Icon size={14} />
                <span className="hidden sm:inline">{label}</span>
              </button>
            ))}
          </div>
        </div>
      </nav>

      <main className="max-w-2xl mx-auto px-4 py-6">

        {/* Feed */}
        {activeTab === 'feed' && (
          <>
            <div className="flex items-center justify-between mb-4">
              <p className="text-xs text-slate-400">{status}</p>
              <button onClick={refresh}
                      className="flex items-center gap-1 text-xs text-blue-600 font-medium hover:underline">
                <RotateCcw size={12} /> Refresh
              </button>
            </div>

            {loading ? (
              <div className="bg-white rounded-2xl border border-slate-100 p-10 text-center text-slate-400">
                Loading updates…
              </div>
            ) : visibleItems.length > 0 ? (
              <div className="space-y-4">
                {visibleItems.map(item => (
                  <FeedCard
                    key={item.id}
                    item={item}
                    onSave={() => save(item)}
                    onDismiss={() => dismiss(item)}
                    isSaved={savedIds.has(item.id)}
                  />
                ))}
              </div>
            ) : (
              <div className="bg-white rounded-2xl border-2 border-dashed border-slate-200 p-10 text-center text-slate-400">
                <p className="font-bold text-lg mb-1 text-slate-600">All caught up</p>
                <p className="text-sm">Refresh for new updates or review saved items.</p>
                <button
                  onClick={() => setDismissedIds(new Set())}
                  className="mt-4 text-sm text-blue-600 font-medium hover:underline"
                >
                  Show dismissed items
                </button>
              </div>
            )}
          </>
        )}

        {/* Calendar */}
        {activeTab === 'calendar' && <CalendarView items={items} />}

        {/* Saved */}
        {activeTab === 'saved' && <SavedView items={savedItems} onUnsave={unsave} />}

        {/* Sources */}
        {activeTab === 'sources' && <SourcesView />}

      </main>
    </div>
  );
}
