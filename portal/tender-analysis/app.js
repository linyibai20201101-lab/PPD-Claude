const SKILL_ID = "tender-analysis";

function showToast(msg) {
  const t = document.getElementById("toast");
  t.textContent = msg;
  t.classList.add("show");
  setTimeout(() => t.classList.remove("show"), 3500);
}

function getUrlParams() {
  const p = new URLSearchParams(window.location.search);
  return {
    jobId: p.get("job_id") || p.get("jobId") || "",
    keywords: p.get("keywords") || "",
    auto: p.get("auto") === "1",
  };
}

function setProgress(pct, msg) {
  document.getElementById("progressFill").style.width = `${pct}%`;
  document.getElementById("progressMsg").textContent = msg;
}

function esc(s) {
  const d = document.createElement("div");
  d.textContent = s == null ? "" : String(s);
  return d.innerHTML;
}

function renderExecutiveSummary(es) {
  const panel = document.getElementById("executiveSummary");
  if (!panel) return;
  if (!es || (!es.paragraph && !(es.insights || []).length)) {
    panel.classList.add("hidden");
    panel.innerHTML = "";
    return;
  }
  panel.classList.remove("hidden");
  const chips = (es.insights || [])
    .map((t) => `<span class="es-chip">${esc(t)}</span>`)
    .join("");
  const src = es.source ? ` · ${esc(es.source)}` : "";
  panel.innerHTML = `
    <h3>执行摘要${src}</h3>
    <p class="es-para">${esc(es.paragraph || "")}</p>
    <div class="es-chips">${chips}</div>
  `;
}

function renderOverview(overview, stats) {
  const el = document.getElementById("overviewCards");
  if (!overview) {
    el.innerHTML = "";
    return;
  }
  el.innerHTML = `
    <div class="ov-card"><span class="ov-val">${overview.count_1y ?? "—"}</span><span class="ov-label">近1年项目</span></div>
    <div class="ov-card"><span class="ov-val">${overview.count_3y ?? "—"}</span><span class="ov-label">近3年项目</span></div>
    <div class="ov-card"><span class="ov-val">${overview.total ?? "—"}</span><span class="ov-label">样本总数</span></div>
    <div class="ov-card"><span class="ov-val">${stats?.dedup_count ?? "—"}</span><span class="ov-label">去重后</span></div>
  `;
}

async function runAnalysis(jobId, keywords) {
  if (!jobId) {
    showToast("请提供任务 ID");
    return;
  }

  document.getElementById("progressPanel").hidden = false;
  document.getElementById("reportPanel").hidden = true;
  setProgress(20, "正在加载数据并清洗去重…");

  try {
    const body = { job_id: jobId };
    if (keywords) body.keywords = keywords;

    setProgress(45, "正在计算分析维度…");
    const res = await fetch(`/api/${SKILL_ID}/run`, {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify(body),
    });
    const data = await res.json();

    if (!res.ok) {
      showToast(data.detail || "分析失败");
      document.getElementById("progressPanel").hidden = true;
      return;
    }

    setProgress(100, data.message);
    showToast(data.message);

    document.getElementById("reportPanel").hidden = false;
    document.getElementById("progressPanel").hidden = true;

    document.getElementById("btnOpenReport").href = data.report_url;
    document.getElementById("btnDownloadReport").dataset.url = data.download_url;
    document.getElementById("btnDownloadReport").dataset.filename =
      `标讯分析_${data.keywords || "report"}_${data.report_id}.html`;
    document.getElementById("reportFrame").src = data.report_url;

    renderOverview(data.overview, data.stats);
    renderExecutiveSummary(data.executive_summary);
    document.getElementById("reportPanel").scrollIntoView({ behavior: "smooth" });
  } catch (err) {
    showToast("请求失败: " + err.message);
    document.getElementById("progressPanel").hidden = true;
  }
}

