const SKILL_ID = "tender-product-analysis";
const $ = (s) => document.querySelector(s);

const state = {
  pollTimer: null,
  currentJobId: null,
  reportId: null,
  products: [],
  activeTab: "products",
  unmatched: [],
  meta: {},
};

const TABLE_COLS = [
  "项目名称",
  "产品名称",
  "品牌",
  "型号",
  "数量",
  "单价",
  "行金额",
  "地区",
  "中标单位",
];

function showToast(msg) {
  let t = document.getElementById("toast");
  if (!t) {
    t = document.createElement("div");
    t.id = "toast";
    t.className = "toast";
    document.body.appendChild(t);
  }
  t.textContent = msg;
  t.classList.add("show");
  setTimeout(() => t.classList.remove("show"), 4000);
}

function esc(s) {
  const d = document.createElement("div");
  d.textContent = s == null ? "" : String(s);
  return d.innerHTML;
}

function getUrlParams() {
  const p = new URLSearchParams(window.location.search);
  return {
    jobId: p.get("source_job_id") || p.get("job_id") || p.get("jobId") || "",
    keywords: safeDecodeParam(p.get("keywords") || ""),
    parseAttachments: p.get("parse_attachments") !== "0",
  };
}

function safeDecodeParam(value) {
  if (!value) return "";
  try {
    return decodeURIComponent(value.replace(/\+/g, " "));
  } catch {
    return value;
  }
}

async function checkStatus() {
  const badge = $("#statusBadge");
  const out = $("#statusOut");
  try {
    const res = await fetch(`/api/${SKILL_ID}/status`);
    const data = await res.json();
    badge.textContent = data.status === "ready" ? "统计+详情 已就绪" : "规划中";
    badge.className = `badge ${data.status === "ready" ? "ready" : "scaffold"}`;
    let msg = data.message || "";
    if (!data.jianyu_configured) msg += " · 未配置剑鱼账号（详情抓取需 .env）";
    out.textContent = msg;
  } catch {
    badge.textContent = "API 未就绪";
    out.textContent = "请启动 portal: python server.py";
  }
}

function stopPoll() {
  if (state.pollTimer) clearInterval(state.pollTimer);
  state.pollTimer = null;
}

function showProgress(show, pct, msg) {
  $("#progressBlock").classList.toggle("hidden", !show);
  $("#progressFill").style.width = `${Math.min(100, pct)}%`;
  $("#progressMsg").textContent = msg || "";
  $("#btnRun").disabled = show;
  const abortBtn = $("#btnAbort");
  if (abortBtn) {
    abortBtn.hidden = !show || !state.currentJobId;
    if (show && abortBtn.textContent !== "中止中…") {
      abortBtn.disabled = false;
    }
  }
}

async function abortCurrentJob() {
  if (!state.currentJobId) {
    showToast("当前没有进行中的任务");
    return;
  }
  const btn = $("#btnAbort");
  if (btn) {
    btn.disabled = true;
    btn.textContent = "中止中…";
  }
  try {
    const res = await fetch(`/api/${SKILL_ID}/jobs/${state.currentJobId}/cancel`, {
      method: "POST",
    });
    const data = await res.json();
    if (!res.ok) {
      showToast(data.detail || "中止失败");
      if (btn) {
        btn.disabled = false;
        btn.textContent = "中止分析";
      }
      return;
    }
    showToast("已发送中止请求，正在停止详情/附件抓取…");
    $("#progressMsg").textContent = data.message || "正在中止…";
  } catch (e) {
    showToast("中止失败: " + (e.message || String(e)));
    if (btn) {
      btn.disabled = false;
      btn.textContent = "中止分析";
    }
  }
}

function startJobPolling(jobId) {
  state.currentJobId = jobId;
  stopPoll();
  const abortBtn = $("#btnAbort");
  if (abortBtn) {
    abortBtn.hidden = false;
    abortBtn.disabled = false;
    abortBtn.textContent = "中止分析";
  }
  state.pollTimer = setInterval(async () => {
    const jr = await fetch(`/api/${SKILL_ID}/jobs/${jobId}`);
    const jd = await jr.json();
    if (!jr.ok) {
      stopPoll();
      finishJobRun(false, jd.detail || "任务查询失败");
      return;
    }
    showProgress(true, jd.progress || 0, jd.message || "");
    if (jd.status === "completed") {
      finishJobRun(true, "分析完成，结果已展示在右侧", jd);
    } else if (jd.status === "cancelled") {
      finishJobRun(true, "已中止，已保存部分结果", jd);
    } else if (jd.status === "failed") {
      finishJobRun(false, jd.error || jd.message || "分析失败");
    }
  }, 2000);
}

