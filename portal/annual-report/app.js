const SKILL_ID = "annual-report";
const $ = (s) => document.querySelector(s);
const $$ = (s) => document.querySelectorAll(s);

const state = {
  pdfFile: null,
  extraPdfFiles: [],
  templateFile: null,
  resultMarkdown: "",
  currentMeta: {},
  currentMetrics: null,
  currentVerification: null,
  currentReportId: null,
  sections: [],
  pollTimer: null,
  defaultModel: "",
  traceSteps: {},
  runStartedAt: null,
};

const PHASE_LABELS = {
  extract: "解析 PDF",
  analyze: "分章 AI 分析",
  verify: "指标抽取与校验",
  save: "保存报告",
  idle: "待命",
};

function escHtml(s) {
  return String(s)
    .replace(/&/g, "&amp;")
    .replace(/</g, "&lt;")
    .replace(/>/g, "&gt;");
}

function appendChat(role, html, cls = "") {
  const box = $("#chatMessages");
  const div = document.createElement("div");
  div.className = `msg ${role} ${cls}`.trim();
  const avatar = role === "user" ? "我" : role === "system" ? "⚙" : "AI";
  div.innerHTML = `<div class="msg-avatar">${avatar}</div><div class="msg-body">${html}</div>`;
  box.appendChild(div);
  box.scrollTop = box.scrollHeight;
}

function appendChatText(role, text) {
  appendChat(role, `<p>${escHtml(text).replace(/\n/g, "<br>")}</p>`);
}

function clearTrace() {
  state.traceSteps = {};
  state.runStartedAt = Date.now();
  const tl = $("#traceTimeline");
  tl.innerHTML = "";
}

function upsertTraceStep(id, { title, detail, status = "running" }) {
  const tl = $("#traceTimeline");
  let li = state.traceSteps[id]?.el;
  if (!li) {
    li = document.createElement("li");
    li.className = `trace-item ${status}`;
    li.dataset.step = id;
    li.innerHTML = `
      <span class="trace-dot"></span>
      <div class="trace-content">
        <strong></strong>
        <p></p>
        <span class="trace-time"></span>
      </div>`;
    tl.appendChild(li);
    state.traceSteps[id] = { el: li, started: Date.now() };
  }
  li.className = `trace-item ${status}`;
  li.querySelector("strong").textContent = title;
  li.querySelector("p").textContent = detail || "";
  const elapsed = Math.round((Date.now() - (state.traceSteps[id].started || state.runStartedAt)) / 1000);
  li.querySelector(".trace-time").textContent = status === "done" ? `耗时 ${elapsed}s` : status === "running" ? "进行中…" : "";
}

function initTracePlan() {
  clearTrace();
  upsertTraceStep("plan", { title: "规划任务", detail: "提取 PDF → 按章选页 → 生成报告 → 校验数字", status: "done" });
  upsertTraceStep("extract", { title: PHASE_LABELS.extract, detail: "等待开始…", status: "running" });
}

function updateTraceFromJob(data) {
  const phase = data.phase || "analyze";
  const pct = data.progress || 0;
  const msg = data.message || "";

  if (phase === "extract" || pct <= 20) {
    upsertTraceStep("extract", { title: PHASE_LABELS.extract, detail: msg, status: pct >= 15 ? "done" : "running" });
    if (pct >= 15) {
      upsertTraceStep("analyze", { title: PHASE_LABELS.analyze, detail: "准备分章生成…", status: "running" });
    }
  } else if (phase === "analyze" || (pct > 20 && pct < 88)) {
    upsertTraceStep("extract", { title: PHASE_LABELS.extract, detail: "PDF 文本已就绪", status: "done" });
    upsertTraceStep("analyze", { title: PHASE_LABELS.analyze, detail: msg, status: "running" });
  } else if (phase === "verify" || pct >= 88) {
    upsertTraceStep("analyze", { title: PHASE_LABELS.analyze, detail: "各章节已生成", status: "done" });
    upsertTraceStep("verify", { title: PHASE_LABELS.verify, detail: msg, status: pct >= 95 ? "done" : "running" });
  }

  if (data.status === "completed") {
    upsertTraceStep("extract", { title: PHASE_LABELS.extract, detail: "完成", status: "done" });
    upsertTraceStep("analyze", { title: PHASE_LABELS.analyze, detail: "完成", status: "done" });
    upsertTraceStep("verify", { title: PHASE_LABELS.verify, detail: "完成", status: "done" });
    upsertTraceStep("save", { title: PHASE_LABELS.save, detail: "报告已写入历史", status: "done" });
  }
}

