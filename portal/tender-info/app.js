const SKILL_ID = "tender-info";
let eventSource = null;
let currentJobId = null;
const PHASE_ORDER = ["login", "search", "crawl", "filter", "done"];

let queryOptions = null;
let publishTimePreset = "1y";
let infoTypeMode = "all";

function showToast(msg) {
  const t = document.getElementById("toast");
  t.textContent = msg;
  t.classList.add("show");
  setTimeout(() => t.classList.remove("show"), 3500);
}

function setStep(n) {
  document.querySelectorAll(".step").forEach((el) => {
    const step = Number(el.dataset.step);
    el.classList.toggle("active", step === n);
    el.classList.toggle("done", step < n);
  });
}

function toggleCredentialFields() {
  const useSaved = document.getElementById("useSaved").checked;
  document.getElementById("credentialFields").classList.toggle("disabled", useSaved);
}

function renderTimePresets(presets, defaultId) {
  const row = document.getElementById("timePresetRow");
  row.innerHTML = "";
  publishTimePreset = defaultId || "1y";
  presets.forEach((p) => {
    const btn = document.createElement("button");
    btn.type = "button";
    btn.className = "chip" + (p.id === publishTimePreset ? " active" : "");
    btn.dataset.preset = p.id;
    btn.textContent = p.label;
    btn.addEventListener("click", () => {
      publishTimePreset = p.id;
      row.querySelectorAll(".chip").forEach((c) => c.classList.toggle("active", c.dataset.preset === p.id));
      document.getElementById("customDateRow").hidden = p.id !== "custom";
    });
    row.appendChild(btn);
  });
  document.getElementById("customDateRow").hidden = publishTimePreset !== "custom";
}

function renderSearchScopes(scopes, defaults) {
  const grid = document.getElementById("scopeGrid");
  grid.innerHTML = "";
  const selected = new Set(defaults || []);
  scopes.forEach((s) => {
    const label = document.createElement("label");
    label.className = "scope-item";
    const cb = document.createElement("input");
    cb.type = "checkbox";
    cb.value = s.id;
    cb.checked = selected.has(s.id);
    label.appendChild(cb);
    label.appendChild(document.createTextNode(s.label));
    grid.appendChild(label);
  });
}

function renderInfoTypes(groups) {
  const grid = document.getElementById("infoTypeGrid");
  grid.innerHTML = "";
  groups.forEach((grp) => {
    const title = document.createElement("div");
    title.className = "info-group-title";
    title.textContent = grp.label;
    grid.appendChild(title);
    grp.items.forEach((item) => {
      const label = document.createElement("label");
      label.className = "scope-item";
      const cb = document.createElement("input");
      cb.type = "checkbox";
      cb.value = item;
      cb.dataset.group = grp.id;
      label.appendChild(cb);
      label.appendChild(document.createTextNode(item));
      grid.appendChild(label);
    });
  });
}

function renderRegions(regions, defaultRegion) {
  const sel = document.getElementById("region");
  sel.innerHTML = "";
  regions.forEach((r) => {
    const opt = document.createElement("option");
    opt.value = r.id;
    opt.textContent = r.label;
    if (r.id === (defaultRegion || "全国")) opt.selected = true;
    sel.appendChild(opt);
  });
}

function setupInfoTypeMode() {
  document.querySelectorAll("#infoTypeModeRow .chip").forEach((btn) => {
    btn.addEventListener("click", () => {
      infoTypeMode = btn.dataset.infoMode;
      document.querySelectorAll("#infoTypeModeRow .chip").forEach((b) => {
        b.classList.toggle("active", b.dataset.infoMode === infoTypeMode);
      });
      document.getElementById("infoTypeGrid").hidden = infoTypeMode !== "custom";
    });
  });
}

function getSelectedScopes() {
  return [...document.querySelectorAll("#scopeGrid input:checked")].map((el) => el.value);
}

function getSelectedInfoTypes() {
  if (infoTypeMode === "all") return [];
  return [...document.querySelectorAll("#infoTypeGrid input:checked")].map((el) => el.value);
}

