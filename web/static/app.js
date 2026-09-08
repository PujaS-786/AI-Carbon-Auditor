// EcoChain 24 Frontend Controller

let allRecords = [];
let allLedgerBlocks = [];
let hitlItems = [];

document.addEventListener('DOMContentLoaded', () => {
  initTabs();
  initIntakeZone();
  fetchInitialData();

  // Button Listeners
  document.getElementById('btn-ingest-sample')?.addEventListener('click', runSampleIngestion);
  document.getElementById('btn-verify-chain')?.addEventListener('click', () => verifyLedgerChain(true));
  document.getElementById('file-upload-input')?.addEventListener('change', handleFileUpload);
  document.getElementById('filter-scope')?.addEventListener('change', filterRecordsTable);
  document.getElementById('search-records')?.addEventListener('input', filterRecordsTable);
  document.getElementById('btn-view-json')?.addEventListener('click', openJsonModal);
});

// Tab Navigation
function initTabs() {
  const tabBtns = document.querySelectorAll('.tab-btn');
  tabBtns.forEach(btn => {
    btn.addEventListener('click', () => {
      tabBtns.forEach(b => b.classList.remove('active'));
      document.querySelectorAll('.tab-content').forEach(c => c.classList.remove('active'));

      btn.classList.add('active');
      const targetId = btn.getAttribute('data-tab');
      const targetEl = document.getElementById(targetId);
      if (targetEl) targetEl.classList.add('active');
    });
  });
}

function switchToTab(tabId) {
  const btn = document.querySelector(`.tab-btn[data-tab="${tabId}"]`);
  if (btn) btn.click();
}

// Toast Notifications
function showToast(msg, type = "success") {
  let container = document.getElementById('toast-container');
  if (!container) {
    container = document.createElement('div');
    container.id = 'toast-container';
    document.body.appendChild(container);
  }

  const toast = document.createElement('div');
  toast.className = `toast toast-${type}`;
  toast.innerHTML = `
    <div style="flex: 1;">${escapeHtml(msg)}</div>
    <button style="background:none;border:none;color:currentColor;cursor:pointer;font-size:1.1rem;padding:0 4px;line-height:1;" onclick="this.parentElement.remove()">✕</button>
  `;
  container.appendChild(toast);

  setTimeout(() => {
    toast.style.opacity = '0';
    setTimeout(() => toast.remove(), 350);
  }, 4500);
}

// Fetch all dashboard data
async function fetchInitialData() {
  try {
    await Promise.all([
      loadDashboardSummary(),
      loadRecords(),
      loadHITLQueue(),
      loadLedger(),
      verifyLedgerChain(false) // silent check on boot
    ]);
  } catch (err) {
    console.error("Failed to load initial data:", err);
  }
}

// Load Summary & Metrics
async function loadDashboardSummary() {
  try {
    const res = await fetch('/api/reports/summary');
    if (!res.ok) return;
    const data = await res.json();

    const sum = data.summary || {};
    const scopes = data.scopes || {};

    const elTotal = document.getElementById('stat-total-tco2e');
    const elScope1 = document.getElementById('stat-scope1');
    const elScope2 = document.getElementById('stat-scope2');
    const elScope3 = document.getElementById('stat-scope3');
    const elConf = document.getElementById('stat-confidence');
    const elReady = document.getElementById('stat-readiness');

    if (elTotal) elTotal.innerText = formatNum(sum.total_tonnes_co2e || 0);
    if (elScope1) elScope1.innerText = formatNum(scopes.scope_1_direct_tco2e || 0);
    if (elScope2) elScope2.innerText = formatNum(scopes.scope_2_electricity_tco2e || 0);
    if (elScope3) elScope3.innerText = formatNum(scopes.scope_3_value_chain_tco2e || 0);
    if (elConf) elConf.innerText = sum.average_confidence_rating || "100%";
    if (elReady) elReady.innerText = sum.audit_readiness_score || "Grade A";

    renderDisclosureSection(data);
  } catch (err) {
    console.error("Error loading summary:", err);
  }
}