function renderReflection(meta, verification, markdown) {
  const body = $("#reflectionBody");
  if (!markdown) {
    body.innerHTML = '<p class="empty-reflect">分析完成后，将基于数字校验与覆盖情况生成复盘摘要</p>';
    return;
  }

  const score = verification?.score ?? meta?.verification_score;
  const pct = score != null ? Math.round(score * 100) : null;
  const undisclosed = (markdown.match(/未披露|待补充/g) || []).length;
  const truncated = meta?.text_truncated;
  const pages = meta?.pages_used != null && meta?.page_count != null
    ? `${meta.pages_used}/${meta.page_count} 页`
    : null;

  const lines = [];
  if (pct != null) {
    const cls = pct >= 70 ? "ok-line" : "warn-line";
    lines.push(`<p class="score-line ${cls}">数字校验 ${pct}%（${verification?.matched_count ?? "?"}/${verification?.checked_count ?? "?"} 匹配）</p>`);
  }
  lines.push("<ul>");
  if (pages) lines.push(`<li>PDF 覆盖：${pages}${truncated ? "，<span class='warn-line'>未读全篇</span>" : ""}</li>`);
  if (meta?.section_read_mode) lines.push("<li>已启用按章节分读 PDF（各章独立选页）</li>");
  if (undisclosed > 8) lines.push(`<li class="warn-line">「未披露/待补充」出现 ${undisclosed} 次，附注或明细可能不足</li>`);
  if (pct != null && pct < 70) {
    lines.push("<li class='warn-line'>建议：在轨迹区重跑「财务分析」章节，或扩大 PDF 页数上限</li>");
  } else if (pct != null && pct >= 70) {
    lines.push("<li class='ok-line'>核心数字与 PDF 对齐较好，建议人工抽查页码引用</li>");
  }
  if (verification?.issues?.length) {
    lines.push(`<li>未匹配项 ${verification.issues.length} 条（见指标 Tab）</li>`);
  }
  lines.push("</ul>");
  lines.push("<p style='margin-top:8px;color:#94a3b8;font-size:0.75rem'>后续版本将支持一键自动优化重跑</p>");
  body.innerHTML = lines.join("");
}

function renderMetricCards(metrics) {
  const el = $("#metricCards");
  if (!metrics || typeof metrics !== "object") {
    el.innerHTML = "";
    return;
  }
  const items = [
    { key: "revenue", label: "营业收入", suffix: metrics.revenue_unit || "亿" },
    { key: "revenue_yoy", label: "营收同比", suffix: "%", prefix: metrics.revenue_yoy > 0 ? "+" : "" },
    { key: "net_profit", label: "归母净利润", suffix: metrics.net_profit_unit || "亿" },
    { key: "net_profit_yoy", label: "利润同比", suffix: "%", prefix: metrics.net_profit_yoy > 0 ? "+" : "" },
    { key: "roe", label: "ROE", suffix: "%" },
    { key: "verification_score", label: "校验分", suffix: "%", scale: 100 },
  ];
  const cards = items
    .filter((it) => metrics[it.key] != null && metrics[it.key] !== "")
    .map((it) => {
      let val = metrics[it.key];
      if (it.scale) val = Math.round(val * it.scale);
      else if (typeof val === "number" && !Number.isInteger(val)) val = val.toFixed(2);
      const prefix = it.prefix || "";
      return `<div class="metric-card"><div class="label">${it.label}</div><div class="value">${prefix}${val}${it.suffix || ""}</div></div>`;
    });
  el.innerHTML = cards.length ? cards.join("") : "";
}

function showProgress(show, pct = 0, msg = "") {
  $("#progressBlock").classList.toggle("hidden", !show);
  $("#progressFill").style.width = `${Math.min(100, pct)}%`;
  if (msg) $("#progressMsg").textContent = msg;
  $("#btnRun").disabled = show;
  $("#btnAgent").disabled = show;
}