async function loadQueryOptions() {
  try {
    const res = await fetch(`/api/${SKILL_ID}/query-options`);
    queryOptions = await res.json();
    const d = queryOptions.defaults || {};
    renderTimePresets(queryOptions.publish_time_presets, d.publish_time_preset);
    renderSearchScopes(queryOptions.search_scopes, d.search_scopes);
    renderInfoTypes(queryOptions.info_type_groups);
    renderRegions(queryOptions.regions, d.region);
    setupInfoTypeMode();
  } catch {
    showToast("无法加载查询选项，将使用默认配置");
    renderTimePresets(
      [
        { id: "7d", label: "近7天" },
        { id: "30d", label: "近30天" },
        { id: "1y", label: "近1年" },
        { id: "3y", label: "近3年" },
        { id: "5y", label: "近5年" },
        { id: "custom", label: "自定义" },
      ],
      "1y"
    );
    renderSearchScopes(
      [
        { id: "title", label: "标题" },
        { id: "body", label: "正文" },
      ],
      ["title", "body"]
    );
    renderRegions([{ id: "全国", label: "全国" }], "全国");
    setupInfoTypeMode();
  }
}

async function loadStatus() {
  const hint = document.getElementById("envHint");
  try {
    const res = await fetch(`/api/${SKILL_ID}/status`);
    const data = await res.json();
    if (data.jianyu_configured) {
      hint.textContent = "✓ 检测到 .env 中已保存剑鱼标讯账号，可勾选上方直接使用";
      hint.style.color = "#059669";
      document.getElementById("useSaved").checked = true;
    } else {
      hint.textContent = "未检测到 .env 账号，请在本页填写手机号与密码（或在 portal/.env 配置 JIANYU_PHONE）";
      hint.style.color = "#b45309";
    }
    toggleCredentialFields();
  } catch {
    hint.textContent = "无法连接后端服务，请先启动 portal（start-portal.bat）";
    hint.style.color = "#dc2626";
  }
}

function buildRequestBody() {
  const useSaved = document.getElementById("useSaved").checked;
  const includePending = document.getElementById("includePending").checked;
  const scopes = getSelectedScopes();
  return {
    keywords: document.getElementById("keywords").value.trim(),
    region: document.getElementById("region").value || "全国",
    publish_time_preset: publishTimePreset,
    date_from: document.getElementById("dateFrom").value || null,
    date_to: document.getElementById("dateTo").value || null,
    search_scopes: scopes.length ? scopes : ["title", "body"],
    info_types: getSelectedInfoTypes(),
    max_pages: Number(document.getElementById("maxPages").value) || 5,
    skip_detail: document.getElementById("skipDetail").checked,
    headless: document.getElementById("headless").checked,
    include_pending: includePending,
    only_awarded: !includePending,
    use_saved_credentials: useSaved,
    jianyu_phone: useSaved ? null : document.getElementById("phone").value.trim() || null,
    jianyu_password: useSaved ? null : document.getElementById("password").value || null,
  };
}

function logLineClass(line) {
  if (line.includes("[错误]")) return "log-line log-error";
  if (line.includes("[截图]")) return "log-line log-shot";
  if (line.includes("[登录]")) return "log-line log-login";
  if (line.includes("[搜索]")) return "log-line log-search";
  if (line.includes("[抓取]") || line.includes("[翻页]") || line.includes("[详情]")) return "log-line log-crawl";
  if (line.includes("[筛选]") || line.includes("[解析]") || line.includes("[导出]")) return "log-line log-filter";
  if (line.includes("[完成]")) return "log-line log-done";
  return "log-line";
}

function renderLogs(logs) {
  const el = document.getElementById("logOut");
  el.innerHTML = (logs || [])
    .map((line) => `<div class="${logLineClass(line)}">${esc(line)}</div>`)
    .join("");
  el.scrollTop = el.scrollHeight;
}

