/* ============================================================
   Modal — Detail view, favorites, notes
   ============================================================ */

var currentTender = null;

function openModal(index) {
    var d = window._dashboard;
    var tender = window._filteredTenders[index];
    currentTender = tender;

    if (!tender.viewed) {
        fetch('/api/tender/' + tender.cartel_no + '/' + tender.cartel_seq + '/viewed', { method: 'POST', headers: { 'X-Requested-With': 'XMLHttpRequest' } });
        var dataIndex = d.TENDERS.indexOf(tender);
        d.TENDERS[dataIndex].viewed = 1;
        tender.viewed = 1;
        var counter = document.getElementById('unviewed-count');
        if (counter) counter.textContent = Math.max(0, parseInt(counter.textContent) - 1);
    }

    document.getElementById('modal-title').textContent = tender.name || '—';

    var detailFields = [
        ['N° de concurso', tender.inst_cartel_no, false, true],
        ['N° SICOP', tender.cartel_no, false, true],
        ['Institución', tender.institution_name, true],
        ['Ejecutor', tender.executor_name, true],
        ['Tipo de procedimiento', d.PROCEDURE_TYPES[tender.procedure_type]
            ? tender.procedure_type + ' — ' + d.PROCEDURE_TYPES[tender.procedure_type]
            : tender.procedure_type, true],
        ['Estado', tender.status],
        ['Publicación', d.formatDateTime(tender.registration_date)],
        ['Inicio oferta', d.formatDateTime(tender.bid_start_date)],
        ['Fecha límite', d.formatDateTime(tender.bid_end_date)],
        ['Apertura', d.formatDateTime(tender.opening_date)],
        ['Primera vez visto', d.formatDateTime(tender.first_seen)],
    ];

    document.getElementById('modal-details').innerHTML = detailFields.map(function(field) {
        var label = field[0], value = field[1], isFullWidth = field[2], copyable = field[3];
        var copyBtn = copyable && value ? ' <button class="copy-btn" onclick="copyToClipboard(\'' + d.escapeHtml(value) + '\', this)" title="Copiar">Copiar</button>' : '';
        return '<div class="detail-item' + (isFullWidth ? ' full' : '') + '">' +
            '<div class="detail-label">' + label + '</div>' +
            '<div class="detail-value">' + d.escapeHtml(value) + copyBtn + '</div>' +
        '</div>';
    }).join('');

    var keywords = Array.isArray(tender.matched_keywords) ? tender.matched_keywords : [];
    var keywordsSection = document.getElementById('modal-keywords');
    if (keywords.length) {
        document.getElementById('modal-keyword-tags').innerHTML =
            keywords.map(function(k) { return '<span class="keyword-tag">' + d.escapeHtml(k) + '</span>'; }).join('');
        keywordsSection.style.display = 'block';
    } else {
        keywordsSection.style.display = 'none';
    }

    document.getElementById('modal-notes').value = tender.notes || '';
    document.getElementById('notes-saved').style.display = 'none';

    var favButton = document.getElementById('modal-fav-btn');
    var hiddenButton = document.getElementById('modal-hidden-btn');
    favButton.className = 'action-btn ' + (tender.favorite ? 'fav-on' : '');
    favButton.textContent = tender.favorite ? '★ Favorito' : 'Favorito';
    hiddenButton.className = 'action-btn ' + (tender.not_interested ? 'hidden-on' : '');
    hiddenButton.textContent = tender.not_interested ? 'Mostrar' : 'No me interesa';

    document.getElementById('overlay').classList.add('open');
    document.body.style.overflow = 'hidden';
}

function closeModal() {
    document.getElementById('overlay').classList.remove('open');
    document.body.style.overflow = '';
    currentTender = null;
}

document.getElementById('overlay').addEventListener('click', function(event) {
    if (event.target === event.currentTarget) closeModal();
});
document.addEventListener('keydown', function(event) { if (event.key === 'Escape') closeModal(); });

function modalToggleFavorite() {
    if (!currentTender) return;
    var d = window._dashboard;
    var tender = currentTender;
    fetch('/api/tender/' + tender.cartel_no + '/' + tender.cartel_seq + '/favorite', { method: 'POST', headers: { 'X-Requested-With': 'XMLHttpRequest' } })
        .then(function(res) { return res.json(); })
        .then(function(data) {
            var dataIndex = d.TENDERS.indexOf(tender);
            d.TENDERS[dataIndex].favorite = data.favorite;
            tender.favorite = data.favorite;
            var button = document.getElementById('modal-fav-btn');
            button.className = 'action-btn ' + (data.favorite ? 'fav-on' : '');
            button.textContent = data.favorite ? '★ Favorito' : 'Favorito';
            d.updateFavoriteCount();
            d.render();
        });
}

function modalToggleHidden() {
    if (!currentTender) return;
    var d = window._dashboard;
    var tender = currentTender;
    fetch('/api/tender/' + tender.cartel_no + '/' + tender.cartel_seq + '/not-interested', { method: 'POST', headers: { 'X-Requested-With': 'XMLHttpRequest' } })
        .then(function(res) { return res.json(); })
        .then(function(data) {
            var dataIndex = d.TENDERS.indexOf(tender);
            d.TENDERS[dataIndex].not_interested = data.not_interested;
            tender.not_interested = data.not_interested;
            var button = document.getElementById('modal-hidden-btn');
            button.className = 'action-btn ' + (data.not_interested ? 'hidden-on' : '');
            button.textContent = data.not_interested ? 'Mostrar' : 'No me interesa';
            closeModal();
            d.render();
        });
}

function copyToClipboard(text, btn) {
    navigator.clipboard.writeText(text).then(function() {
        var original = btn.textContent;
        btn.textContent = 'Copiado';
        btn.classList.add('copied');
        setTimeout(function() {
            btn.textContent = original;
            btn.classList.remove('copied');
        }, 1500);
    });
}

function saveNotes() {
    if (!currentTender) return;
    var d = window._dashboard;
    var tender = currentTender;
    var notes = document.getElementById('modal-notes').value;
    fetch('/api/tender/' + tender.cartel_no + '/' + tender.cartel_seq + '/notes', {
        method: 'PUT',
        headers: { 'Content-Type': 'application/json', 'X-Requested-With': 'XMLHttpRequest' },
        body: JSON.stringify({ notes: notes }),
    }).then(function() {
        var dataIndex = d.TENDERS.indexOf(tender);
        d.TENDERS[dataIndex].notes = notes;
        tender.notes = notes;
        var savedIndicator = document.getElementById('notes-saved');
        savedIndicator.style.display = 'inline';
        setTimeout(function() { savedIndicator.style.display = 'none'; }, 2000);
    });
}
