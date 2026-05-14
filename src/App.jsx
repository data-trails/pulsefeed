import React, { useState, useCallback, useRef, useEffect } from 'react';
import { Rss, LayoutGrid, Heart, BarChart3, X, ChevronDown, RotateCcw } from 'lucide-react';
import { useFeed } from './useFeed';

function getSavedItems() {
  try { return JSON.parse(localStorage.getItem('savedPlanningUpdates')) || []; }
  catch { return []; }
}

export default function App() {
  const { items, loading, status, refresh } = useFeed();
  const [currentIndex, setCurrentIndex] = useState(0);
  const [savedItems, setSavedItems] = useState(getSavedItems);
  const [activeTab, setActiveTab] = useState('feed');
  const [detailsOpen, setDetailsOpen] = useState(false);
  const cardRef = useRef(null);
  const drag = useRef({ active: false, startX: 0, dx: 0 });

  useEffect(() => { setCurrentIndex(0); setDetailsOpen(false); }, [items]);

  const currentItem = items[currentIndex];

  const dismiss = useCallback(() => {
    setCurrentIndex(i => i + 1);
    setDetailsOpen(false);
  }, []);

  const save = useCallback(() => {
    const item = items[currentIndex];
    if (!item) return;
    setSavedItems(prev => {
      if (prev.some(s => s.id === item.id)) return prev;
      const next = [item, ...prev];
      localStorage.setItem('savedPlanningUpdates', JSON.stringify(next));
      return next;
    });
    setCurrentIndex(i => i + 1);
    setDetailsOpen(false);
  }, [items, currentIndex]);

  const onPointerDown = useCallback((e) => {
    drag.current = { active: true, startX: e.clientX, dx: 0 };
    cardRef.current?.setPointerCapture(e.pointerId);
  }, []);

  const onPointerMove = useCallback((e) => {
    if (!drag.current.active) return;
    drag.current.dx = e.clientX - drag.current.startX;
    if (cardRef.current) {
      cardRef.current.style.transform = `translateX(${drag.current.dx}px) rotate(${drag.current.dx / 22}deg)`;
    }
  }, []);

  const onPointerUp = useCallback(() => {
    if (!drag.current.active) return;
    drag.current.active = false;
    const { dx } = drag.current;
    if (dx > 120) save();
    else if (dx < -120) dismiss();
    else if (cardRef.current) cardRef.current.style.transform = '';
    drag.current.dx = 0;
  }, [save, dismiss]);

  return (
    <div className="min-h-screen bg-[#f8f7f2] p-4 text-slate-900 font-sans">

      {/* Nav */}
      <nav className="max-w-4xl mx-auto flex items-center justify-between mb-8 bg-white p-4 rounded-2xl shadow-sm">
        <div className="flex items-center gap-3">
          <div className="bg-blue-600 p-2 rounded-lg text-white">
            <Rss size={24} />
          </div>
          <div>
            <h1 className="font-bold text-xl leading-none text-blue-900">PulseFeed</h1>
            <p className="text-[10px] uppercase tracking-widest text-slate-500">Lakeshore Advantage</p>
          </div>
        </div>
        <div className="flex gap-6 font-medium text-slate-600">
          {[
            { id: 'feed', label: 'Feed', Icon: LayoutGrid },
            { id: 'saved', label: 'Saved', Icon: Heart },
            { id: 'insights', label: 'Insights', Icon: BarChart3 },
          ].map(({ id, label, Icon }) => (
            <button
              key={id}
              onClick={() => setActiveTab(id)}
              className={`flex items-center gap-2 px-1 transition-colors ${
                activeTab === id
                  ? 'text-blue-600 border-b-2 border-blue-600'
                  : 'hover:text-blue-600'
              }`}
            >
              <Icon size={18} /> {label}
            </button>
          ))}
        </div>
      </nav>

      <main className="max-w-xl mx-auto">

        {/* Feed tab */}
        {activeTab === 'feed' && (
          <>
            <div className="flex items-center justify-between mb-3">
              <p className="text-sm text-slate-500">{status}</p>
              <button
                onClick={refresh}
                className="flex items-center gap-1 text-sm text-blue-600 font-medium hover:underline"
              >
                <RotateCcw size={14} /> Refresh
              </button>
            </div>

            {loading ? (
              <div className="bg-white rounded-[2rem] shadow-xl border border-slate-100 p-10 text-center text-slate-400">
                Loading updates...
              </div>
            ) : currentItem ? (
              <div
                ref={cardRef}
                onPointerDown={onPointerDown}
                onPointerMove={onPointerMove}
                onPointerUp={onPointerUp}
                className="bg-white rounded-[2rem] shadow-xl border border-slate-100 cursor-grab active:cursor-grabbing touch-pan-y select-none"
                style={{ willChange: 'transform' }}
              >
                <div className="p-8">
                  {/* Card header */}
                  <div className="flex justify-between items-start mb-4">
                    <div>
                      <span className="text-[10px] font-black text-slate-400 uppercase tracking-widest block">
                        {currentItem.county}
                      </span>
                      {currentItem.tag && (
                        <span className="inline-block bg-blue-50 text-blue-700 text-xs font-bold px-2 py-1 rounded mt-1">
                          {currentItem.tag}
                        </span>
                      )}
                    </div>
                    {(currentItem.dateDisplay || currentItem.time) && (
                      <div className="text-right">
                        {currentItem.dateDisplay && (
                          <p className="font-bold text-slate-800">{currentItem.dateDisplay}</p>
                        )}
                        {currentItem.time && (
                          <p className="text-sm text-slate-500">{currentItem.time}</p>
                        )}
                      </div>
                    )}
                  </div>

                  {/* Source + title */}
                  <p className="text-xs text-slate-400 mb-1">{currentItem.source}</p>
                  <h3 className="text-xl font-bold text-slate-900 mb-4 leading-tight">
                    {currentItem.title}
                  </h3>

                  {/* Summary */}
                  {currentItem.summary && (
                    <p className="text-slate-600 text-sm mb-4 leading-relaxed">
                      {currentItem.summary}
                    </p>
                  )}

                  {/* Expandable details */}
                  {currentItem.details && (
                    <div className="mb-4">
                      <button
                        onClick={() => setDetailsOpen(o => !o)}
                        className="flex items-center gap-1 text-xs text-blue-600 font-medium mb-2"
                      >
                        Details{' '}
                        <ChevronDown
                          size={12}
                          className={`transition-transform ${detailsOpen ? 'rotate-180' : ''}`}
                        />
                      </button>
                      {detailsOpen && (
                        <div className="bg-slate-50 rounded-xl p-3 text-sm text-slate-600 leading-relaxed border border-slate-100">
                          {currentItem.details}
                        </div>
                      )}
                    </div>
                  )}

                  {/* Open source link */}
                  {currentItem.link && currentItem.link !== '#' && (
                    <a
                      href={currentItem.link}
                      target="_blank"
                      rel="noopener noreferrer"
                      className="text-sm text-teal-600 font-bold hover:underline block mb-6"
                    >
                      Open source →
                    </a>
                  )}

                  {/* Actions */}
                  <div className="flex gap-3">
                    <button
                      onClick={dismiss}
                      className="flex-1 flex items-center justify-center gap-2 py-4 rounded-2xl border-2 border-slate-100 text-slate-400 font-bold hover:bg-red-50 hover:text-red-500 hover:border-red-50 transition-all"
                    >
                      <X size={20} /> Dismiss
                    </button>
                    <button
                      onClick={save}
                      className="flex-1 flex items-center justify-center gap-2 py-4 rounded-2xl bg-teal-500 text-white font-bold shadow-lg shadow-teal-100 hover:bg-teal-600 transition-all"
                    >
                      <Heart size={20} /> Save
                    </button>
                  </div>
                </div>
              </div>
            ) : (
              <div className="bg-white rounded-[2rem] border-2 border-dashed border-slate-200 p-10 text-center text-slate-400">
                <p className="font-bold text-lg mb-1 text-slate-600">All caught up</p>
                <p className="text-sm">Refresh for new updates or review saved cards.</p>
                <button
                  onClick={() => setCurrentIndex(0)}
                  className="mt-4 text-sm text-blue-600 font-medium hover:underline"
                >
                  Review cards again
                </button>
              </div>
            )}

            <p className="text-center text-xs text-slate-400 mt-4">
              Swipe right to save · left to dismiss
            </p>
          </>
        )}

        {/* Saved tab */}
        {activeTab === 'saved' && (
          <div className="bg-white rounded-[2rem] shadow-xl border border-slate-100 p-6">
            <h2 className="font-bold text-lg text-slate-800 mb-4">
              Saved updates{savedItems.length > 0 && ` (${savedItems.length})`}
            </h2>
            {savedItems.length === 0 ? (
              <p className="text-slate-400 text-sm">
                No saved updates yet — save cards from the feed.
              </p>
            ) : (
              <div className="space-y-4">
                {savedItems.map(item => (
                  <div key={item.id} className="border-t border-slate-100 pt-4 first:border-0 first:pt-0">
                    <a
                      href={item.link}
                      target="_blank"
                      rel="noopener noreferrer"
                      className="font-bold text-teal-600 hover:underline text-sm block"
                    >
                      {item.title}
                    </a>
                    <p className="text-xs text-slate-400 mt-1">
                      {item.source}
                      {item.dateDisplay ? ` · ${item.dateDisplay}` : ''}
                    </p>
                  </div>
                ))}
              </div>
            )}
          </div>
        )}

        {/* Insights tab */}
        {activeTab === 'insights' && (
          <div className="bg-white rounded-[2rem] shadow-xl border border-slate-100 p-6 text-center">
            <BarChart3 size={32} className="mx-auto mb-3 text-slate-300" />
            <p className="font-bold text-slate-600">Insights coming soon</p>
            <p className="text-sm text-slate-400 mt-1">
              Activity trends and source stats will appear here.
            </p>
          </div>
        )}

      </main>
    </div>
  );
}