function setPhase(phase) {
  const idx = PHASE_ORDER.indexOf(phase);
  document.querySelectorAll("#phaseTrack .phase-step").forEach((el) => {
    const p = el.dataset.phase;
    const pi = PHASE_ORDER.indexOf(p);
    el.classList.toggle("active", p === phase);
    el.classList.toggle("done", pi >= 0 && idx >= 0 && pi < idx);
  });
}

function refreshPreview(jobId) {
  const img = document.getElementById("previewImg");
  const hint = document.getElementById("previewHint");
  img.src = `/api/${SKILL_ID}/jobs/${jobId}/preview?t=${Date.now()}`;
  img.onload = () => {
    img.hidden = false;
    hint.hidden = true;
  };
  img.onerror = () => {
    img.hidden = true;
    hint.hidden = false;
  };
}

function stopStream() {
  if (eventSource) {
    eventSource.close();
    eventSource = null;
  }
}

function setAbortVisible(visible) {
  const btn = document.getElementById("btnAbort");
  if (btn) btn.hidden = !visible;
}

async function abortCurrentJob() {
  if (!currentJobId) return;
  const btn = document.getElementById("btnAbort");
  if (btn) {
    btn.disabled = true;
    btn.textContent = "中止中…";
  }
  try {
    const res = await fetch(`/api/${SKILL_ID}/jobs/${currentJobId}/cancel`, { method: "POST" });
    const data = await res.json();
    if (!res.ok) {
      showToast(data.detail || "中止失败");
      if (btn) {
        btn.disabled = false;
        btn.textContent = "中止任务";
      }
      return;
    }
    showToast("已发送中止请求，正在停止爬虫…");
    document.getElementById("taskMessage").textContent = "正在中止，已抓取的数据将尽量保留…";
  } catch (err) {
    showToast("中止请求失败: " + err.message);
    if (btn) {
      btn.disabled = false;
      btn.textContent = "中止任务";
    }
  }
}

function finishTask(success, message, result, cancelled = false) {
  stopStream();
  setAbortVisible(false);
  const btn = document.getElementById("btnSubmit");
  btn.disabled = false;
  btn.textContent = "开始执行任务";
  const abortBtn = document.getElementById("btnAbort");
  if (abortBtn) {
    abortBtn.disabled = false;
    abortBtn.textContent = "中止任务";
  }

  if ((success || cancelled) && result) {
    setPhase("done");
    setStep(3);
    renderResults(result);
    loadJobHistory();
    showToast(message || (cancelled ? `已中止，保留 ${result.total} 条` : `完成：${result.total} 条`));
  } else {
    showToast(message || (cancelled ? "任务已中止" : "任务失败"));
  }
}

function startJobStream(jobId) {
  stopStream();
  currentJobId = jobId;
  setAbortVisible(true);
  const logs = [];

  document.getElementById("previewImg").hidden = true;
  document.getElementById("previewHint").hidden = false;
  document.getElementById("previewHint").textContent = "正在启动浏览器，截图将在此显示…";
  setPhase("login");
  renderLogs(["[启动] 连接实时日志流…"]);

  eventSource = new EventSource(`/api/${SKILL_ID}/jobs/${jobId}/stream`);

  eventSource.onmessage = (ev) => {
    let data;
    try {
      data = JSON.parse(ev.data);
    } catch {
      return;
    }

    if (data.type === "log") {
      logs.push(data.line);
      renderLogs(logs);
      if (data.line.includes("[登录]")) setPhase("login");
      if (data.line.includes("[搜索]")) setPhase("search");
      if (data.line.includes("[抓取]") || data.line.includes("[翻页]")) setPhase("crawl");
      if (data.line.includes("[筛选]") || data.line.includes("[解析]")) setPhase("filter");
      if (data.line.includes("[截图]") && currentJobId) refreshPreview(currentJobId);
    }

    if (data.type === "status") {
      updateTaskUI({
        status: data.status,
        progress: data.progress,
        message: data.message,
        phase: data.phase,
        logs,
      });
      if (data.phase) setPhase(data.phase === "detail" ? "crawl" : data.phase);
      if (data.has_preview && currentJobId) refreshPreview(currentJobId);

      if (data.status === "failed") {
        finishTask(false, data.message);
      }
      if (data.status === "cancelled" && !data.result) {
        finishTask(false, data.message, null, true);
      }
    }

    if (data.type === "done" && data.result) {
      const cancelled = data.result.status === "cancelled";
      finishTask(
        !cancelled,
        cancelled ? data.result.message : `完成：${data.result.total} 条（已中标 ${data.result.total_awarded ?? "—"}）`,
        data.result,
        cancelled
      );
    }

    if (data.type === "cancelled") {
      finishTask(false, data.message, null, true);
    }

    if (data.type === "error") {
      finishTask(false, data.message);
    }
  };

  eventSource.onerror = () => {
    if (!eventSource) return;
    stopStream();
    fallbackPoll(jobId, logs);
  };
}