// Load Records Table
async function loadRecords() {
  try {
    const res = await fetch('/api/records');
    if (!res.ok) return;
    allRecords = await res.json();
    filterRecordsTable();
  } catch (err) {
    console.error("Error loading records:", err);
  }
}

function filterRecordsTable() {
  const scopeFilter = document.getElementById('filter-scope')?.value || 'ALL';
  const query = (document.getElementById('search-records')?.value || '').toLowerCase();
  const tbody = document.getElementById('records-tbody');
  if (!tbody) return;

  const filtered = allRecords.filter(r => {
    const rScope = (r.scope || '').toUpperCase();
    const matchScope = scopeFilter === 'ALL' || rScope === scopeFilter.toUpperCase();
    const matchQuery = !query ||
      (r.record_id || '').toLowerCase().includes(query) ||
      (r.supplier_or_facility || '').toLowerCase().includes(query) ||
      (r.activity_type || '').toLowerCase().includes(query);
    return matchScope && matchQuery;
  });

  if (filtered.length === 0) {
    tbody.innerHTML = `<tr><td colspan="10" class="empty-state">No audit records found. Ingest sample data or use the Data Intake Zone to begin.</td></tr>`;
    return;
  }

  tbody.innerHTML = filtered.map(r => {
    let pillClass = "pill-approved";
    if (r.status === "FLAGGED_HITL") pillClass = "pill-flagged";
    else if (r.status === "RESOLVED") pillClass = "pill-resolved";
    else if (r.status === "REJECTED") pillClass = "pill-rejected";

    const hashShort = r.ledger_block_hash && r.ledger_block_hash !== "PENDING"
      ? r.ledger_block_hash.substring(0, 8) + '...'
      : 'Genesis';
    const docRef = r.raw_document_ref || 'storage/raw/...';

    return `
      <tr>
        <td class="mono"><strong>${r.record_id}</strong></td>
        <td>${r.date || ''}</td>
        <td>${escapeHtml(r.supplier_or_facility || '')}</td>
        <td>${escapeHtml(r.activity_type || '')}</td>
        <td><span class="pill pill-scope">${r.scope || ''}</span></td>
        <td>${formatNum(r.quantity)} <span class="text-dim">${r.unit || ''}</span></td>
        <td><strong>${formatNum(r.tonnes_co2e, 4)}</strong></td>
        <td>${((r.confidence_score || 0) * 100).toFixed(0)}%</td>
        <td><span class="pill ${pillClass}">${r.status}</span></td>
        <td>
          <div style="font-size: 0.72rem; line-height: 1.3;" title="${escapeHtml(docRef)}">
            <span class="mono" style="color: var(--text-muted);">${escapeHtml(docRef.split('/').pop() || docRef)}</span>
            <br>
            <span class="mono" style="color: var(--brand-accent);" title="Ledger Hash: ${r.ledger_block_hash || ''}">#${hashShort}</span>
          </div>
        </td>
      </tr>
    `;
  }).join('');
}

