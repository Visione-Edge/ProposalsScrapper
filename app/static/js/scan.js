/* ============================================================
   Scan polling & toast notifications
   ============================================================ */

function showToast(message) {
    const toast = document.getElementById('toast');
    toast.textContent = message;
    toast.classList.add('show');
    clearTimeout(toast._timer);
    toast._timer = setTimeout(() => toast.classList.remove('show'), 4000);
}

async function startScan() {
    const scanButton = document.getElementById('btn-scan');
    scanButton.disabled = true;
    scanButton.textContent = 'Escaneando...';
    showToast('Scan iniciado, puede tomar unos minutos...');

    try {
        const response = await fetch('/api/scan', {
            method: 'POST',
            headers: { 'Content-Type': 'application/json', 'X-Requested-With': 'XMLHttpRequest' },
            body: '{}',
        });
        if (response.status === 409) {
            showToast('Ya hay un scan en curso.');
            scanButton.disabled = false;
            scanButton.textContent = 'Escanear';
            return;
        }
        pollScanStatus();
    } catch (error) {
        showToast('Error iniciando scan.');
        scanButton.disabled = false;
        scanButton.textContent = 'Escanear';
    }
}

function pollScanStatus() {
    const pollInterval = setInterval(async () => {
        try {
            const response = await fetch('/api/scan/status');
            const data = await response.json();

            if (!data.running) {
                clearInterval(pollInterval);
                const scanButton = document.getElementById('btn-scan');
                scanButton.disabled = false;
                scanButton.textContent = 'Escanear';

                if (data.error) {
                    showToast('Error: ' + data.error);
                } else if (data.last_result) {
                    const result = data.last_result;
                    showToast(`Scan completo — ${result.new} nuevas, ${result.new_relevant} relevantes`);
                    var scanInfo = document.getElementById('scan-time-stat');
                    if (scanInfo) scanInfo.textContent = 'Último scan: ' + (result.completed_at || '').slice(0, 16).replace('T', ' ');
                    setTimeout(() => location.reload(), 1500);
                }
            }
        } catch (error) {
            clearInterval(pollInterval);
        }
    }, 2500);
}