async function fallbackPoll(jobId, existingLogs = []) {
  const logs = [...existingLogs];
  for (let i = 0; i < 120; i++) {
    await new Promise((r) => setTimeout(r, 2000));
    try {
      const res = await fetch(`/api/${SKILL_ID}/jobs/${jobId}`);
      const job = await res.json();
      if (!res.ok) break;
      if (job.logs?.length > logs.length) {
        logs.length = 0;
        logs.push(...job.logs);
        renderLogs(logs);
      }
      updateTaskUI(job);
      if (job.phase) setPhase(job.phase === "detail" ? "crawl" : job.phase);
      refreshPreview(jobId);
      if (job.status === "completed" && job.result) {
        finishTask(true, null, job.result);
        return;
      }
      if (job.status === "cancelled") {
        finishTask(!!job.result, job.message, job.result, true);
        return;
      }
      if (job.status === "failed") {
        finishTask(false, job.message);
        return;
      }
    } catch {
      break;
    }
  }
  finishTask(false, "连接中断，请刷新页面重试");
}

function typeBadgeClass(projectType, winner) {
  const t = (projectType || "").trim();
  if (winner || t === "成交" || t === "中标") return "type-badge awarded";
  if (t === "预告") return "type-badge pending";
  if (t === "招标" || t === "询价" || t === "竞价") return "type-badge bidding";
  return "type-badge other";
}

