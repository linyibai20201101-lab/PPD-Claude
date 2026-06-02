/**
 * Image-to-PPT structural converter frontend
 */

const state = {
  slides: [],
  rawFiles: [],
  currentIndex: 0,
  selectedElementId: null,
  history: [],
  historyIndex: -1,
  analyzing: false,
};

const $ = (sel) => document.querySelector(sel);
const $$ = (sel) => document.querySelectorAll(sel);

function showToast(msg) {
  const t = $("#toast");
  t.textContent = msg;
  t.classList.add("show");
  setTimeout(() => t.classList.remove("show"), 3500);
}

function pushHistory() {
  state.history = state.history.slice(0, state.historyIndex + 1);
  state.history.push(JSON.stringify(state.slides));
  state.historyIndex = state.history.length - 1;
  if (state.history.length > 30) {
    state.history.shift();
    state.historyIndex--;
  }
  updateUndoBtn();
}

function undo() {
  if (state.historyIndex <= 0) return;
  state.historyIndex--;
  state.slides = JSON.parse(state.history[state.historyIndex]);
  state.selectedElementId = null;
  renderAll();
}

function updateUndoBtn() {
  const btn = $("#btnUndo");
  if (btn) btn.disabled = state.historyIndex <= 0;
}

async function loadStatus() {
  try {
    const res = await fetch("/api/image-to-ppt/status");
    const data = await res.json();
    const ocr = $("#statusOcr");
    const vision = $("#statusVision");
    if (data.ocr_available) {
      ocr.textContent = `OCR: ${data.ocr_backend || "就绪"}`;
      ocr.classList.add("ok");
    } else {
      ocr.textContent = "OCR: 未安装";
      ocr.classList.add("warn");
    }
    if (data.vision_available) {
      vision.textContent = "Vision: 可用";
      vision.classList.add("ok");
    } else {
      vision.textContent = "Vision: 未配置";
      vision.classList.add("warn");
    }
  } catch {
    showToast("无法连接后端服务");
  }
}

function getCurrentSlide() {
  return state.slides[state.currentIndex] || null;
}

function getSelectedElement() {
  const slide = getCurrentSlide();
  if (!slide || !state.selectedElementId) return null;
  return slide.elements.find((e) => e.id === state.selectedElementId) || null;
}

function renderPageList() {
  const list = $("#pageList");
  list.innerHTML = "";

  if (!state.slides.length) {
    list.innerHTML = '<p style="color:#64748b;font-size:0.8rem;text-align:center;padding:12px;">暂无页面</p>';
    return;
  }

  state.slides.forEach((slide, i) => {
    const item = document.createElement("div");
    item.className = "page-item" + (i === state.currentIndex ? " active" : "");
    item.innerHTML = `
      <img class="page-thumb" src="${slide.thumbnail || ""}" alt="">
      <div class="page-meta">
        <div class="name">${slide.sourceName || `页面 ${i + 1}`}</div>
        <div class="count">${slide.elements.length} 个元素</div>
      </div>
      <button class="page-remove" title="删除">×</button>
    `;
    item.querySelector(".page-thumb").onclick = () => selectPage(i);
    item.querySelector(".page-meta").onclick = () => selectPage(i);
    item.querySelector(".page-remove").onclick = (e) => {
      e.stopPropagation();
      removePage(i);
    };
    list.appendChild(item);
  });
}

function selectPage(index) {
  state.currentIndex = index;
  state.selectedElementId = null;
  renderAll();
}

function removePage(index) {
  state.slides.splice(index, 1);
  state.rawFiles.splice(index, 1);
  if (state.currentIndex >= state.slides.length) {
    state.currentIndex = Math.max(0, state.slides.length - 1);
  }
  pushHistory();
  renderAll();
}