// Load HITL Queue
async function loadHITLQueue() {
  try {
    const res = await fetch('/api/hitl/queue');
    if (!res.ok) return;
    hitlItems = await res.json();

    const countBadge = document.getElementById('hitl-badge-count');
    const pendingCount = hitlItems.filter(i => i.status === 'FLAGGED_HITL').length;
    if (countBadge) countBadge.innerText = pendingCount;

    const container = document.getElementById('hitl-cards-container');
    if (!container) return;

    const batchActions = document.getElementById('hitl-batch-actions');
    const btnAcceptAll = document.getElementById('btn-hitl-accept-all');
    const btnRejectAll = document.getElementById('btn-hitl-reject-all');
    const pendingItems = hitlItems.filter(i => i.status === 'FLAGGED_HITL');

    if (batchActions) {
      batchActions.style.display = 'flex';
    }
    if (btnAcceptAll) {
      btnAcceptAll.disabled = pendingItems.length === 0;
      btnAcceptAll.style.opacity = pendingItems.length === 0 ? '0.5' : '1';
      btnAcceptAll.style.cursor = pendingItems.length === 0 ? 'not-allowed' : 'pointer';
      btnAcceptAll.title = pendingItems.length === 0 ? 'No pending records to accept' : `Accept all ${pendingItems.length} pending records`;
      btnAcceptAll.innerHTML = `
        <svg style="width: 14px; height: 14px;" fill="none" viewBox="0 0 24 24" stroke="currentColor">
          <path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M5 13l4 4L19 7"/>
        </svg>
        Accept All (${pendingItems.length})
      `;
    }
    if (btnRejectAll) {
      btnRejectAll.disabled = pendingItems.length === 0;
      btnRejectAll.style.opacity = pendingItems.length === 0 ? '0.5' : '1';
      btnRejectAll.style.cursor = pendingItems.length === 0 ? 'not-allowed' : 'pointer';
      btnRejectAll.title = pendingItems.length === 0 ? 'No pending records to reject' : `Reject all ${pendingItems.length} pending records`;
      btnRejectAll.innerHTML = `
        <svg style="width: 14px; height: 14px;" fill="none" viewBox="0 0 24 24" stroke="currentColor">
          <path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M6 18L18 6M6 6l12 12"/>
        </svg>
        Reject All (${pendingItems.length})
      `;
    }

    if (pendingItems.length === 0) {
      container.innerHTML = `
        <div class="empty-state">
          <svg fill="none" viewBox="0 0 24 24" stroke="currentColor">
            <path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M9 12l2 2 4-4m6 2a9 9 0 11-18 0 9 9 0 0118 0z"/>
          </svg>
          <p>Zero flagged records. All ingested data cleared automated audit verification gates!</p>
          <p style="font-size: 0.8rem; color: var(--text-dim); margin-top: 6px;">Tip: Ingest <code>test_anomalies_and_duplicates.csv</code> in Data Intake Zone to trigger flagged HITL records.</p>
        </div>
      `;
      return;
    }

    container.innerHTML = pendingItems.map(item => {
      const rec = item.calculated_record;
      const reasons = item.flag_reasons.map(r => `<li>${escapeHtml(r)}</li>`).join('');

      return `
        <div class="content-card" style="border-left: 4px solid var(--amber-warn);">
          <div class="card-header">
            <div>
              <span class="pill pill-flagged" style="margin-bottom: 8px;">HUMAN REVIEW REQUIRED</span>
              <h3 style="font-size: 1.1rem;">Record ${rec.record_id} — ${escapeHtml(rec.supplier_or_facility)}</h3>
              <p style="font-size: 0.8rem; color: var(--text-dim); margin-top: 4px;">Flagged at: ${item.flagged_at.slice(0, 19).replace('T', ' ')}</p>
            </div>
            <div style="text-align: right;">
              <div style="font-size: 1.3rem; font-weight: 700; color: var(--amber-warn);">${formatNum(rec.tonnes_co2e, 4)} tCO2e</div>
              <div style="font-size: 0.75rem; color: var(--text-muted);">${rec.scope} &bull; ${rec.category}</div>
            </div>
          </div>

          <div style="background: rgba(0,0,0,0.25); padding: 14px; border-radius: var(--radius-md); margin-bottom: 16px;">
            <strong style="color: var(--amber-warn); font-size: 0.82rem; text-transform: uppercase;">Flag Reasons:</strong>
            <ul style="margin: 6px 0 0 18px; font-size: 0.85rem; color: #fca5a5;">
              ${reasons}
            </ul>
          </div>

          <div style="display: flex; gap: 10px; justify-content: flex-end;">
            <button class="btn btn-secondary btn-sm" onclick="openOverrideModal('${rec.record_id}', ${rec.activity_quantity}, '${rec.emission_factor_key}')">
              Adjust & Override
            </button>
            <button class="btn btn-danger btn-sm" onclick="resolveRecord('${rec.record_id}', 'reject')">
              Reject Record
            </button>
            <button class="btn btn-primary btn-sm" onclick="resolveRecord('${rec.record_id}', 'approve')">
              Approve As-Is
            </button>
          </div>
        </div>
      `;
    }).join('');
  } catch (err) {
    console.error("Error loading HITL queue:", err);
  }
}

