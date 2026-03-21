/* ============================================================
   Dashboard — Filtering, sorting, rendering
   ============================================================ */

const TENDERS = window.SICOP.tenders;

const RELEVANCE_ORDER = { alta: 0, media: 1, baja: 2 };

const SOURCE_LABELS = {
    sicop: 'SICOP',
    worldbank: 'Banco Mundial',
    undp: 'UNDP',
    idb: 'BID/IDB',
    bcie: 'BCIE',
    caf: 'CAF',
};

const PROCEDURE_TYPES = {
    LN: 'Licitación Pública Nacional',
    LI: 'Licitación Pública Internacional',
    LA: 'Licitación Abreviada',
    PP: 'Procedimiento por Principio',
    CD: 'Contratación Directa',
    CE: 'Contratación Especial',
    RE: 'Remate',
    LY: 'Licitación Mayor',
    LE: 'Licitación Menor',
    LD: 'Licitación Reducida',
    PE: 'Procedimientos Especiales',
    SE: 'Subasta Inversa Electrónica',
    PX: 'Procedimiento por Excepción',
};

/* State */
const filterState = { fav: false, new: false, hidden: false };
let sortColumn = 'registration_date';
let sortDirection = -1;

const NEW_CUTOFF = new Date(Date.now() - 48 * 3600 * 1000).toISOString().slice(0, 19);
const TODAY = new Date().toISOString().slice(0, 10);

function isExpired(tender) {
    var end = tender.bid_end_date;
    if (end && String(end).length >= 10 && String(end).slice(0, 10) < TODAY) return true;
    if (!end || String(end).length < 10) {
        var reg = tender.registration_date;
        if (reg && String(reg).length >= 10) {
            var diff = (new Date() - new Date(String(reg).slice(0, 10))) / 86400000;
            if (diff > 180) return true;
        }
    }
    return false;
}

/* DOM references */
const searchInput = document.getElementById('search-input');
const relevanceFilter = document.getElementById('filter-relevance');
const institutionFilter = document.getElementById('filter-institution');
const tableBody = document.getElementById('table-body');
const mobileCardsContainer = document.getElementById('mobile-cards');
const noResultsMessage = document.getElementById('no-results');
const resultsCounter = document.getElementById('results-count');

const sourceFilter = document.getElementById('filter-source');

/* Populate institution dropdown */
const institutions = [...new Set(TENDERS.map(t => t.institution_name))].filter(Boolean).sort();
institutions.forEach(name => {
    const option = document.createElement('option');
    option.value = option.textContent = name;
    institutionFilter.appendChild(option);
});

/* Populate source dropdown */
(function populateSources() {
    var sel = document.getElementById('filter-source');
    if (!sel) return;
    var seen = {};
    for (var i = 0; i < TENDERS.length; i++) {
        var s = TENDERS[i].source || 'sicop';
        TENDERS[i].source = s;
        seen[s] = true;
    }
    var keys = Object.keys(seen).sort();
    for (var j = 0; j < keys.length; j++) {
        var opt = document.createElement('option');
        opt.value = keys[j];
        opt.textContent = SOURCE_LABELS[keys[j]] || keys[j];
        sel.appendChild(opt);
    }
    console.log('Sources found:', keys);
})();