async function checkStatus() {
  const badge = $("#statusBadge");
  try {
    const res = await fetch(`/api/${SKILL_ID}/status`);
    const data = await res.json();
    badge.textContent = data.status === "ready" ? "在线" : "待配置";
    badge.className = `badge ${data.status === "ready" ? "ready" : "scaffold"}`;
    $("#statusOut").textContent = (data.message || "") + (data.ocr_available ? " · OCR 可用" : "");
  } catch {
    badge.textContent = "离线";
    $("#statusOut").textContent = "请启动 portal 服务";
  }
}

async function loadModels() {
  const sel = $("#modelSelect");
  try {
    const res = await fetch("/api/models");
    const data = await res.json();
    state.defaultModel = data.default_model || "";
    sel.innerHTML = "";
    for (const g of data.groups || []) {
      for (const m of g.models || []) {
        if (!m.available) continue;
        const o = document.createElement("option");
        o.value = m.id;
        o.textContent = m.name + (m.id === data.default_model ? "（默认）" : "");
        sel.appendChild(o);
      }
    }
    if (state.defaultModel) {
      sel.value = state.defaultModel;
      $("#modelPill").textContent = state.defaultModel;
    }
    sel.addEventListener("change", () => {
      $("#modelPill").textContent = sel.value || "—";
    });
  } catch {
    sel.innerHTML = '<option value="">未配置 Key</option>';
  }
}

async function loadTemplate() {
  try {
    const res = await fetch(`/api/${SKILL_ID}/template`);
    const data = await res.json();
    $("#templatePreview").textContent = data.template;
  } catch (e) {
    $("#templatePreview").textContent = "加载失败: " + e.message;
  }
}

async function loadSections() {
  try {
    const res = await fetch(`/api/${SKILL_ID}/sections`);
    const data = await res.json();
    state.sections = data.sections || [];
    const sel = $("#sectionSelect");
    sel.innerHTML = '<option value="">选择章节</option>';
    state.sections.forEach((s) => {
      const o = document.createElement("option");
      o.value = s.section_id;
      o.textContent = s.title;
      sel.appendChild(o);
    });
  } catch { /* ignore */ }
}

async function loadHistory() {
  const list = $("#historyList");
  try {
    const res = await fetch(`/api/${SKILL_ID}/reports?limit=15`);
    const data = await res.json();
    const reports = data.reports || [];
    if (!reports.length) {
      list.innerHTML = '<li class="empty">暂无</li>';
      return;
    }
    list.innerHTML = "";
    reports.forEach((r) => {
      const li = document.createElement("li");
      const label = [r.company_name, r.report_year].filter(Boolean).join(" ") || r.report_id;
      li.innerHTML = `<button type="button" class="history-btn">${escHtml(label)}</button><span class="history-meta">${(r.saved_at || "").slice(0, 16)}</span>`;
      li.querySelector("button").onclick = () => openReport(r.report_id);
      list.appendChild(li);
    });
  } catch {
    list.innerHTML = '<li class="empty">加载失败</li>';
  }
}

function setupDropzone(zoneId, inputId, onFile, multiple = false) {
  const zone = $(zoneId);
  const input = $(inputId);
  zone.onclick = () => input.click();
  zone.ondragover = (e) => { e.preventDefault(); zone.classList.add("dragover"); };
  zone.ondragleave = () => zone.classList.remove("dragover");
  zone.ondrop = (e) => {
    e.preventDefault();
    zone.classList.remove("dragover");
    if (multiple) onFile([...e.dataTransfer.files]);
    else if (e.dataTransfer.files[0]) onFile(e.dataTransfer.files[0]);
  };
  input.onchange = () => {
    if (multiple) onFile([...input.files]);
    else if (input.files[0]) onFile(input.files[0]);
  };
}

function setPdfFile(file) {
  if (!file.name.toLowerCase().endsWith(".pdf")) return alert("请选 PDF");
  state.pdfFile = file;
  $("#pdfLabel").textContent = file.name;
  $("#pdfDropzone").classList.add("has-file");
  appendChatText("system", `已选择主 PDF：${file.name}`);
}