// Load Cryptographic Audit Trail Ledger
async function loadLedger() {
  try {
    const res = await fetch('/api/ledger');
    if (!res.ok) return;
    allLedgerBlocks = await res.json();

    const tbody = document.getElementById('ledger-tbody');
    if (!tbody) return;

    const countBadge = document.getElementById('stat-ledger-blocks');
    if (countBadge) countBadge.innerText = allLedgerBlocks.length;

    if (allLedgerBlocks.length === 0) {
      tbody.innerHTML = `<tr><td colspan="7" class="empty-state">Ledger is empty.</td></tr>`;
      return;
    }

    // Show newest on top
    const sorted = [...allLedgerBlocks].reverse();

    tbody.innerHTML = sorted.map(b => {
      return `
        <tr>
          <td class="mono" style="font-weight: 700;">#${b.index}</td>
          <td>${b.timestamp.slice(11, 19)}</td>
          <td class="mono"><strong>${b.record_id}</strong></td>
          <td><span class="pill pill-scope">${b.agent_name}</span></td>
          <td style="font-size: 0.8rem;">${b.action}</td>
          <td>
            <span class="hash-tag mono" title="${b.previous_hash}">${b.previous_hash.slice(0, 10)}...</span>
          </td>
          <td>
            <span class="hash-tag mono" style="color: var(--emerald-glow); border: 1px solid rgba(16, 185, 129, 0.2);" title="${b.block_hash}">
              ${b.block_hash.slice(0, 10)}...
            </span>
          </td>
        </tr>
      `;
    }).join('');
  } catch (err) {
    console.error("Error loading ledger:", err);
  }
}

// Verify Ledger Integrity
async function verifyLedgerChain(notify = true) {
  const shouldNotify = (notify === true);

  try {
    const res = await fetch('/api/ledger/verify');
    const result = await res.json();

    const healthBadge = document.getElementById('stat-ledger-health');
    const tab3Badge = document.getElementById('tab3-verify-badge');

    if (result.is_valid) {
      if (healthBadge) healthBadge.innerHTML = `<span style="color: var(--emerald-glow);">CHAIN: 100% SECURE</span>`;
      if (tab3Badge) {
        tab3Badge.style.display = 'inline-block';
        tab3Badge.className = 'pill pill-approved mono';
        tab3Badge.innerText = `CHAIN INTACT (${result.chain_length} BLOCKS)`;
      }
      if (shouldNotify) {
        showToast(`Cryptographic Audit Trail Verified: All ${result.chain_length} blocks verified with intact SHA-256 chain links.`, 'success');
      }
    } else {
      if (healthBadge) healthBadge.innerHTML = `<span style="color: var(--rose-alert);">INTEGRITY COMPROMISED</span>`;
      if (tab3Badge) {
        tab3Badge.style.display = 'inline-block';
        tab3Badge.className = 'pill pill-rejected mono';
        tab3Badge.innerText = 'INTEGRITY COMPROMISED';
      }
      if (shouldNotify) {
        showToast(`TAMPERING DETECTED: ${result.message}`, 'error');
      }
    }
  } catch (err) {
    console.error("Verification failed", err);
    if (shouldNotify) {
      showToast("Verification failed: " + err, 'error');
    }
  }
}

