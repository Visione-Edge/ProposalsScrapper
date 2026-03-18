/* ============================================================
   Dashboard — Filtering, sorting, rendering
   ============================================================ */

const TENDERS = window.SICOP.tenders;

const RELEVANCE_ORDER = { alta: 0, media: 1, baja: 2 };

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

/* DOM references */
const searchInput = document.getElementById('search-input');
const relevanceFilter = document.getElementById('filter-relevance');
const institutionFilter = document.getElementById('filter-institution');
const tableBody = document.getElementById('table-body');
const mobileCardsContainer = document.getElementById('mobile-cards');
const noResultsMessage = document.getElementById('no-results');
const resultsCounter = document.getElementById('results-count');

/* Populate institution dropdown */
const institutions = [...new Set(TENDERS.map(t => t.institution_name))].filter(Boolean).sort();
institutions.forEach(name => {
    const option = document.createElement('option');
    option.value = option.textContent = name;
    institutionFilter.appendChild(option);
});

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

    let rows = TENDERS.filter(tender => {
        if (relevance && tender.relevance !== relevance) return false;
        if (institution && tender.institution_name !== institution) return false;
        if (filterState.fav && !tender.favorite) return false;
        if (filterState.new && !isNewTender(tender)) return false;
        if (!filterState.hidden && tender.not_interested) return false;
        if (filterState.hidden && !tender.not_interested) return false;
        if (query) {
            const searchable = `${tender.name} ${tender.inst_cartel_no} ${tender.institution_name} ${tender.executor_name} ${tender.notes || ''}`.toLowerCase();
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

        return `<tr class="${rowClass}" onclick="openModal(${index})">
            <td onclick="event.stopPropagation(); toggleFavorite(${index})">
                <button class="star-btn ${tender.favorite ? 'on' : ''}" title="Favorito">★</button>
            </td>
            <td><span class="badge badge-${escapeHtml(tender.relevance)}">${escapeHtml(tender.relevance)}</span></td>
            <td class="name-cell">${unviewedDot}<span class="title">${escapeHtml(tender.name)}</span>${newBadge}
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

        return `<div class="mobile-card rel-${escapeHtml(tender.relevance)} ${cardClass}" onclick="openModal(${index})">
            <div class="card-top">
                <div class="card-star" onclick="event.stopPropagation(); toggleFavorite(${index})">
                    <button class="star-btn ${tender.favorite ? 'on' : ''}" title="Favorito">★</button>
                </div>
                <div class="card-body">
                    <div class="card-title">${unviewedDot}${escapeHtml(tender.name)}${newBadge}</div>
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

/* Expose shared state for modal.js */
window._dashboard = { TENDERS, PROCEDURE_TYPES, escapeHtml, formatDateTime, render, updateFavoriteCount };

/* Initialize */
render();