function setExtraPdfs(files) {
  state.extraPdfFiles = files.filter((f) => f.name.toLowerCase().endsWith(".pdf"));
  $("#extraPdfLabel").textContent = state.extraPdfFiles.length
    ? state.extraPdfFiles.map((f) => f.name).join(", ")
    : "多选其他年度";
  if (state.extraPdfFiles.length) {
    $("#extraPdfDropzone").classList.add("has-file");
    appendChatText("system", `已添加 ${state.extraPdfFiles.length} 个对比 PDF`);
  }
}

function setTemplateFile(file) {
  state.templateFile = file;
  $("#tplLabel").textContent = file.name;
  $("#tplDropzone").classList.add("has-file");
}

function switchTab(name) {
  $$(".artifact-tabs .tab").forEach((t) => t.classList.toggle("active", t.dataset.tab === name));
  ["template", "result", "metrics"].forEach((id) => {
    $(`#panel${id.charAt(0).toUpperCase() + id.slice(1)}`).classList.toggle("active", id === name);
  });
}

function setExportEnabled(on) {
  ["btnCopy", "btnExportMd", "btnExportDocx", "btnExportPdf", "btnExportXlsx", "btnCompetitorLink", "btnRerunSection"].forEach((id) => {
    $(`#${id}`).disabled = !on;
  });
}

function renderMetricsPanel(metrics, verification) {
  $("#metricsPreview").textContent = metrics ? JSON.stringify(metrics, null, 2) : "暂无";
  $("#verificationPreview").textContent = verification ? JSON.stringify(verification, null, 2) : "暂无";
  renderMetricCards(metrics);
  const banner = $("#verifyBanner");
  if (verification && verification.score != null) {
    banner.classList.remove("hidden");
    const pct = Math.round(verification.score * 100);
    banner.textContent = `数字校验：${verification.matched_count}/${verification.checked_count} 匹配（${pct}%）`;
    banner.className = "verify-banner " + (pct >= 70 ? "ok" : "warn");
  } else {
    banner.classList.add("hidden");
  }
}

function renderResult(markdown, meta, metrics, verification) {
  state.resultMarkdown = markdown;
  state.currentMeta = meta || {};
  state.currentMetrics = metrics;
  state.currentVerification = verification;
  state.currentReportId = meta?.report_id || null;
  $("#resultPreview").innerHTML = marked.parse(markdown);
  $("#resultRaw").textContent = markdown;
  const parts = [];
  if (meta?.company_name) parts.push(meta.company_name);
  if (meta?.report_year) parts.push(meta.report_year);
  if (meta?.filename) parts.push(meta.filename);
  if (meta?.pages_used != null) parts.push(`${meta.pages_used}/${meta.page_count || "?"} 页`);
  if (meta?.verification_score != null) parts.push(`校验 ${Math.round(meta.verification_score * 100)}%`);
  if (meta?.report_id) parts.push(meta.report_id);
  $("#resultMeta").textContent = parts.join(" · ");
  renderMetricsPanel(metrics, verification);
  renderReflection(meta, verification, markdown);
  setExportEnabled(true);
  switchTab("result");

  const company = meta?.company_name || "目标公司";
  const scorePct = verification?.score != null ? Math.round(verification.score * 100) : null;
  appendChat(
    "assistant",
    `<p><strong>${escHtml(company)}</strong> 年报分析已完成。</p>
     ${scorePct != null ? `<p>数字校验 ${scorePct}%，报告与指标已更新至右侧交付物。</p>` : "<p>报告已生成，请查看右侧交付物。</p>"}
     <p>可在执行轨迹区查看复盘，或继续提问。</p>`
  );
}

async function openReport(reportId) {
  appendChatText("system", `加载历史报告 ${reportId}…`);
  const res = await fetch(`/api/${SKILL_ID}/reports/${reportId}`);
  const data = await res.json();
  if (!res.ok) throw new Error(data.detail);
  renderResult(data.result, { ...data.meta, report_id: reportId }, data.metrics, data.verification);
  upsertTraceStep("load", { title: "加载历史报告", detail: reportId, status: "done" });
}