// Ingest All Sample Files with 1 click
async function runSampleIngestion() {
  const btn = document.getElementById('btn-ingest-sample');
  if (btn) {
    btn.disabled = true;
    btn.innerText = "Ingesting Multi-Source Data...";
  }

  showToast("Ingesting multi-source sample data (Invoices + ERP + Utility)...", "info");

  try {
    const res = await fetch('/api/sample/ingest_all', { method: 'POST' });
    const data = await res.json();
    if (data.success) {
      showToast("Sample Data Ingested! 14 multi-source records audited & chained.", "success");
      await fetchInitialData();
      switchToTab('tab-records');
    } else {
      showToast("Sample ingestion error: " + (data.error || "Unknown"), "error");
    }
  } catch (err) {
    showToast("Sample ingestion failed: " + err, "error");
  } finally {
    if (btn) {
      btn.disabled = false;
      btn.innerHTML = `
        <svg style="width: 16px; height: 16px;" fill="none" viewBox="0 0 24 24" stroke="currentColor">
          <path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M13 10V3L4 14h7v7l9-11h-7z"/>
        </svg>
        Ingest Sample Data (Invoices + ERP + Utility)
      `;
    }
  }
}
// Load Named Test File from Pre-loaded Library
async function loadNamedSample(filename, hint = "auto") {
  showToast(`Loading test file: ${filename}...`, 'info');
  try {
    const res = await fetch('/api/sample/load_named', {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({ filename, hint })
    });
    const result = await res.json();
    if (result.success) {
      showToast(`Test Dataset '${filename}' processed & ledgered!`, 'success');
      await fetchInitialData();
      switchToTab('tab-records');
    } else {
      showToast("Failed to load test dataset: " + result.error, 'error');
    }
  } catch (err) {
    showToast("Error loading test dataset: " + err, 'error');
  }
}

// Data Intake Zone Event Bindings
function initIntakeZone() {
  // 1. Manual Entry Form
  document.getElementById('form-manual-entry')?.addEventListener('submit', async (e) => {
    e.preventDefault();
    const vendor = document.getElementById('manual-vendor').value.trim();
    const date = document.getElementById('manual-date').value;
    const activity = document.getElementById('manual-activity').value;
    const qty = parseFloat(document.getElementById('manual-qty').value);
    const unit = document.getElementById('manual-unit').value.trim();

    const submitBtn = document.getElementById('btn-submit-manual');
    if (submitBtn) {
      submitBtn.disabled = true;
      submitBtn.innerText = "Auditing Transaction...";
    }

    try {
      const res = await fetch('/api/ingest/direct', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({
          supplier: vendor,
          date: date,
          activity: activity,
          quantity: qty,
          unit: unit
        })
      });
      const data = await res.json();
      if (data.success) {
        showToast(`Transaction ${data.record_id} audited and chained to ledger!`, 'success');
        document.getElementById('form-manual-entry').reset();
        await fetchInitialData();
        switchToTab('tab-records');
      } else {
        showToast("Submission error: " + (data.error || "Unknown"), 'error');
      }
    } catch (err) {
      showToast("Manual submission failed: " + err, 'error');
    } finally {
      if (submitBtn) {
        submitBtn.disabled = false;
        submitBtn.innerText = "Audit & Chain Transaction";
      }
    }
  });

  // 2. Raw Snippet Submission
  document.getElementById('btn-submit-snippet')?.addEventListener('click', async () => {
    const rawText = document.getElementById('raw-snippet-text')?.value;
    const hint = document.getElementById('raw-snippet-hint')?.value || 'invoice';
    if (!rawText || !rawText.trim()) {
      showToast("Please enter CSV rows or JSON records first.", "error");
      return;
    }

    showToast("Processing raw snippet...", "info");
    try {
      const res = await fetch('/api/ingest/direct', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ raw_text: rawText, source_type: hint })
      });
      const data = await res.json();
      if (data.success) {
        showToast(`Snippet ingested into ${data.raw_document_ref}!`, 'success');
        document.getElementById('raw-snippet-text').value = '';
        await fetchInitialData();
        switchToTab('tab-records');
      } else {
        showToast("Snippet processing error: " + data.error, 'error');
      }
    } catch (err) {
      showToast("Snippet ingestion failed: " + err, 'error');
    }
  });

  // 3. Dropzone File Input
  const intakeInput = document.getElementById('intake-file-input');
  intakeInput?.addEventListener('change', async (e) => {
    const file = e.target.files[0];
    if (!file) return;
    const hint = document.getElementById('intake-source-hint')?.value || 'auto';
    await uploadFileToRaw(file, hint);
  });

  // 4. Drag & Drop
  const dropzone = document.getElementById('intake-dropzone');
  if (dropzone) {
    dropzone.addEventListener('dragover', (e) => {
      e.preventDefault();
      dropzone.classList.add('dragover');
    });
    dropzone.addEventListener('dragleave', () => dropzone.classList.remove('dragover'));
    dropzone.addEventListener('drop', async (e) => {
      e.preventDefault();
      dropzone.classList.remove('dragover');
      if (e.dataTransfer.files && e.dataTransfer.files.length > 0) {
        const file = e.dataTransfer.files[0];
        const hint = document.getElementById('intake-source-hint')?.value || 'auto';
        await uploadFileToRaw(file, hint);
      }
    });
  }
}