function finishJobRun(ok, message, jobPayload) {
  stopPoll();
  state.currentJobId = null;
  showProgress(false);
  const abortBtn = $("#btnAbort");
  if (abortBtn) abortBtn.hidden = true;
  if (ok && jobPayload) {
    showToast(message);
    if (jobPayload.report_id) openReport(jobPayload.report_id);
    else if (jobPayload.stats) {
      renderReport({
        report_id: "",
        stats: jobPayload.stats,
        products: [],
        report_md: "",
      });
    }
    loadHistory();
  } else if (!ok) {
    alert(message);
  }
}

function showLinkedJob(jobId, keywords) {
  const bar = $("#linkedJobBar");
  if (!bar) return;
  bar.classList.remove("hidden");
  $("#linkedJobId").textContent = jobId;
  $("#linkedKeywords").textContent = keywords || "（未指定，将使用任务文件名中的关键词）";
}

function renderSummaryCards(stats, meta) {
  const el = $("#summaryCards");
  const s = stats || {};
  const cards = [
    { label: "项目数", value: s.project_count ?? "—" },
    { label: "产品行", value: s.product_line_count ?? meta?.product_line_count ?? "—" },
    {
      label: "金额合计(万)",
      value: s.total_amount_万元 != null ? s.total_amount_万元 : "—",
    },
    { label: "详情成功", value: s.detail_fetched_ok ?? "—" },
    {
      label: "关键词匹配行",
      value: s.keyword_matched_lines != null ? s.keyword_matched_lines : "—",
    },
    { label: "有附件项目", value: s.with_attachment_count ?? "—" },
    { label: "待抽检", value: s.unmatched_count ?? "—" },
    {
      label: "附件解析率%",
      value:
        s.attachment_parse_rate_pct != null ? s.attachment_parse_rate_pct : "—",
    },
  ];
  el.innerHTML = cards
    .map(
      (c) =>
        `<div class="summary-card"><span class="summary-val">${esc(c.value)}</span><span class="summary-label">${esc(c.label)}</span></div>`
    )
    .join("");
}

function rowSearchText(row) {
  return TABLE_COLS.map((k) => row[k] ?? "")
    .join(" ")
    .toLowerCase();
}

function renderProductsTable(products, filterText = "") {
  const tbody = $("#productsTable tbody");
  const q = (filterText || "").trim().toLowerCase();
  const filtered = q
    ? products.filter((r) => rowSearchText(r).includes(q))
    : products;

  $("#tableCount").textContent = `显示 ${filtered.length} / ${products.length} 行`;

  if (!filtered.length) {
    tbody.innerHTML = `<tr><td colspan="10" class="empty-cell">暂无产品行${q ? "（请调整筛选）" : ""}</td></tr>`;
    return;
  }

  tbody.innerHTML = "";
  filtered.forEach((row, i) => {
    const tr = document.createElement("tr");
    const pname = row["项目名称"] || "";
    const shortName = pname.length > 36 ? pname.slice(0, 36) + "…" : pname;
    tr.innerHTML = `
      <td>${i + 1}</td>
      <td class="col-project" title="${esc(pname)}">${esc(shortName)}</td>
      <td class="col-product">${esc(row["产品名称"])}</td>
      <td>${esc(row["品牌"] || "—")}</td>
      <td>${esc(row["型号"] || "—")}</td>
      <td>${esc(row["数量"] ?? "—")}</td>
      <td>${esc(row["单价"] ?? "—")}</td>
      <td>${esc(row["行金额"] ?? "—")}</td>
      <td>${esc(row["地区"] || "—")}</td>
      <td class="col-vendor">${esc(row["中标单位"] || "—")}</td>
    `;
    tbody.appendChild(tr);
  });
}