function renderResults(result) {
  const panel = document.getElementById("resultPanel");
  const tbody = document.querySelector("#resultTable tbody");
  const summary = document.getElementById("resultSummary");
  const statsEl = document.getElementById("resultStats");
  const download = document.getElementById("downloadCsv");
  const reportBtn = document.getElementById("btnToggleReport");
  const reportPreview = document.getElementById("reportPreview");

  panel.hidden = false;
  summary.textContent = `关键词「${result.keywords}」· 输出 ${result.total} 条`;

  const nextSteps = document.getElementById("resultNextSteps");
  if (nextSteps) nextSteps.hidden = !(result.total > 0);

  const jobBar = document.getElementById("jobIdBar");
  const jobDisplay = document.getElementById("jobIdDisplay");
  const copyBtn = document.getElementById("btnCopyJobId");
  if (jobBar && jobDisplay && currentJobId) {
    jobBar.hidden = false;
    jobDisplay.textContent = currentJobId;
    if (copyBtn) {
      copyBtn.onclick = async () => {
        try {
          await navigator.clipboard.writeText(currentJobId);
          showToast("任务 ID 已复制");
        } catch {
          showToast("复制失败，请手动选中 ID 复制");
        }
      };
    }
  } else if (jobBar) {
    jobBar.hidden = true;
  }

  const raw = result.total_raw ?? result.total;
  const awarded = result.total_awarded ?? 0;
  const pending = result.total_pending ?? 0;
  statsEl.hidden = false;
  statsEl.innerHTML = `
    <span class="stat-chip">匹配 ${raw} 条</span>
    <span class="stat-chip stat-awarded">已中标 ${awarded}</span>
    <span class="stat-chip stat-pending">招标/预告 ${pending}</span>
  `;

  tbody.innerHTML = "";
  (result.records || []).forEach((r, i) => {
    const tr = document.createElement("tr");
    const ptype = r.project_type || (r.winner ? "成交" : "—");
    const link = r.source_url
      ? `<a href="${escAttr(r.source_url)}" target="_blank" rel="noopener">打开</a>`
      : "—";
    tr.innerHTML = `
      <td>${i + 1}</td>
      <td><span class="${typeBadgeClass(r.project_type, r.winner)}">${esc(ptype)}</span></td>
      <td class="col-name">${esc(r.project_name)}</td>
      <td>${esc(r.buyer || "—")}</td>
      <td>${esc(r.winner || "—")}</td>
      <td>${esc(r.amount || "—")}</td>
      <td>${esc(r.bid_date || "—")}</td>
      <td>${esc(r.region || "—")}</td>
      <td>${link}</td>
    `;
    tbody.appendChild(tr);
  });

  if (result.csv_download) {
    download.href = result.csv_download;
    download.hidden = false;
  } else {
    download.hidden = true;
  }

  if (result.report_markdown) {
    reportPreview.textContent = result.report_markdown;
    reportBtn.hidden = false;
    reportPreview.hidden = true;
    reportBtn.textContent = "查看报告";
  } else {
    reportBtn.hidden = true;
    reportPreview.hidden = true;
  }

  const analyzeBtn = document.getElementById("btnAnalyze");
  const productBtn = document.getElementById("btnProductAnalyze");
  const kwText =
    (result.keywords || "").trim() ||
    (document.getElementById("keywords")?.value || "").trim();
  const kwEnc = encodeURIComponent(kwText);
  const hasData =
    (result.total || 0) > 0 ||
    (result.total_raw || 0) > 0 ||
    (result.records && result.records.length > 0);

  if (analyzeBtn) {
    if (currentJobId && hasData) {
      analyzeBtn.hidden = false;
      analyzeBtn.disabled = false;
      analyzeBtn.onclick = () => {
        window.location.href = `/tender-analysis/?job_id=${currentJobId}&keywords=${kwEnc}&auto=1`;
      };
    } else {
      analyzeBtn.hidden = true;
    }
  }
  if (productBtn) {
    if (currentJobId) {
      productBtn.hidden = false;
      productBtn.disabled = !hasData;
      productBtn.title = hasData
        ? "跳转到产品分析（带入任务与关键词，需手动开始）"
        : "筛选结果为 0，请调整条件后重新检索";
      productBtn.onclick = () => {
        if (!hasData) {
          showToast("当前无输出记录，无法产品分析");
          return;
        }
        if (!kwText) {
          showToast("缺少关键词，无法匹配产品清单");
          return;
        }
        window.location.href = `/tender-product-analysis/?source_job_id=${currentJobId}&keywords=${kwEnc}`;
      };
    } else {
      productBtn.hidden = true;
    }
  }
}

function esc(s) {
  const d = document.createElement("div");
  d.textContent = s;
  return d.innerHTML;
}