function renderPreview() {
  const stage = $("#previewStage");
  const empty = $("#emptyState");
  const slide = getCurrentSlide();

  if (!slide) {
    stage.style.display = "none";
    empty.style.display = "block";
    return;
  }

  empty.style.display = "none";
  stage.style.display = "block";
  stage.style.aspectRatio = `${slide.width} / ${slide.height}`;
  stage.style.width = "min(900px, 100%)";

  const rawFile = state.rawFiles[state.currentIndex];
  const bgSrc =
    slide.sourceImage || slide.thumbnail || (rawFile ? URL.createObjectURL(rawFile) : "");

  stage.innerHTML = `
    <img class="bg" src="${bgSrc}" alt="">
    <div class="layer-overlay" id="layerOverlay"></div>
  `;

  const overlay = $("#layerOverlay");
  const scaleX = stage.clientWidth / slide.width;
  const scaleY = stage.clientHeight / slide.height;

  slide.elements.forEach((el, idx) => {
    const box = document.createElement("div");
    box.className = `layer-box ${el.type}${el.id === state.selectedElementId ? " selected" : ""}`;
    box.style.left = `${(el.x / slide.width) * 100}%`;
    box.style.top = `${(el.y / slide.height) * 100}%`;
    box.style.width = `${(el.w / slide.width) * 100}%`;
    box.style.height = `${(el.h / slide.height) * 100}%`;
    box.dataset.id = el.id;

    const label = document.createElement("span");
    label.className = "layer-label";
    label.textContent = el.type === "text" ? (el.text || "").slice(0, 12) : el.type;
    box.appendChild(label);

    box.addEventListener("click", (e) => {
      e.stopPropagation();
      selectElement(el.id);
    });

    makeDraggable(box, el, slide);
    overlay.appendChild(box);
  });
}

function makeDraggable(box, el, slide) {
  let startX, startY, origX, origY;

  box.addEventListener("mousedown", (e) => {
    if (e.button !== 0) return;
    e.preventDefault();
    selectElement(el.id);
    startX = e.clientX;
    startY = e.clientY;
    origX = el.x;
    origY = el.y;

    const onMove = (ev) => {
      const stage = $("#previewStage");
      const dx = ((ev.clientX - startX) / stage.clientWidth) * slide.width;
      const dy = ((ev.clientY - startY) / stage.clientHeight) * slide.height;
      el.x = Math.max(0, Math.min(slide.width - el.w, origX + dx));
      el.y = Math.max(0, Math.min(slide.height - el.h, origY + dy));
      box.style.left = `${(el.x / slide.width) * 100}%`;
      box.style.top = `${(el.y / slide.height) * 100}%`;
      renderProps();
    };

    const onUp = () => {
      document.removeEventListener("mousemove", onMove);
      document.removeEventListener("mouseup", onUp);
      pushHistory();
    };

    document.addEventListener("mousemove", onMove);
    document.addEventListener("mouseup", onUp);
  });
}

function selectElement(id) {
  state.selectedElementId = id;
  renderPreview();
  renderLayerList();
  renderProps();
}

function renderLayerList() {
  const list = $("#layerList");
  const slide = getCurrentSlide();
  if (!slide) {
    list.innerHTML = "";
    return;
  }

  list.innerHTML = "";
  [...slide.elements].reverse().forEach((el) => {
    const item = document.createElement("div");
    item.className = "layer-list-item" + (el.id === state.selectedElementId ? " selected" : "");
    const preview = el.type === "text" ? (el.text || "").slice(0, 20) : el.type;
    item.innerHTML = `<span class="type-dot ${el.type}"></span><span>${preview}</span>`;
    item.onclick = () => selectElement(el.id);
    list.appendChild(item);
  });
}