function switchTab(tabId) {
  state.activeTab = tabId;
  document.querySelectorAll(".result-tabs .tab").forEach((btn) => {
    btn.classList.toggle("active", btn.dataset.tab === tabId);
  });
  const panelMap = {
    products: "tabProducts",
    report: "tabReport",
    stats: "tabStats",
    unmatched: "tabUnmatched",
  };
  document.querySelectorAll(".tab-panel").forEach((panel) => {
    panel.classList.toggle("active", panel.id === panelMap[tabId]);
  });
}

function renderUnmatchedTable(rows) {
  const tbody = $("#unmatchedTable tbody");
  const list = rows || [];
  $("#unmatchedHint").textContent = list.length
    ? `共 ${list.length} 项待抽检（详情失败 / 未命中 / 附件未解析）`
    : "暂无异常项";
  if (!list.length) {
    tbody.innerHTML = `<tr><td colspan="6" class="empty-cell">全部项目已命中或无需抽检</td></tr>`;
    return;
  }
  tbody.innerHTML = "";
  list.forEach((row, i) => {
    const tr = document.createElement("tr");
    const title = row["项目名称"] || "";
    const short = title.length > 40 ? title.slice(0, 40) + "…" : title;
    tr.innerHTML = `
      <td>${i + 1}</td>
      <td class="col-project" title="${esc(title)}">${esc(short)}</td>
      <td>${esc(row["原因"] || "—")}</td>
      <td>${esc(row["详情抓取"] || "—")}</td>
      <td>${esc(row["产品数量"] ?? "—")}</td>
      <td>${row["有附件"] ? "是" : "否"}</td>
    `;
    tbody.appendChild(tr);
  });
}

function renderReport(data) {
  const stats = data.stats || {};
  const meta = data.meta || {};
  const products = data.products || [];

  state.products = products;
  state.reportId = data.report_id;
  state.meta = meta;
  state.unmatched = data.unmatched_projects || stats.unmatched_projects || [];

  $("#resultsEmpty").classList.add("hidden");
  $("#resultsBody").classList.remove("hidden");

  const kw = stats.keyword || meta.keyword || "";
  const job = stats.source_job_id || meta.source_job_id || "";
  $("#resultMeta").textContent = `报告 ${data.report_id} · 关键词「${kw}」· 来源任务 ${job}`;

  renderSummaryCards(stats, meta);

  const md = data.report_md || "";
  $("#reportPreview").innerHTML = typeof marked !== "undefined" ? marked.parse(md) : esc(md);
  $("#statsPreview").textContent = JSON.stringify(stats, null, 2);

  renderProductsTable(products, $("#tableFilter")?.value || "");
  renderUnmatchedTable(state.unmatched);
  switchTab(state.activeTab);

  $("#btnExportXlsx").disabled = false;
  $("#btnExportMd").disabled = false;
  const canRetry = Boolean(state.reportId);
  $("#btnRetryFailed").disabled = !canRetry;
  $("#btnRetryUnmatched").disabled = !canRetry;
  $("#btnRetryAttachments").disabled = !canRetry;

  $("#resultsPanel").scrollIntoView({ behavior: "smooth", block: "start" });
}

async function openReport(reportId) {
  const res = await fetch(`/api/${SKILL_ID}/reports/${reportId}`);
  const data = await res.json();
  if (!res.ok) return alert(data.detail || "加载报告失败");
  renderReport(data);
}

async function loadHistory() {
  const ul = $("#historyList");
  try {
    const res = await fetch(`/api/${SKILL_ID}/reports?limit=12`);
    const data = await res.json();
    const reports = data.reports || [];
    if (!reports.length) {
      ul.innerHTML = "<li class='empty'>暂无</li>";
      return;
    }
    ul.innerHTML = "";
    reports.forEach((r) => {
      const li = document.createElement("li");
      const label = [r.keyword, r.source_job_id].filter(Boolean).join(" · ") || r.report_id;
      const cnt = r.project_count != null ? ` · ${r.project_count}项` : "";
      li.innerHTML = `<button type="button" class="history-btn">${esc(label)}</button><span>${(r.saved_at || "").slice(0, 16)}${cnt}</span>`;
      li.querySelector("button").onclick = () => openReport(r.report_id);
      ul.appendChild(li);
    });
  } catch {
    ul.innerHTML = "<li class='empty'>加载失败</li>";
  }
}