async function uploadFileToRaw(file, hint) {
  const formData = new FormData();
  formData.append('file', file);
  formData.append('source_hint', hint);

  showToast(`Uploading ${file.name} to immutable raw storage...`, 'info');
  try {
    const res = await fetch('/api/ingest', { method: 'POST', body: formData });
    const result = await res.json();
    if (result.success) {
      showToast(`File ${result.filename} uploaded and audited successfully!`, 'success');
      await fetchInitialData();
      switchToTab('tab-records');
    } else {
      showToast("Upload failed: " + result.error, 'error');
    }
  } catch (err) {
    showToast("Upload error: " + err, 'error');
  }
}

// Topbar File Upload
async function handleFileUpload(e) {
  const file = e.target.files[0];
  if (!file) return;
  await uploadFileToRaw(file, 'auto');
}

// Resolve Record Actions
async function resolveRecord(recordId, action, notes = "Audited via UI", qty = null, factor = null) {
  try {
    const res = await fetch('/api/hitl/resolve', {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({
        record_id: recordId,
        reviewer_name: "Lead Sustainability Auditor",
        action: action,
        notes: notes,
        adjusted_quantity: qty,
        adjusted_factor_key: factor
      })
    });
    const result = await res.json();
    if (result.success) {
      showToast(`Record ${recordId} resolved as [${action.toUpperCase()}] and chained!`, 'success');
      await fetchInitialData();
    } else {
      showToast("Resolution error: " + result.error, 'error');
    }
  } catch (err) {
    showToast("Failed to resolve: " + err, 'error');
  }
}

// Resolve All HITL Records (Accept All / Reject All)
async function resolveAllHITL(action) {
  const isApprove = action === 'approve' || action === 'accept';
  const actionLabel = isApprove ? 'Accept' : 'Reject';
  const pending = hitlItems.filter(i => i.status === 'FLAGGED_HITL');
  if (pending.length === 0) {
    showToast("No pending records to " + actionLabel.toLowerCase(), "info");
    return;
  }

  if (!confirm(`Are you sure you want to ${actionLabel.toUpperCase()} all ${pending.length} pending flagged records?`)) {
    return;
  }

  showToast(`Processing batch ${actionLabel.toLowerCase()} for ${pending.length} records...`, "info");
  try {
    const res = await fetch('/api/hitl/resolve_all', {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({
        action: isApprove ? 'approve' : 'reject',
        reviewer_name: "Lead Sustainability Auditor",
        notes: `Batch ${actionLabel.toLowerCase()}ed via HITL queue dashboard`
      })
    });
    const result = await res.json();
    if (result.success) {
      showToast(`Batch Complete: ${result.count} records ${actionLabel.toLowerCase()}ed & chained to ledger!`, 'success');
      await fetchInitialData();
    } else {
      showToast("Batch resolution error: " + (result.error || "Unknown"), 'error');
    }
  } catch (err) {
    showToast("Batch resolution failed: " + err, 'error');
  }
}

// Override Modal Logic
let currentOverrideRecordId = null;