function escAttr(s) {
  return String(s).replace(/"/g, "&quot;");
}

function updateTaskUI(job) {
  const badge = document.getElementById("taskBadge");
  const msg = document.getElementById("taskMessage");
  const fill = document.getElementById("progressFill");
  const pct = document.getElementById("progressText");

  fill.style.width = `${job.progress || 0}%`;
  pct.textContent = `${job.progress || 0}%`;
  msg.textContent = job.message || "";
  if (job.logs) renderLogs(job.logs);

  if (job.status === "running" || job.status === "queued") {
    badge.textContent = "运行中";
    badge.className = "badge running";
  } else if (job.status === "completed") {
    badge.textContent = "完成";
    badge.className = "badge ok";
  } else if (job.status === "cancelled") {
    badge.textContent = "已中止";
    badge.className = "badge cancelled";
  } else if (job.status === "failed") {
    badge.textContent = "失败";
    badge.className = "badge fail";
  }
}

async function submitTask(e) {
  e.preventDefault();

  const body = buildRequestBody();
  if (!body.keywords) {
    showToast("请输入关键词");
    return;
  }
  if (!body.search_scopes.length) {
    showToast("请至少勾选一个搜索范围");
    return;
  }
  if (infoTypeMode === "custom" && !body.info_types.length) {
    showToast("自定义信息类型时请至少选择一项，或改选「全部」");
    return;
  }
  if (!body.use_saved_credentials && !body.jianyu_phone) {
    showToast("请填写手机号或勾选使用已保存账号");
    return;
  }

  const btn = document.getElementById("btnSubmit");
  btn.disabled = true;
  btn.textContent = "提交中…";

  document.getElementById("taskPanel").hidden = false;
  document.getElementById("resultPanel").hidden = true;
  document.getElementById("taskPanel").scrollIntoView({ behavior: "smooth", block: "start" });
  setStep(2);
  updateTaskUI({ status: "queued", progress: 5, message: "任务已提交…", logs: [] });
  setPhase("login");

  try {
    const res = await fetch(`/api/${SKILL_ID}/run`, {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify(body),
    });
    const data = await res.json();

    if (!res.ok) {
      showToast(data.detail || "提交失败");
      btn.disabled = false;
      btn.textContent = "开始执行任务";
      return;
    }

    showToast("任务已开始，请查看下方爬取过程");
    setStep(3);
    startJobStream(data.job_id);
  } catch (err) {
    showToast("请求失败: " + err.message);
    btn.disabled = false;
    btn.textContent = "开始执行任务";
  }
}

document.getElementById("taskForm").addEventListener("submit", submitTask);
document.getElementById("useSaved").addEventListener("change", toggleCredentialFields);
document.getElementById("btnAbort")?.addEventListener("click", abortCurrentJob);
document.getElementById("btnToggleReport")?.addEventListener("click", () => {
  const el = document.getElementById("reportPreview");
  const btn = document.getElementById("btnToggleReport");
  const show = el.hidden;
  el.hidden = !show;
  btn.textContent = show ? "隐藏报告" : "查看报告";
});

async function loadJobHistory() {
  const ul = document.getElementById("jobHistoryList");
  if (!ul) return;
  try {
    const res = await fetch(`/api/${SKILL_ID}/jobs?limit=15`);
    const data = await res.json();
    const jobs = data.jobs || [];
    if (!jobs.length) {
      ul.innerHTML = "<li class='empty'>暂无历史任务（完成检索后会出现在此）</li>";
      return;
    }
    ul.innerHTML = "";
    jobs.forEach((j) => {
      const li = document.createElement("li");
      const label = `${j.keywords || "检索"} · ${j.total != null ? j.total + "条" : j.job_id}`;
      const time = (j.updated_at || j.saved_at || "").slice(0, 16).replace("T", " ");
      li.innerHTML = `<button type="button" class="history-btn">${esc(label)}</button><span>${esc(time)}</span>`;
      li.querySelector("button").onclick = () => restoreHistoryJob(j.job_id);
      ul.appendChild(li);
    });
  } catch {
    ul.innerHTML = "<li class='empty'>历史任务加载失败</li>";
  }
}

async function restoreHistoryJob(jobId) {
  currentJobId = jobId;
  try {
    const res = await fetch(`/api/${SKILL_ID}/jobs/${jobId}/restore`);
    const data = await res.json();
    if (!res.ok) {
      showToast(data.detail || "恢复失败");
      return;
    }
    const kw = data.keywords || data.meta?.keywords || "";
    if (kw) document.getElementById("keywords").value = kw;
    renderResults({
      keywords: kw,
      total: data.total,
      records: data.records || [],
      csv_download: data.csv_download,
      total_raw: data.meta?.total_raw ?? data.total,
      total_awarded: data.meta?.total_awarded,
      total_pending: data.meta?.total_pending,
    });
    setStep(3);
    document.getElementById("resultPanel").scrollIntoView({ behavior: "smooth", block: "start" });
    showToast("已加载历史任务，可点「产品分析」继续");
  } catch (err) {
    showToast("恢复失败: " + err.message);
  }
}

loadQueryOptions();
loadStatus();
loadJobHistory();