function buildFormData() {
  const form = new FormData();
  form.append("file", state.pdfFile);
  state.extraPdfFiles.forEach((f) => form.append("extra_files", f));
  if (state.templateFile) form.append("template_file", state.templateFile);
  form.append("company_name", $("#companyName").value.trim());
  form.append("report_year", $("#reportYear").value.trim());
  form.append("compare_years", $("#compareYears").value.trim());
  form.append("competitors", $("#competitors").value.trim());
  form.append("industry", $("#industry").value.trim());
  form.append("extra_instructions", $("#extraInstructions").value.trim());
  form.append("model", $("#modelSelect").value);
  form.append("max_tokens", "8192");
  form.append("section_mode", $("#sectionMode").checked ? "true" : "false");
  form.append("force_ocr", $("#forceOcr").checked ? "true" : "false");
  return form;
}

function stopPolling() {
  if (state.pollTimer) clearInterval(state.pollTimer);
  state.pollTimer = null;
}

function pollJob(jobId) {
  stopPolling();
  state.pollTimer = setInterval(async () => {
    const res = await fetch(`/api/${SKILL_ID}/jobs/${jobId}`);
    const data = await res.json();
    if (!res.ok) { stopPolling(); showProgress(false); return; }
    showProgress(true, data.progress || 0, data.message || "");
    updateTraceFromJob(data);
    if (data.status === "completed") {
      stopPolling();
      showProgress(false);
      const meta = data.meta || {};
      renderResult(data.result || "", meta, meta.metrics, meta.verification);
      loadHistory();
    } else if (data.status === "failed") {
      stopPolling();
      showProgress(false);
      upsertTraceStep("error", { title: "任务失败", detail: data.error || data.message, status: "error" });
      appendChatText("assistant", `分析失败：${data.error || data.message}`);
      alert(data.error || data.message);
    }
  }, 2000);
}

async function runAnalysis(userMessage) {
  if (!state.pdfFile) {
    appendChatText("assistant", "请先在「分析参数」中上传主年报 PDF，然后再开始分析。");
    return alert("请上传主 PDF");
  }
  const label = state.pdfFile.name;
  const company = $("#companyName").value.trim();
  appendChatText("user", userMessage || `开始分析：${label}${company ? `（${company}）` : ""}`);
  appendChatText("assistant", "收到，正在规划并执行分析任务，请查看中间执行轨迹。");
  initTracePlan();
  showProgress(true, 2, "提交任务…");
  try {
    const res = await fetch(`/api/${SKILL_ID}/run`, { method: "POST", body: buildFormData() });
    const data = await res.json();
    if (!res.ok) throw new Error(data.detail || JSON.stringify(data));
    upsertTraceStep("submit", { title: "任务已提交", detail: `job_id: ${data.job_id}`, status: "done" });
    pollJob(data.job_id);
  } catch (e) {
    showProgress(false);
    upsertTraceStep("error", { title: "提交失败", detail: e.message, status: "error" });
    appendChatText("assistant", `提交失败：${e.message}`);
    alert(e.message);
  }
}

async function rerunSection() {
  const sid = $("#sectionSelect").value;
  if (!state.currentReportId || !sid) return alert("请先完成分析并选择章节");
  const sec = state.sections.find((s) => s.section_id === sid);
  appendChatText("user", `重跑章节：${sec?.title || sid}`);
  initTracePlan();
  upsertTraceStep("rerun", { title: "章节重跑", detail: sec?.title || sid, status: "running" });
  showProgress(true, 5, "提交章节重跑…");
  try {
    const res = await fetch(`/api/${SKILL_ID}/reports/${state.currentReportId}/sections/${sid}/rerun`, {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({ model: $("#modelSelect").value }),
    });
    const data = await res.json();
    if (!res.ok) throw new Error(data.detail);
    pollJob(data.job_id);
  } catch (e) {
    showProgress(false);
    alert(e.message);
  }
}

function exportReport(fmt) {
  if (!state.currentReportId) return;
  window.open(`/api/${SKILL_ID}/reports/${state.currentReportId}/export?format=${fmt}`, "_blank");
}