function openOverrideModal(recordId, currentQty, currentFactor) {
  currentOverrideRecordId = recordId;
  const modal = document.getElementById('override-modal');
  document.getElementById('modal-record-id').innerText = recordId;
  document.getElementById('modal-qty').value = currentQty;
  document.getElementById('modal-notes').value = "Adjusted after manual invoice inspection";
  if (modal) modal.classList.add('active');
}

function closeOverrideModal() {
  const modal = document.getElementById('override-modal');
  if (modal) modal.classList.remove('active');
  currentOverrideRecordId = null;
}

document.getElementById('modal-btn-save')?.addEventListener('click', async () => {
  if (!currentOverrideRecordId) return;
  const newQty = parseFloat(document.getElementById('modal-qty').value);
  const factor = document.getElementById('modal-factor-select').value;
  const notes = document.getElementById('modal-notes').value;

  await resolveRecord(currentOverrideRecordId, 'override', notes, newQty, factor || null);
  closeOverrideModal();
});

// JSON Viewer Modal Logic
async function openJsonModal() {
  const modal = document.getElementById('json-modal');
  const pre = document.getElementById('json-modal-content');
  if (modal) modal.classList.add('active');
  if (pre) pre.innerText = "Loading latest carbon disclosure JSON...";

  try {
    const res = await fetch('/api/reports/summary');
    const data = await res.json();
    if (pre) pre.innerText = JSON.stringify(data, null, 2);
  } catch (err) {
    if (pre) pre.innerText = "Error loading report: " + err;
  }
}

function closeJsonModal() {
  const modal = document.getElementById('json-modal');
  if (modal) modal.classList.remove('active');
}

function copyJsonToClipboard() {
  const pre = document.getElementById('json-modal-content');
  if (!pre) return;
  navigator.clipboard.writeText(pre.innerText).then(() => {
    showToast("Carbon disclosure JSON copied to clipboard!", "success");
  }).catch(err => {
    showToast("Could not copy: " + err, "error");
  });
}

// Render Executive Board Disclosure Section
function renderDisclosureSection(data) {
  const disclosureContainer = document.getElementById('disclosure-view');
  if (!disclosureContainer) return;

  const categories = data.categories || [];
  const topEmitters = data.top_emitters || [];

  const catRows = categories.map(c => `
    <tr>
      <td>${escapeHtml(c.category)}</td>
      <td style="text-align: right; font-weight: 600;">${formatNum(c.tonnes_co2e, 4)} tCO2e</td>
    </tr>
  `).join('');

  const emitterRows = topEmitters.slice(0, 5).map(e => `
    <tr>
      <td>${escapeHtml(e.name)}</td>
      <td style="text-align: right; font-weight: 600;">${formatNum(e.tonnes_co2e, 4)} tCO2e</td>
    </tr>
  `).join('');

  disclosureContainer.innerHTML = `
    <div style="display: grid; grid-template-columns: 1fr 1fr; gap: 20px;">
      <div class="content-card">
        <h4 style="margin-bottom: 14px;">Emissions by Activity Category</h4>
        <table>
          <tbody>${catRows || '<tr><td>No data</td></tr>'}</tbody>
        </table>
      </div>
      <div class="content-card">
        <h4 style="margin-bottom: 14px;">Top Emitting Suppliers / Facilities</h4>
        <table>
          <tbody>${emitterRows || '<tr><td>No data</td></tr>'}</tbody>
        </table>
      </div>
    </div>
  `;
}

// Helpers
function formatNum(val, decimals = 2) {
  if (val === undefined || val === null || isNaN(val)) return '0.00';
  return Number(val).toLocaleString(undefined, { minimumFractionDigits: decimals, maximumFractionDigits: decimals });
}

function escapeHtml(str) {
  if (!str) return '';
  return str.toString()
    .replace(/&/g, '&amp;')
    .replace(/</g, '&lt;')
    .replace(/>/g, '&gt;')
    .replace(/"/g, '&quot;')
    .replace(/'/g, '&#039;');
}
