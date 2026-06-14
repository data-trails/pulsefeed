const PALETTE = ['#3b82f6', '#10b981', '#8b5cf6', '#f59e0b', '#ef4444', '#06b6d4', '#f97316', '#84cc16', '#ec4899', '#14b8a6', '#6366f1', '#d97706'];
const ZONING_KW = ['zoning', 'rezoning', 'rezone', 'variance', 'ordinance', 'conditional use', 'special use', 'site plan', 'overlay', 'setback', 'land use', 'master plan', 'special land use', 'text amendment', 'zba', 'zoning board'];
const HOUSING_KW = ['housing', 'residential', 'apartment', 'dwelling', 'affordable', 'subdivision', 'plat', 'condominium', 'condo', 'single family', 'multifamily', 'multi-family', 'duplex', 'accessory dwelling', 'adu', 'short-term rental', 'str', 'townhouse', 'senior housing', 'mixed use'];
const INDUSTRIAL_KW = ['industrial', 'warehouse', 'manufacturing', 'logistics', 'commercial', 'business park', 'distribution', 'storage', 'factory', 'data center', 'solar', 'wind', 'energy', 'utility', 'mining', 'gravel', 'aggregate', 'renewable'];

const TABS = ['feed', 'calendar', 'saved', 'sources'];
const savedKey = 'pulsefeed.savedItems';
const dismissedKey = 'pulsefeed.dismissedIds';

