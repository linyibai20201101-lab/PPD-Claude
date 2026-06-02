const SKILL_ID = "industry-research";

async function checkStatus() {
  const el = document.getElementById("statusOut");
  try {
    const res = await fetch(`/api/${SKILL_ID}/status`);
    const data = await res.json();
    el.textContent = `API 状态: ${data.status} · ${data.message || ""}`;
  } catch {
    el.textContent = "API 未就绪";
  }
}

checkStatus();