function renderProps() {
  const panel = $("#propsPanel");
  const el = getSelectedElement();

  if (!el) {
    panel.innerHTML = '<p style="color:#64748b;font-size:0.82rem;">点击图层或预览区元素进行编辑</p>';
    return;
  }

  let html = `
    <div class="field"><label>类型</label><input value="${el.type}" disabled></div>
    <div class="field"><label>X</label><input type="number" id="propX" value="${Math.round(el.x)}"></div>
    <div class="field"><label>Y</label><input type="number" id="propY" value="${Math.round(el.y)}"></div>
    <div class="field"><label>宽</label><input type="number" id="propW" value="${Math.round(el.w)}"></div>
    <div class="field"><label>高</label><input type="number" id="propH" value="${Math.round(el.h)}"></div>
  `;

  if (el.type === "text") {
    html += `
      <div class="field"><label>文字</label><textarea id="propText">${el.text || ""}</textarea></div>
      <div class="field"><label>字号</label><input type="number" id="propFontSize" value="${Math.round(el.fontSize || 16)}"></div>
      <div class="field"><label>颜色</label><input type="text" id="propColor" value="${el.color || "#1a1a1a"}"></div>
      <div class="checkbox-row"><input type="checkbox" id="propBold" ${el.bold ? "checked" : ""}><label for="propBold">粗体</label></div>
    `;
  } else if (el.type === "shape") {
    html += `
      <div class="field"><label>填充色</label><input type="text" id="propFill" value="${el.fill || ""}"></div>
      <div class="field"><label>描边色</label><input type="text" id="propStroke" value="${el.stroke || ""}"></div>
    `;
  }

  panel.innerHTML = html;

  const bind = (id, key, parser = (v) => v) => {
    const input = document.getElementById(id);
    if (!input) return;
    input.addEventListener("change", () => {
      el[key] = parser(input.value);
      pushHistory();
      renderPreview();
      renderLayerList();
    });
  };

  bind("propX", "x", parseFloat);
  bind("propY", "y", parseFloat);
  bind("propW", "w", parseFloat);
  bind("propH", "h", parseFloat);
  bind("propText", "text");
  bind("propFontSize", "fontSize", parseFloat);
  bind("propColor", "color");
  bind("propFill", "fill");
  bind("propStroke", "stroke");

  const bold = document.getElementById("propBold");
  if (bold) {
    bold.addEventListener("change", () => {
      el.bold = bold.checked;
      pushHistory();
    });
  }
}

function renderAll() {
  renderPageList();
  renderPreview();
  renderLayerList();
  renderProps();
  $("#btnExport").disabled = !state.slides.length;
  $("#btnReanalyze").disabled = !state.slides.length || state.analyzing;
}

async function analyzeFiles(files) {
  if (!files.length) return;

  state.analyzing = true;
  $("#progressBar").classList.add("show");
  $("#progressFill").style.width = "20%";
  $("#btnAnalyze").disabled = true;

  const form = new FormData();
  for (const f of files) form.append("files", f);
  form.append("use_vision", $("#useVision").checked ? "true" : "false");
  form.append("detect_shapes", $("#detectShapes").checked ? "true" : "false");
  form.append("detect_images", $("#detectImages").checked ? "true" : "false");

  try {
    $("#progressFill").style.width = "50%";
    const res = await fetch("/api/image-to-ppt/analyze", { method: "POST", body: form });
    const data = await res.json();

    if (!res.ok) {
      showToast(data.detail || "识别失败");
      return;
    }

    $("#progressFill").style.width = "90%";
    state.slides = data.slides;
    state.rawFiles = files.filter((f) => !f.name.toLowerCase().endsWith(".pdf"));
    if (state.rawFiles.length < state.slides.length) {
      state.rawFiles = Array(state.slides.length).fill(null);
    }
    state.currentIndex = 0;
    state.selectedElementId = null;
    pushHistory();
    renderAll();
    showToast(`已识别 ${data.slides.length} 页，共 ${data.slides.reduce((n, s) => n + s.elements.length, 0)} 个元素`);
  } catch (e) {
    showToast("请求失败: " + e.message);
  } finally {
    state.analyzing = false;
    $("#progressFill").style.width = "100%";
    setTimeout(() => {
      $("#progressBar").classList.remove("show");
      $("#progressFill").style.width = "0%";
    }, 500);
    $("#btnAnalyze").disabled = false;
  }
}