function initFromUrl() {
  const { jobId, keywords, auto } = getUrlParams();
  if (jobId) {
    document.getElementById("sourceFromJob").hidden = false;
    document.getElementById("linkedJobId").textContent = jobId;
    document.getElementById("linkedKeywords").textContent = keywords || "（未指定）";
    document.getElementById("manualJobId").value = jobId;
    if (keywords) document.getElementById("manualKeywords").value = keywords;
    if (auto) runAnalysis(jobId, keywords);
  }
}

document.getElementById("btnAnalyze")?.addEventListener("click", () => {
  const { jobId, keywords } = getUrlParams();
  runAnalysis(jobId || document.getElementById("manualJobId").value.trim(), keywords);
});

document.getElementById("btnAnalyzeManual")?.addEventListener("click", () => {
  runAnalysis(
    document.getElementById("manualJobId").value.trim(),
    document.getElementById("manualKeywords").value.trim() || null
  );
});

document.getElementById("btnDownloadReport")?.addEventListener("click", async () => {
  const btn = document.getElementById("btnDownloadReport");
  const url = btn?.dataset.url;
  if (!url) {
    showToast("请先生成报告");
    return;
  }
  try {
    const res = await fetch(url);
    if (!res.ok) {
      const err = await res.json().catch(() => ({}));
      showToast(err.detail || "下载失败");
      return;
    }
    const blob = await res.blob();
    const cd = res.headers.get("Content-Disposition") || "";
    let filename = btn.dataset.filename || "tender_report.html";
    const utf8Match = cd.match(/filename\*=UTF-8''([^;]+)/i);
    const asciiMatch = cd.match(/filename="([^"]+)"/i);
    if (utf8Match) filename = decodeURIComponent(utf8Match[1]);
    else if (asciiMatch) filename = asciiMatch[1];

    const a = document.createElement("a");
    a.href = URL.createObjectURL(blob);
    a.download = filename;
    a.click();
    URL.revokeObjectURL(a.href);
  } catch (err) {
    showToast("下载失败: " + err.message);
  }
});

async function runUploadAnalysis() {
  const fileInput = document.getElementById("csvFile");
  const file = fileInput?.files?.[0];
  if (!file) {
    showToast("请选择 CSV 或 Excel 文件");
    return;
  }
  document.getElementById("progressPanel").hidden = false;
  document.getElementById("reportPanel").hidden = true;
  setProgress(15, "上传文件中…");
  const fd = new FormData();
  fd.append("file", file);
  fd.append("keywords", document.getElementById("uploadKeywords")?.value?.trim() || "");
  fd.append("enable_llm_summary", document.getElementById("enableLlmSummary")?.checked ? "true" : "false");
  try {
    setProgress(40, "清洗数据并生成报告…");
    const res = await fetch(`/api/${SKILL_ID}/run/upload`, { method: "POST", body: fd });
    const data = await res.json();
    if (!res.ok) {
      showToast(data.detail || "分析失败");
      document.getElementById("progressPanel").hidden = true;
      return;
    }
    setProgress(100, data.message);
    showToast(data.message);
    document.getElementById("reportPanel").hidden = false;
    document.getElementById("progressPanel").hidden = true;
    document.getElementById("btnOpenReport").href = data.report_url;
    document.getElementById("btnDownloadReport").dataset.url = data.download_url;
    document.getElementById("reportFrame").src = data.report_url;
    renderOverview(data.overview, data.stats);
    renderExecutiveSummary(data.executive_summary);
    document.getElementById("reportPanel").scrollIntoView({ behavior: "smooth" });
  } catch (err) {
    showToast("上传失败: " + err.message);
    document.getElementById("progressPanel").hidden = true;
  }
}

document.getElementById("btnAnalyzeUpload")?.addEventListener("click", () => runUploadAnalysis());

initFromUrl();

(async function checkStatus() {
  try {
    await fetch(`/api/${SKILL_ID}/status`);
  } catch {
    showToast("无法连接后端，请先启动 portal");
  }
})();