/* Utilities */
function escapeHtml(value) {
    if (value == null || value === '') return '—';
    return String(value).replace(/&/g, '&amp;').replace(/</g, '&lt;').replace(/>/g, '&gt;').replace(/"/g, '&quot;');
}

function formatDate(dateStr) {
    return dateStr ? String(dateStr).slice(0, 10) : '—';
}

function formatDateTime(dateStr) {
    return dateStr ? String(dateStr).slice(0, 16).replace('T', ' ') : '—';
}

function isNewTender(tender) {
    return tender.first_seen && tender.first_seen >= NEW_CUTOFF;
}

/* ── Filtering & Rendering ──────────────────────────────────── */

function render() {
    const query = searchInput.value.toLowerCase();
    const relevance = relevanceFilter.value;
    const institution = institutionFilter.value;
    const source = sourceFilter ? sourceFilter.value : '';

    let rows = TENDERS.filter(tender => {
        if (isExpired(tender)) return false;
        if (relevance && tender.relevance !== relevance) return false;
        if (institution && tender.institution_name !== institution) return false;
        if (source && (tender.source || 'sicop') !== source) return false;
        if (filterState.fav && !tender.favorite) return false;
        if (filterState.new && !isNewTender(tender)) return false;
        if (!filterState.hidden && tender.not_interested) return false;
        if (filterState.hidden && !tender.not_interested) return false;
        if (query) {
            const searchable = `${tender.name} ${tender.inst_cartel_no} ${tender.institution_name} ${tender.executor_name} ${tender.notes || ''} ${SOURCE_LABELS[tender.source] || tender.source || ''}`.toLowerCase();
            if (!searchable.includes(query)) return false;
        }
        return true;
    });

    rows.sort((a, b) => {
        let valueA = a[sortColumn] ?? '';
        let valueB = b[sortColumn] ?? '';
        if (sortColumn === 'relevance') {
            valueA = RELEVANCE_ORDER[valueA] ?? 9;
            valueB = RELEVANCE_ORDER[valueB] ?? 9;
        }
        if (valueA < valueB) return -sortDirection;
        if (valueA > valueB) return sortDirection;
        return 0;
    });

    window._filteredTenders = rows;
    resultsCounter.textContent = rows.length;

    if (!rows.length) {
        tableBody.innerHTML = '';
        mobileCardsContainer.innerHTML = '';
        noResultsMessage.style.display = 'block';
        return;
    }
    noResultsMessage.style.display = 'none';
    renderTable(rows);
    renderMobileCards(rows);
}

function renderTable(rows) {
    tableBody.innerHTML = rows.map((tender, index) => {
        const keywords = Array.isArray(tender.matched_keywords) ? tender.matched_keywords : [];
        const isNew = isNewTender(tender);
        const newBadge = isNew ? '<span class="badge badge-new">nuevo</span>' : '';
        const unviewedDot = !tender.viewed ? '<span class="unviewed-dot"></span>' : '';

        let rowClass = '';
        if (tender.not_interested) rowClass = 'hidden-row';
        else if (isNew && !tender.viewed) rowClass = 'is-new';
        else if (!tender.viewed) rowClass = 'unviewed';

        const sourceBadge = tender.source && tender.source !== 'sicop' ? `<span class="badge badge-source badge-source-${escapeHtml(tender.source)}">${escapeHtml(SOURCE_LABELS[tender.source] || tender.source)}</span>` : '';

        return `<tr class="${rowClass}" onclick="openModal(${index})">
            <td onclick="event.stopPropagation(); toggleFavorite(${index})">
                <button class="star-btn ${tender.favorite ? 'on' : ''}" title="Favorito">★</button>
            </td>
            <td><span class="badge badge-${escapeHtml(tender.relevance)}">${escapeHtml(tender.relevance)}</span></td>
            <td class="name-cell">${unviewedDot}<span class="title">${escapeHtml(tender.name)}</span>${newBadge}${sourceBadge}
                ${keywords.length ? `<div class="keyword-preview">${keywords.slice(0, 4).map(k => escapeHtml(k)).join(', ')}</div>` : ''}</td>
            <td class="institution-cell" title="${escapeHtml(tender.institution_name)}">${escapeHtml(tender.institution_name)}</td>
            <td title="${escapeHtml(PROCEDURE_TYPES[tender.procedure_type])}">${escapeHtml(tender.procedure_type)}</td>
            <td>${escapeHtml(tender.status)}</td>
            <td class="date-cell">${formatDate(tender.registration_date)}</td>
            <td class="date-cell">${formatDate(tender.bid_end_date)}</td>
        </tr>`;
    }).join('');
}

function renderMobileCards(rows) {
    mobileCardsContainer.innerHTML = rows.map((tender, index) => {
        const keywords = Array.isArray(tender.matched_keywords) ? tender.matched_keywords : [];
        const isNew = isNewTender(tender);
        const newBadge = isNew ? ' <span class="badge badge-new">nuevo</span>' : '';
        const unviewedDot = !tender.viewed ? '<span class="unviewed-dot"></span>' : '';

        let cardClass = '';
        if (tender.not_interested) cardClass = 'card-hidden';
        else if (isNew) cardClass = 'card-new';
        else if (!tender.viewed) cardClass = 'card-unviewed';

        const mSourceBadge = tender.source && tender.source !== 'sicop' ? ` <span class="badge badge-source badge-source-${escapeHtml(tender.source)}">${escapeHtml(SOURCE_LABELS[tender.source] || tender.source)}</span>` : '';

        return `<div class="mobile-card rel-${escapeHtml(tender.relevance)} ${cardClass}" onclick="openModal(${index})">
            <div class="card-top">
                <div class="card-star" onclick="event.stopPropagation(); toggleFavorite(${index})">
                    <button class="star-btn ${tender.favorite ? 'on' : ''}" title="Favorito">★</button>
                </div>
                <div class="card-body">
                    <div class="card-title">${unviewedDot}${escapeHtml(tender.name)}${newBadge}${mSourceBadge}</div>
                    <div class="card-institution">${escapeHtml(tender.institution_name)}</div>
                    ${keywords.length ? `<div class="card-keywords">${keywords.slice(0, 3).map(k => escapeHtml(k)).join(', ')}</div>` : ''}
                </div>
                <div class="card-badge-wrap"><span class="badge badge-${escapeHtml(tender.relevance)}">${escapeHtml(tender.relevance)}</span></div>
            </div>
            <div class="card-footer">
                <div><span>Pub:</span> ${formatDate(tender.registration_date)}</div>
                <div><span>Límite:</span> ${formatDate(tender.bid_end_date)}</div>
            </div>
        </div>`;
    }).join('');
}

/* ── Favorites ──────────────────────────────────────────────── */

async function toggleFavorite(index) {
    const tender = window._filteredTenders[index];
    const dataIndex = TENDERS.indexOf(tender);
    const response = await fetch(`/api/tender/${tender.cartel_no}/${tender.cartel_seq}/favorite`, { method: 'POST', headers: { 'X-Requested-With': 'XMLHttpRequest' } });
    const { favorite } = await response.json();
    TENDERS[dataIndex].favorite = favorite;
    updateFavoriteCount();
    render();
}

function updateFavoriteCount() {
    document.getElementById('fav-count').textContent = TENDERS.filter(t => t.favorite).length;
}

/* ── Filter Toggles ─────────────────────────────────────────── */

function toggleFilter(key) {
    filterState[key] = !filterState[key];
    const buttonMap = { fav: 'btn-fav', new: 'btn-new', hidden: 'btn-hidden' };
    const button = document.getElementById(buttonMap[key]);
    if (key === 'hidden') button.classList.toggle('active-red', filterState[key]);
    else button.classList.toggle('active', filterState[key]);
    render();
}

/* ── Sorting ────────────────────────────────────────────────── */

document.querySelectorAll('th[data-sort]').forEach(header => {
    header.addEventListener('click', () => {
        const column = header.dataset.sort;
        sortDirection = sortColumn === column ? -sortDirection : (column.includes('date') ? -1 : 1);
        sortColumn = column;
        document.querySelectorAll('th .sort-arrow').forEach(arrow => arrow.textContent = '');
        header.querySelector('.sort-arrow').textContent = sortDirection === 1 ? '▲' : '▼';
        render();
    });
});

searchInput.addEventListener('input', render);
relevanceFilter.addEventListener('change', render);
institutionFilter.addEventListener('change', render);
if (sourceFilter) sourceFilter.addEventListener('change', render);

/* Expose shared state for modal.js */
window._dashboard = { TENDERS, PROCEDURE_TYPES, escapeHtml, formatDateTime, render, updateFavoriteCount };

/* Initialize */
render();