const SOURCES = [
  { county: 'Allegan', name: 'Allegan Township Planning Commission', url: 'https://allegantownship.org/planning-commission/' },
  { county: 'Allegan', name: 'Casco Township Planning Commission', url: 'https://www.cascotownship.info/meetings---planning-commission.html' },
  { county: 'Allegan', name: 'Cheshire Township Planning Commission', url: 'https://cheshiretownshipmi.gov/minutes.html' },
  { county: 'Allegan', name: 'Clyde Township Planning Commission', url: 'https://clydetwp.com/' },
  { county: 'Allegan', name: 'Dorr Township Planning Commission', url: 'https://dorrtownshipmi.gov/-Minutes-Agendas/Planning-Commission' },
  { county: 'Allegan', name: 'Fillmore Township Planning Commission', url: 'https://fillmoretownship.org/board-minutes/' },
  { county: 'Allegan', name: 'Ganges Township Planning Commission', url: 'https://www.gangestownship.org/Planning-Commission-Meetings-Archive.html' },
  { county: 'Allegan', name: 'Gun Plain Township Planning Commission', url: 'https://www.gunplain.org/meeting-minutes-and-agendas/' },
  { county: 'Allegan', name: 'Heath Township Planning Commission', url: 'https://heathtownship.net/' },
  { county: 'Allegan', name: 'Hopkins Township Planning Commission', url: 'https://www.hopkinstownship.org/board-minutes/' },
  { county: 'Allegan', name: 'Laketown Township Planning Commission', url: 'https://laketowntwp.org/boards-commissions/' },
  { county: 'Allegan', name: 'Lee Township Planning Commission', url: 'http://www.leetwp.org/meetingminutes.htm' },
  { county: 'Allegan', name: 'Leighton Township Planning Commission', url: 'https://leightontownship.org/meetings-minutes/' },
  { county: 'Allegan', name: 'Manlius Township Planning Commission', url: 'https://www.manliustwp.org/boardmeetings' },
  { county: 'Allegan', name: 'Martin Township Planning Commission', url: 'https://www.martintownship.org/' },
  { county: 'Allegan', name: 'Monterey Township Planning Commission', url: 'https://www.montereytownship.org/' },
  { county: 'Allegan', name: 'Otsego Township Planning Commission', url: 'https://www.otsegotownship.org/building-planning-and-zoning/' },
  { county: 'Allegan', name: 'Overisel Township Planning Commission', url: 'https://overiseltownship.org/planning-commission/' },
  { county: 'Allegan', name: 'Salem Township Planning Commission', url: 'https://salemtownship.org/planning-commission' },
  { county: 'Allegan', name: 'Saugatuck Township Planning Commission', url: 'https://saugatucktownshipmi.gov/saugatuck-township-local-government/packets-agendas-minutes/agendas/' },
  { county: 'Allegan', name: 'Trowbridge Township Planning Commission', url: 'https://trowbridgetownship.org/' },
  { county: 'Allegan', name: 'Valley Township Planning Commission', url: 'https://valleytwp.org/minutes.htm' },
  { county: 'Allegan', name: 'Watson Township Planning Commission', url: 'https://watsontownshipmi.gov/' },
  { county: 'Allegan', name: 'Wayland Township Planning Commission', url: 'https://waytwp.org/departments/zoning/' },
  { county: 'Allegan', name: 'City of Allegan Planning Commission', url: 'https://www.cityofallegan.org/government/planning_commission.php' },
  { county: 'Ottawa', name: 'Allendale Charter Township Planning Commission', url: 'https://allendalemi.gov/planning-commission/' },
  { county: 'Ottawa', name: 'Blendon Township Planning Commission', url: 'https://www.blendontownship-mi.gov/planning-commission/' },
  { county: 'Ottawa', name: 'Chester Township Planning Commission', url: 'https://www.chester-twp.org/documents/' },
  { county: 'Ottawa', name: 'Crockery Township Planning Commission', url: 'https://crockerytownship.gov/planning-commission/' },
  { county: 'Ottawa', name: 'Georgetown Charter Township Planning Commission', url: 'https://www.gtwp.com/155/Planning-Commission' },
  { county: 'Ottawa', name: 'Grand Haven Charter Township Planning Commission', url: 'https://ghtmi.gov/boards/planning-commission/' },
  { county: 'Ottawa', name: 'Holland Charter Township Planning Commission', url: 'https://www.hct.holland.mi.us/agendas-minutes/planning-commission' },
  { county: 'Ottawa', name: 'Jamestown Charter Township Planning Commission', url: 'https://twp.jamestown.mi.us/government/boards-and-minutes/planning-commission-agendas-minutes/' },
  { county: 'Ottawa', name: 'Olive Township Planning Commission', url: 'https://www.olivetownship.org/document-category/pcminutes/' },
  { county: 'Ottawa', name: 'Park Township Planning Commission', url: 'https://webgen1files1.revize.com/parktwpmi/Document_Center/Meeting%20Agenda_Minutes%20%26%20Packets/Planning%20Commission/' },
  { county: 'Ottawa', name: 'Polkton Charter Township Planning Commission', url: 'https://polktontownship.com/planning-commission/' },
  { county: 'Ottawa', name: 'Port Sheldon Township Planning Commission', url: 'https://www.portsheldontwp.org/planning-commission/' },
  { county: 'Ottawa', name: 'Robinson Township Planning Commission', url: 'https://robinsontwpmi.gov/' },
  { county: 'Ottawa', name: 'Spring Lake Township Planning Commission', url: 'https://springlaketwp.org/board/planning-commission/' },
  { county: 'Ottawa', name: 'Tallmadge Charter Township Planning Commission', url: 'https://tallmadge.com/minutes-agendas/' },
  { county: 'Ottawa', name: 'Wright Township Planning Commission', url: 'http://wrighttownshipottawami.gov/' },
  { county: 'Ottawa', name: 'Zeeland Charter Township Planning Commission', url: 'https://zeelandchartertwpmi.documents-on-demand.com/' }
];

let activeTab = 'feed';
let items = [];
let savedItems = loadSavedItems();
let dismissedIds = loadDismissedIds();