async function runRetry(retryMode) {
  if (!state.reportId) return showToast("请先完成一次分析或打开历史报告");
  const keywords = $("#keywords").value.trim() || state.meta.keyword || "";
  showProgress(true, 2, `重跑（${retryMode}）…`);
  try {
    const res = await fetch(`/api/${SKILL_ID}/run`, {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({
        source_job_id: state.meta.source_job_id || $("#sourceJobId").value.trim(),
        keywords,
        from_report_id: state.reportId,
        retry_mode: retryMode,
        fetch_detail: true,
        parse_attachments: $("#parseAttachments").checked,
        max_projects: parseInt($("#maxProjects").value, 10) || 50,
        headless: $("#headless").checked,
      }),
    });
    const data = await res.json();
    if (!res.ok) throw new Error(data.detail || JSON.stringify(data));
    startJobPolling(data.job_id);
  } catch (e) {
    finishJobRun(false, e.message || String(e));
  }
}

async function runAnalysis() {
  const source_job_id = $("#sourceJobId").value.trim();
  const keywords = $("#keywords").value.trim();
  if (!source_job_id) {
    showToast("请填写 tender-info 任务 ID");
    return alert("请填写 tender-info 任务 ID");
  }
  if (!keywords) {
    showToast("请填写检索关键词");
    return alert("请填写检索关键词（用于匹配产品清单）");
  }

  $("#resultsEmpty").classList.remove("hidden");
  $("#resultsBody").classList.add("hidden");

  showProgress(true, 2, "提交任务…");
  try {
    const res = await fetch(`/api/${SKILL_ID}/run`, {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({
        source_job_id,
        keywords,
        only_with_attachment: $("#onlyAttachment").checked,
        fetch_detail: $("#fetchDetail").checked,
        parse_attachments: $("#parseAttachments").checked,
        max_projects: parseInt($("#maxProjects").value, 10) || 50,
        headless: $("#headless").checked,
      }),
    });
    const data = await res.json();
    if (!res.ok) {
      const err = data.detail || JSON.stringify(data);
      throw new Error(typeof err === "string" ? err : JSON.stringify(err));
    }

    startJobPolling(data.job_id);
  } catch (e) {
    finishJobRun(false, e.message || String(e));
  }
}

function initFromUrl() {
  const p = getUrlParams();
  const { jobId, keywords, parseAttachments } = p;
  if (jobId) {
    $("#sourceJobId").value = jobId;
    showLinkedJob(jobId, keywords);
  }
  if (keywords) $("#keywords").value = keywords;
  if ($("#parseAttachments")) $("#parseAttachments").checked = parseAttachments;

  if (jobId && keywords) {
    showToast("已带入任务与关键词，请确认后点击「开始分析」");
  } else if (jobId) {
    showToast("已带入任务 ID，请填写关键词后点击「开始分析」");
  }
}

function setupTabs() {
  document.querySelectorAll(".result-tabs .tab").forEach((btn) => {
    btn.addEventListener("click", () => switchTab(btn.dataset.tab));
  });
  $("#tableFilter")?.addEventListener("input", (e) => {
    renderProductsTable(state.products, e.target.value);
  });
}

document.addEventListener("DOMContentLoaded", () => {
  initFromUrl();
  checkStatus();
  loadHistory();
  setupTabs();
  $("#btnRun").onclick = () => runAnalysis();
  $("#btnAbort")?.addEventListener("click", abortCurrentJob);
  $("#btnExportXlsx").onclick = () => {
    if (state.reportId) window.open(`/api/${SKILL_ID}/reports/${state.reportId}/export?format=xlsx`, "_blank");
  };
  $("#btnExportMd").onclick = () => {
    if (state.reportId) window.open(`/api/${SKILL_ID}/reports/${state.reportId}/export?format=md`, "_blank");
  };
  $("#btnRetryFailed")?.addEventListener("click", () => runRetry("failed"));
  $("#btnRetryUnmatched")?.addEventListener("click", () => runRetry("no_match"));
  $("#btnRetryAttachments")?.addEventListener("click", () => runRetry("attachments"));
});
