let manifest = null;
let activeCategory = "all";
let searchQuery = "";

const CATEGORY_ICONS = {
  "market-policy": "📊",
  "product-planning": "📐",
  "tech-rd": "🔬",
  "finance": "📈",
  "ecommerce": "🛒",
};

async function loadManifest() {
  const res = await fetch("/api/work/manifest");
  manifest = await res.json();
  renderTabs();
  renderSkills();
  document.getElementById("skillCount").textContent = manifest.skills.length;
}

function renderTabs() {
  const container = document.getElementById("categoryTabs");
  container.innerHTML = "";

  const allTab = document.createElement("button");
  allTab.className = "tab active";
  allTab.textContent = "全部";
  allTab.onclick = () => setCategory("all");
  container.appendChild(allTab);

  for (const cat of manifest.categories) {
    const tab = document.createElement("button");
    tab.className = "tab";
    tab.textContent = `${CATEGORY_ICONS[cat.id] || ""} ${cat.name}`;
    tab.onclick = () => setCategory(cat.id);
    container.appendChild(tab);
  }
}

function setCategory(id) {
  activeCategory = id;
  document.querySelectorAll(".tab").forEach((t, i) => {
    const isAll = id === "all" && i === 0;
    const cat = manifest.categories[i - 1];
    t.classList.toggle("active", isAll || (cat && cat.id === id));
  });
  renderSkills();
}

function filterSkills() {
  return manifest.skills.filter((s) => {
    const matchCat = activeCategory === "all" || s.category === activeCategory;
    const q = searchQuery.toLowerCase();
    const matchSearch =
      !q ||
      s.name.toLowerCase().includes(q) ||
      s.description.toLowerCase().includes(q) ||
      s.id.toLowerCase().includes(q);
    return matchCat && matchSearch;
  });
}

function renderSkills() {
  const container = document.getElementById("skillSections");
  const skills = filterSkills();
  container.innerHTML = "";

  if (skills.length === 0) {
    container.innerHTML = '<div class="empty">未找到匹配的 SKILL</div>';
    return;
  }

  if (activeCategory === "all") {
    for (const cat of manifest.categories) {
      const catSkills = skills.filter((s) => s.category === cat.id);
      if (catSkills.length === 0) continue;
      container.appendChild(buildSection(cat.name, catSkills));
    }
  } else {
    const cat = manifest.categories.find((c) => c.id === activeCategory);
    container.appendChild(buildSection(cat ? cat.name : "", skills));
  }
}

function buildSection(title, skills) {
  const section = document.createElement("div");
  if (title) {
    const h2 = document.createElement("h2");
    h2.className = "section-title";
    h2.textContent = title;
    section.appendChild(h2);
  }

  const grid = document.createElement("div");
  grid.className = "cards";

  for (const skill of skills) {
    grid.appendChild(buildCard(skill));
  }

  section.appendChild(grid);
  return section;
}

function buildCard(skill) {
  const card = document.createElement("div");
  card.className = "card";

  const badgeClass = skill.status === "ready" ? "ready" : "scaffold";
  const badgeText = skill.status === "ready" ? "可用" : "开发中";

  const tags = (skill.inputTypes || [])
    .map((t) => `<span class="tag">${t}</span>`)
    .join("");

  card.innerHTML = `
    <div class="card-top">
      <h3>${skill.name}</h3>
      <span class="badge ${badgeClass}">${badgeText}</span>
    </div>
    <p>${skill.description}</p>
    <div class="input-tags">${tags}</div>
    <a class="btn" href="${skill.url}">进入 SKILL</a>
  `;
  return card;
}

document.getElementById("searchBox").addEventListener("input", (e) => {
  searchQuery = e.target.value.trim();
  renderSkills();
});

loadManifest().catch(() => {
  document.getElementById("skillSections").innerHTML =
    '<div class="empty">无法加载 SKILL 列表，请确认 portal 服务正在运行</div>';
});