function escapeHtml(value) {
  return String(value || '')
    .replace(/&/g, '&amp;')
    .replace(/</g, '&lt;')
    .replace(/>/g, '&gt;')
    .replace(/"/g, '&quot;')
    .replace(/'/g, '&#39;');
}

function sourceColor(name) {
  let hash = 0;
  for (let i = 0; i < name.length; i += 1) {
    hash = (hash * 31 + name.charCodeAt(i)) & 0xffff;
  }
  return PALETTE[hash % PALETTE.length];
}

function getTopics(item) {
  if (Array.isArray(item.topics) && item.topics.length > 0) {
    return item.topics;
  }
  const content = [item.title, item.summary, item.pdfItems].filter(Boolean).join(' ').toLowerCase();
  const topics = [];
  if (ZONING_KW.some(keyword => content.includes(keyword))) topics.push('Zoning');
  if (HOUSING_KW.some(keyword => content.includes(keyword))) topics.push('Housing');
  if (INDUSTRIAL_KW.some(keyword => content.includes(keyword))) topics.push('Industrial');
  return topics;
}

function filterPdfItems(pdfItems) {
  if (!pdfItems) return '';
  return pdfItems.split('\n').filter(Boolean).join('\n');
}

function formatCalendarDate(dateStr) {
  const date = new Date(`${dateStr}T00:00:00`);
  if (Number.isNaN(date.getTime())) return dateStr;
  const today = new Date();
  today.setHours(0, 0, 0, 0);
  const diff = Math.round((date - today) / 86400000);
  if (diff === 0) return 'Today';
  if (diff === 1) return 'Tomorrow';
  if (diff === -1) return 'Yesterday';
  return date.toLocaleDateString('en-US', { weekday: 'short', month: 'short', day: 'numeric' });
}

function loadSavedItems() {
  try {
    return JSON.parse(localStorage.getItem(savedKey)) || [];
  } catch (error) {
    return [];
  }
}

function loadDismissedIds() {
  try {
    return new Set(JSON.parse(localStorage.getItem(dismissedKey)) || []);
  } catch (error) {
    return new Set();
  }
}

function writeSavedItems() {
  localStorage.setItem(savedKey, JSON.stringify(savedItems));
}

function writeDismissedIds() {
  localStorage.setItem(dismissedKey, JSON.stringify([...dismissedIds]));
}

function setActiveTab(tab) {
  activeTab = tab;
  document.querySelectorAll('.tab-button').forEach(button => {
    button.classList.toggle('active', button.dataset.tab === tab);
  });
  render();
}

async function loadFeed() {
  setStatus('Refreshing updates…');
  try {
    const response = await fetch('/feed.json');
    if (!response.ok) throw new Error('Feed unavailable');
    const data = await response.json();
    items = Array.isArray(data) ? data : [];
    const count = items.length;
    setStatus(count > 0 ? `${count} update${count === 1 ? '' : 's'} loaded.` : 'No live updates yet.');
  } catch (error) {
    items = [];
    setStatus('Could not load feed — check the server.');
    console.error(error);
  }
  render();
}

function setStatus(text) {
  const target = document.getElementById('status-text');
  if (target) target.textContent = text;
}

function cardActions(item) {
  const isSaved = savedItems.some(saved => saved.id === item.id);
  return `
    <div class="action-row">
      <button class="secondary small" data-action="dismiss" data-id="${escapeHtml(item.id)}">Dismiss</button>
      <button class="primary small" data-action="save" data-id="${escapeHtml(item.id)}">${isSaved ? 'Saved' : 'Save'}</button>
    </div>
  `;
}

function renderFeed() {
  const visibleItems = items.filter(item => !dismissedIds.has(item.id));
  if (items.length === 0) {
    return `<div class="empty-state"><p class="card-title">No feed items available</p><p class="detail-text">Your feed has not loaded yet. Try refreshing or check that feed.json is present.</p></div>`;
  }
  if (visibleItems.length === 0) {
    return `<div class="empty-state"><p class="card-title">All caught up</p><p class="detail-text">There are no remaining feed items. Review saved items or reset dismissed updates.</p><button class="primary small" data-action="reset-dismissed">Show dismissed items</button></div>`;
  }
  return visibleItems.map(item => {
    const topics = getTopics(item);
    const pdfLines = filterPdfItems(item.pdfItems).split('\n').filter(Boolean);
    const color = sourceColor(item.source);
    const labelColor = `background: ${color}; opacity: 0.08; border-color: ${color}; color: ${color};`;
    const tags = [];
    if (item.tag) tags.push(`<span class="pill status">${escapeHtml(item.tag)}</span>`);
    if (item.docType) tags.push(`<span class="pill warning">${escapeHtml(item.docType)}</span>`);
    topics.forEach(topic => tags.push(`<span class="pill note">${escapeHtml(topic)}</span>`));
    return `
      <article class="card" style="border-color: ${color}22;">
        <div class="card-header">
          <div>
            <p class="item-meta">${escapeHtml(item.source)}</p>
            <h2 class="card-title">${escapeHtml(item.title)}</h2>
          </div>
          ${item.dateDisplay ? `<span class="pill note">${escapeHtml(item.dateDisplay)}</span>` : ''}
        </div>
        <div class="tags-row">${tags.join('')}</div>
        ${item.summary ? `<p class="detail-text">${escapeHtml(item.summary)}</p>` : ''}
        ${item.parcels && item.parcels.length > 0 ? `<p class="detail-text"><strong>Parcels:</strong> ${escapeHtml(item.parcels.join(', '))}</p>` : ''}
        ${pdfLines.length > 0 ? `<div class="card">
              <p class="card-title">Agenda Items</p>
              <ul>${pdfLines.map(line => `<li>${escapeHtml(line)}</li>`).join('')}</ul>
            </div>` : ''}
        ${item.link ? `<a class="link-row" href="${escapeHtml(item.link)}" target="_blank" rel="noopener noreferrer">Open source</a>` : ''}
        ${cardActions(item)}
      </article>
    `;
  }).join('');
}

function groupByDate(itemsList) {
  return itemsList.reduce((acc, item) => {
    if (!item.date) return acc;
    acc[item.date] = acc[item.date] || [];
    acc[item.date].push(item);
    return acc;
  }, {});
}

function renderCalendar() {
  if (items.length === 0) {
    return `<div class="empty-state"><p class="card-title">No dated events</p><p class="detail-text">Load the feed to see calendar items with meeting dates.</p></div>`;
  }
  const dated = items.filter(item => item.date).sort((a, b) => a.date.localeCompare(b.date));
  const today = new Date().toISOString().slice(0, 10);
  const upcoming = dated.filter(item => item.date >= today);
  const recent = dated.filter(item => item.date < today).reverse();
  const sections = [];
  if (upcoming.length) {
    sections.push(`<section><h2 class="card-title">Upcoming</h2>${renderDateGroups(upcoming)}</section>`);
  }
  if (recent.length) {
    sections.push(`<section><h2 class="card-title">Recent</h2>${renderDateGroups(recent)}</section>`);
  }
  if (!sections.length) {
    return `<div class="empty-state"><p class="card-title">No dated items found</p><p class="detail-text">Items with meeting dates will appear here.</p></div>`;
  }
  return sections.join('');
}

function renderDateGroups(itemsList) {
  const grouped = groupByDate(itemsList);
  return Object.entries(grouped).map(([date, entries]) => `
    <div class="date-group">
      <div class="date-group-header">${escapeHtml(formatCalendarDate(date))}</div>
      ${entries.map(item => `
        <article class="event-card">
          <p class="item-meta">${escapeHtml(item.source)}</p>
          <h3 class="event-title">${escapeHtml(item.title)}</h3>
          <div class="event-labels">
            ${item.tag ? `<span class="pill status">${escapeHtml(item.tag)}</span>` : ''}
            ${item.docType ? `<span class="pill warning">${escapeHtml(item.docType)}</span>` : ''}
            ${getTopics(item).map(topic => `<span class="pill note">${escapeHtml(topic)}</span>`).join('')}
          </div>
          ${item.link ? `<a class="link-row" href="${escapeHtml(item.link)}" target="_blank" rel="noopener noreferrer">Open source</a>` : ''}
        </article>
      `).join('')}
    </div>
  `).join('');
}

function renderSaved() {
  if (!savedItems.length) {
    return `<div class="empty-state"><p class="card-title">No saved items yet</p><p class="detail-text">Save cards from the feed to keep items here.</p></div>`;
  }
  return savedItems.map(item => `
    <article class="card">
      <div class="card-header">
        <div>
          <p class="item-meta">${escapeHtml(item.source)}</p>
          <h2 class="card-title">${escapeHtml(item.title)}</h2>
        </div>
        <button class="secondary small" data-action="unsave" data-id="${escapeHtml(item.id)}">Remove</button>
      </div>
      ${item.dateDisplay ? `<p class="detail-text">${escapeHtml(item.dateDisplay)}</p>` : ''}
    </article>
  `).join('');
}

function renderSources() {
  const byCounty = SOURCES.reduce((acc, source) => {
    acc[source.county] = acc[source.county] || [];
    acc[source.county].push(source);
    return acc;
  }, {});
  return Object.entries(byCounty).map(([county, sources]) => `
    <section class="source-group">
      <div class="source-group-header">${escapeHtml(county)} County</div>
      ${sources.map(source => `
        <a class="source-item" href="${escapeHtml(source.url)}" target="_blank" rel="noopener noreferrer">
          <span>${escapeHtml(source.name)}</span>
          <span>&rarr;</span>
        </a>
      `).join('')}
    </section>
  `).join('');
}

function render() {
  const pane = document.getElementById('pane');
  if (!pane) return;
  if (activeTab === 'feed') {
    pane.innerHTML = renderFeed();
    document.getElementById('refresh-button').style.display = 'inline-flex';
  } else if (activeTab === 'calendar') {
    pane.innerHTML = renderCalendar();
    document.getElementById('refresh-button').style.display = 'none';
  } else if (activeTab === 'saved') {
    pane.innerHTML = renderSaved();
    document.getElementById('refresh-button').style.display = 'none';
  } else if (activeTab === 'sources') {
    pane.innerHTML = renderSources();
    document.getElementById('refresh-button').style.display = 'none';
  }
}

function findItemById(id) {
  return items.find(item => item.id === id) || savedItems.find(item => item.id === id);
}

function handleActions(event) {
  const button = event.target.closest('[data-action]');
  if (!button) return;
  const action = button.dataset.action;
  const id = button.dataset.id;
  const item = id ? findItemById(id) : null;

  if (action === 'save' && item) {
    if (!savedItems.some(saved => saved.id === item.id)) {
      savedItems.unshift(item);
      writeSavedItems();
    }
    dismissedIds.add(item.id);
    writeDismissedIds();
    render();
  }

  if (action === 'dismiss' && item) {
    dismissedIds.add(item.id);
    writeDismissedIds();
    render();
  }

  if (action === 'unsave' && item) {
    savedItems = savedItems.filter(saved => saved.id !== item.id);
    writeSavedItems();
    render();
  }

  if (action === 'reset-dismissed') {
    dismissedIds = new Set();
    writeDismissedIds();
    render();
  }
}

document.addEventListener('DOMContentLoaded', () => {
  document.querySelectorAll('.tab-button').forEach(button => {
    button.addEventListener('click', () => setActiveTab(button.dataset.tab));
  });
  document.getElementById('refresh-button').addEventListener('click', loadFeed);
  document.getElementById('pane').addEventListener('click', handleActions);
  loadFeed();
});
