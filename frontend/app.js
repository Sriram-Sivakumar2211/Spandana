document.addEventListener("DOMContentLoaded", () => {
  const machineSelect = document.getElementById("machineSelect");
  const healthScoreVal = document.getElementById("healthScoreVal");
  const healthGauge = document.getElementById("healthGauge");
  const anomalyScoreVal = document.getElementById("anomalyScoreVal");
  const faultProbVal = document.getElementById("faultProbVal");
  const rulVal = document.getElementById("rulVal");

  const predictedFaultBadge = document.getElementById("predictedFaultBadge");
  const predFaultText = document.getElementById("predFaultText");
  const predConfidenceText = document.getElementById("predConfidenceText");
  const windowIdText = document.getElementById("windowIdText");
  const timestampText = document.getElementById("timestampText");

  const urgencyBadge = document.getElementById("urgencyBadge");
  const reportTitle = document.getElementById("reportTitle");
  const reportSummary = document.getElementById("reportSummary");
  const evidenceList = document.getElementById("evidenceList");
  const likelyCauseText = document.getElementById("likelyCauseText");
  const actionList = document.getElementById("actionList");
  const notesText = document.getElementById("notesText");
  const sourcesList = document.getElementById("sourcesList");

  const btnHealthy = document.getElementById("btnSimulateHealthy");
  const btnWarning = document.getElementById("btnSimulateWarning");
  const btnCritical = document.getElementById("btnSimulateCritical");

  // Fetch initial system health
  fetchSystemHealth();

  // Machine selector event
  machineSelect.addEventListener("change", () => {
    simulatePrediction("healthy");
  });

  btnHealthy.addEventListener("click", () => simulatePrediction("healthy"));
  btnWarning.addEventListener("click", () => simulatePrediction("warning"));
  btnCritical.addEventListener("click", () => simulatePrediction("critical"));

  // Initial load
  simulatePrediction("healthy");

  async function fetchSystemHealth() {
    try {
      const resp = await fetch("/api/v1/health");
      if (resp.ok) {
        const data = await resp.json();
        const el = document.getElementById("systemHealthText");
        if (el) {
          el.textContent = `RAG & LLM Online (${data.knowledge_base.total_chunks} KB Chunks)`;
        }
      }
    } catch (err) {
      console.warn("Backend API offline, using interactive local state.");
    }
  }

  async function simulatePrediction(type) {
    const machineId = machineSelect.value;
    const nowIso = new Date().toISOString();

    let predPayload;
    if (type === "healthy") {
      predPayload = {
        machine_id: machineId,
        window_id: `${machineId}_win_${Date.now()}`,
        timestamp: nowIso,
        health_score: 98.0,
        anomaly_score: 0.08,
        fault_probability: 0.02,
        predicted_fault: "Healthy",
        prediction_confidence: 0.96,
        remaining_useful_life_hours: 124.5,
        recommended_action: "No action required. Machine operating normally."
      };
    } else if (type === "warning") {
      predPayload = {
        machine_id: machineId,
        window_id: `${machineId}_win_${Date.now()}`,
        timestamp: nowIso,
        health_score: 65.0,
        anomaly_score: 0.38,
        fault_probability: 0.35,
        predicted_fault: "Bearing Wear Warning",
        prediction_confidence: 0.74,
        remaining_useful_life_hours: 48.0,
        recommended_action: "Schedule inspection during the next planned maintenance window."
      };
    } else {
      predPayload = {
        machine_id: machineId,
        window_id: `${machineId}_win_${Date.now()}`,
        timestamp: nowIso,
        health_score: 14.5,
        anomaly_score: 0.82,
        fault_probability: 0.865,
        predicted_fault: "Inner Race Fault",
        prediction_confidence: 0.91,
        remaining_useful_life_hours: 6.2,
        recommended_action: "Immediate inspection recommended -- elevated risk of failure."
      };
    }

    try {
      const resp = await fetch("/api/v1/dashboard/machine-status", {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify(predPayload)
      });

      if (resp.ok) {
        const dashboardData = await resp.json();
        renderDashboard(dashboardData);
        return;
      }
    } catch (err) {
      console.warn("API request failed, rendering local client view.", err);
    }

    // Fallback client renderer
    renderLocalFallback(predPayload);
  }

  function renderDashboard(data) {
    const pred = data.prediction;
    const rpt = data.report;
    const ret = data.retrieval;

    // Health Score & Gauge
    const score = pred.health_score;
    healthScoreVal.textContent = score.toFixed(1);
    
    let color = "#10b981"; // success
    if (score < 50) color = "#ef4444";
    else if (score < 85) color = "#f59e0b";

    healthScoreVal.style.color = color;
    const deg = Math.round((score / 100) * 360);
    healthGauge.style.background = `conic-gradient(${color} 0deg ${deg}deg, #1f2937 ${deg}deg 360deg)`;
    healthGauge.style.boxShadow = `0 0 20px ${color}66`;

    anomalyScoreVal.textContent = pred.anomaly_score.toFixed(4);
    faultProbVal.textContent = (pred.fault_probability * 100).toFixed(1) + "%";
    rulVal.textContent = pred.remaining_useful_life_hours ? pred.remaining_useful_life_hours.toFixed(1) + " hrs" : "N/A";

    // LNN Prediction Card
    predFaultText.textContent = pred.predicted_fault;
    predConfidenceText.textContent = (pred.prediction_confidence * 100).toFixed(1) + "%";
    windowIdText.textContent = pred.window_id;
    timestampText.textContent = pred.timestamp;

    predictedFaultBadge.textContent = pred.predicted_fault;
    predictedFaultBadge.className = "badge";
    if (score < 50) predictedFaultBadge.classList.add("badge-danger");
    else if (score < 85) predictedFaultBadge.classList.add("badge-warning");

    // Report Card
    reportTitle.textContent = rpt.title;
    reportSummary.textContent = rpt.summary;
    likelyCauseText.textContent = rpt.likely_cause;
    notesText.textContent = rpt.notes;
    urgencyBadge.textContent = rpt.urgency;

    evidenceList.innerHTML = "";
    (rpt.evidence || []).forEach(item => {
      const li = document.createElement("li");
      li.textContent = item;
      evidenceList.appendChild(li);
    });

    actionList.innerHTML = "";
    (rpt.recommended_action || []).forEach(item => {
      const li = document.createElement("li");
      li.textContent = item;
      actionList.appendChild(li);
    });

    // Knowledge Base Sources
    sourcesList.innerHTML = "";
    (ret.chunks || []).forEach(chunk => {
      const div = document.createElement("div");
      div.className = "source-item";
      div.innerHTML = `
        <div class="source-item-header">
          <span class="source-title">${escapeHtml(chunk.title)}</span>
          <span class="source-score">Match ${(chunk.relevance_score * 100).toFixed(0)}%</span>
        </div>
        <div class="source-file">Source: ${escapeHtml(chunk.source_file)}</div>
        <div class="source-snippet">${escapeHtml(chunk.text.substring(0, 150))}...</div>
      `;
      sourcesList.appendChild(div);
    });
  }

  function renderLocalFallback(pred) {
    const score = pred.health_score;
    healthScoreVal.textContent = score.toFixed(1);
    anomalyScoreVal.textContent = pred.anomaly_score.toFixed(4);
    faultProbVal.textContent = (pred.fault_probability * 100).toFixed(1) + "%";
    rulVal.textContent = pred.remaining_useful_life_hours ? pred.remaining_useful_life_hours.toFixed(1) + " hrs" : "N/A";

    predFaultText.textContent = pred.predicted_fault;
    predConfidenceText.textContent = (pred.prediction_confidence * 100).toFixed(1) + "%";
    windowIdText.textContent = pred.window_id;
    timestampText.textContent = pred.timestamp;

    reportTitle.textContent = `${pred.machine_id} — ${pred.predicted_fault}`;
    reportSummary.textContent = `Machine ${pred.machine_id} diagnosed with ${pred.predicted_fault}. Health score evaluated at ${score}%.`;
    likelyCauseText.textContent = `Vibration harmonic and envelope spectrum signatures align with ${pred.predicted_fault}.`;
    notesText.textContent = "Enforce Lockout/Tagout (LOTO) protocols prior to physical inspection.";

    evidenceList.innerHTML = `<li>LTC model prediction: ${pred.predicted_fault} with ${(pred.prediction_confidence*100).toFixed(1)}% confidence.</li>`;
    actionList.innerHTML = `<li>${pred.recommended_action}</li>`;

    sourcesList.innerHTML = `
      <div class="source-item">
        <div class="source-item-header">
          <span class="source-title">Inner Race Fault Maintenance Guide</span>
          <span class="source-score">Match 92%</span>
        </div>
        <div class="source-file">Source: bearing_faults/inner_race_fault.md</div>
        <div class="source-snippet">An inner race bearing fault occurs when micro-spalling or fatigue cracking develops along the inner raceway...</div>
      </div>
    `;
  }

  function escapeHtml(str) {
    return str.replace(/&/g, "&amp;").replace(/</g, "&lt;").replace(/>/g, "&gt;");
  }
});