async function openCompetitorLink() {
  const params = new URLSearchParams({
    report_id: state.currentReportId || "",
    company: $("#companyName").value.trim() || state.currentMeta.company_name || "",
    peers: $("#competitors").value.trim(),
    industry: $("#industry").value.trim(),
  });
  const res = await fetch(`/api/${SKILL_ID}/links?${params}`);
  const data = await res.json();
  window.open(data.competitor_benchmark, "_blank");
}

async function askAgent(messageOverride) {
  const msg = (messageOverride || $("#agentInput").value).trim();
  if (!msg) return;
  if (!messageOverride) $("#agentInput").value = "";

  const runKeywords = /^(开始分析|分析|运行|执行)/;
  if (runKeywords.test(msg) && state.pdfFile) {
    return runAnalysis(msg);
  }

  appendChatText("user", msg);
  appendChatText("assistant", "思考中…");
  const msgs = $("#chatMessages");
  const thinking = msgs.lastElementChild;

  try {
    const res = await fetch(`/api/${SKILL_ID}/agent/query`, {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({
        message: msg,
        report_id: state.currentReportId,
        company_name: $("#companyName").value.trim(),
        model: $("#modelSelect").value,
      }),
    });
    const data = await res.json();
    if (!res.ok) throw new Error(data.detail);
    thinking.remove();
    let html = `<p>${escHtml(data.content).replace(/\n/g, "<br>")}</p>`;
    if (data.actions?.length) {
      html += "<p><strong>建议操作：</strong></p><ul>";
      data.actions.forEach((a) => {
        if (a.type === "link" && a.url) {
          html += `<li><a href="${escHtml(a.url)}" target="_blank">${escHtml(a.label || "打开链接")}</a></li>`;
        } else if (a.type === "list_reports") {
          html += `<li>共 ${(a.reports || []).length} 份历史报告（见右侧列表）</li>`;
        } else {
          html += `<li>${escHtml(JSON.stringify(a))}</li>`;
        }
      });
      html += "</ul>";
    }
    appendChat("assistant", html);
    if (data.intent === "list_reports") loadHistory();
  } catch (e) {
    thinking.remove();
    appendChatText("assistant", `失败：${e.message}`);
  }
}

function handleQuickChip(action) {
  if (action === "run") return runAnalysis("开始分析");
  if (action === "history") return askAgent("有哪些已分析的年报？");
  if (action === "help") return askAgent("年报分析智能体怎么用？有哪些能力？");
  if (action === "focus-cashflow") {
    const el = $("#extraInstructions");
    el.value = (el.value ? el.value + "\n" : "") + "请重点分析经营活动现金流、盈利质量与现金回收能力。";
    appendChatText("system", "已追加补充要求：重点看现金流");
    return;
  }
}

document.addEventListener("DOMContentLoaded", () => {
  checkStatus();
  loadModels();
  loadTemplate();
  loadSections();
  loadHistory();
  setupDropzone("#pdfDropzone", "#pdfInput", setPdfFile);
  setupDropzone("#extraPdfDropzone", "#extraPdfInput", setExtraPdfs, true);
  setupDropzone("#tplDropzone", "#tplInput", setTemplateFile);
  $$(".artifact-tabs .tab").forEach((t) => t.addEventListener("click", () => switchTab(t.dataset.tab)));
  $$(".chip-btn").forEach((b) => b.addEventListener("click", () => handleQuickChip(b.dataset.action)));
  $("#btnRun").onclick = () => runAnalysis();
  $("#btnRerunSection").onclick = rerunSection;
  $("#btnReloadTemplate").onclick = loadTemplate;
  $("#btnCopy").onclick = () => navigator.clipboard.writeText(state.resultMarkdown);
  $("#btnExportMd").onclick = () => exportReport("md");
  $("#btnExportDocx").onclick = () => exportReport("docx");
  $("#btnExportPdf").onclick = () => exportReport("pdf");
  $("#btnExportXlsx").onclick = () => exportReport("xlsx");
  $("#btnCompetitorLink").onclick = openCompetitorLink;
  $("#btnAgent").onclick = () => askAgent();
  $("#agentInput").addEventListener("keydown", (e) => {
    if (e.key === "Enter" && !e.shiftKey) {
      e.preventDefault();
      askAgent();
    }
  });
  setExportEnabled(false);
});