async function reanalyzeCurrent() {
  const slide = getCurrentSlide();
  const file = state.rawFiles[state.currentIndex];
  if (!slide) return;

  state.analyzing = true;
  $("#btnReanalyze").disabled = true;

  try {
    let blob;
    if (file) {
      blob = file;
    } else if (slide.sourceImage) {
      const resp = await fetch(slide.sourceImage);
      blob = await resp.blob();
    } else if (slide.thumbnail) {
      const resp = await fetch(slide.thumbnail);
      blob = await resp.blob();
    } else {
      showToast("无法重新识别：缺少原始图片");
      return;
    }

    const form = new FormData();
    form.append("file", blob, slide.sourceName || "page.png");
    form.append("use_vision", $("#useVision").checked ? "true" : "false");
    form.append("detect_shapes", $("#detectShapes").checked ? "true" : "false");
    form.append("detect_images", $("#detectImages").checked ? "true" : "false");

    const res = await fetch("/api/image-to-ppt/reanalyze", { method: "POST", body: form });
    const data = await res.json();
    if (!res.ok) {
      showToast(data.detail || "重新识别失败");
      return;
    }

    state.slides[state.currentIndex] = data;
    state.selectedElementId = null;
    pushHistory();
    renderAll();
    showToast("当前页已重新识别");
  } catch (e) {
    showToast("重新识别失败: " + e.message);
  } finally {
    state.analyzing = false;
    $("#btnReanalyze").disabled = false;
  }
}

async function exportPptx() {
  if (!state.slides.length) return;

  const filename = $("#fileNameInput").value.trim() || "presentation";
  $("#btnExport").disabled = true;
  $("#btnExport").textContent = "导出中…";

  const slidesForExport = state.slides.map(({ sourceImage, thumbnail, ...rest }) => rest);

  try {
    const res = await fetch("/api/image-to-ppt/export", {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({ slides: slidesForExport, filename }),
    });

    if (!res.ok) {
      const err = await res.json();
      showToast(err.detail || "导出失败");
      return;
    }

    const blob = await res.blob();
    const url = URL.createObjectURL(blob);
    const a = document.createElement("a");
    a.href = url;
    a.download = filename.endsWith(".pptx") ? filename : filename + ".pptx";
    a.click();
    URL.revokeObjectURL(url);
    showToast("PPTX 已下载");
  } catch (e) {
    showToast("导出失败: " + e.message);
  } finally {
    $("#btnExport").disabled = false;
    $("#btnExport").textContent = "导出 PPTX";
  }
}

function setupUpload() {
  const dropzone = $("#dropzone");
  const fileInput = $("#fileInput");

  dropzone.addEventListener("click", () => fileInput.click());
  fileInput.addEventListener("change", (e) => {
    const files = Array.from(e.target.files || []);
    if (files.length) analyzeFiles(files);
    fileInput.value = "";
  });

  dropzone.addEventListener("dragover", (e) => {
    e.preventDefault();
    dropzone.classList.add("dragover");
  });
  dropzone.addEventListener("dragleave", () => dropzone.classList.remove("dragover"));
  dropzone.addEventListener("drop", (e) => {
    e.preventDefault();
    dropzone.classList.remove("dragover");
    const files = Array.from(e.dataTransfer.files || []);
    if (files.length) analyzeFiles(files);
  });
}

document.addEventListener("DOMContentLoaded", () => {
  setupUpload();
  loadStatus();
  renderAll();

  $("#btnExport").addEventListener("click", exportPptx);
  $("#btnReanalyze").addEventListener("click", reanalyzeCurrent);
  $("#btnUndo").addEventListener("click", undo);
  $("#btnAnalyze").addEventListener("click", () => $("#fileInput").click());
});
