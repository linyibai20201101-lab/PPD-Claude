const SKILL_ID = "competitor-benchmark";

function applyUrlContext() {
  const p = new URLSearchParams(location.search);
  const company = p.get("company") || "";
  const peers = p.get("peers") || "";
  const industry = p.get("industry") || "";
  const reportId = p.get("report_id") || "";
  const from = p.get("from") || "";

  if (company) document.getElementById("inputCompany").value = company;
  if (peers) document.getElementById("inputPeers").value = peers;
  if (industry) document.getElementById("inputIndustry").value = industry;
  if (reportId) document.getElementById("inputReportId").value = reportId;

  const box = document.getElementById("contextBox");
  if (from === "annual-report" && company) {
    document.getElementById("statusBadge").textContent = "来自年报分析";
    box.innerHTML = `<p><strong>${company}</strong> 年报分析已完成串联。</p>
      <p style="margin-top:8px">可比公司：${peers || "（未指定）"}</p>
      <p>行业：${industry || "—"}</p>
      <p style="margin-top:8px;font-size:0.85rem">report_id: ${reportId || "—"}</p>`;
  }
}

async function checkStatus() {
  const el = document.getElementById("statusOut");
  try {
    const res = await fetch(`/api/${SKILL_ID}/status`);
    const data = await res.json();
    el.textContent = `API: ${data.status} · ${data.message || ""}`;
  } catch {
    el.textContent = "API 未就绪";
  }
}

applyUrlContext();
checkStatus();
