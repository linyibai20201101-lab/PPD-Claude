"""18 个工作 SKILL 智能体成熟度审计（L0–L3）。"""

from __future__ import annotations

import json
import re
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any, Dict, List, Optional

PORTAL_ROOT = Path(__file__).resolve().parent.parent
MANIFEST_PATH = PORTAL_ROOT / "skills" / "manifest.json"

# L0 占位 | L1 工具（API/脚本可用）| L2 编排（模块联动）| L3 智能体（NL+规划+解读）
LEVEL_LABELS = {
    0: "L0 占位",
    1: "L1 工具",
    2: "L2 编排",
    3: "L3 智能体",
}

# 人工维护：覆盖 manifest.status，反映智能体视角真实成熟度
AGENT_OVERRIDES: Dict[str, Dict[str, Any]] = {
    "tender-info": {
        "agent_level": 2,
        "agent_gap": "缺 NL 入口；历史任务 total 需补全索引；运行中任务仍内存态",
        "next_for_agent": "暴露 Agent Tools API；接入对话编排",
        "tools": ["剑鱼爬取", "筛选对齐", "中止", "CSV", "历史恢复", "跳转产品/标讯分析"],
    },
    "tender-analysis": {
        "agent_level": 2,
        "agent_gap": "缺 LLM 解读报告；无自主选参",
        "next_for_agent": "function calling 调 analyze；LLM 写竞争格局摘要",
        "tools": ["清洗去重", "HTML 报告", "联动 job_id"],
    },
    "tender-product-analysis": {
        "agent_level": 2,
        "agent_gap": "S1.7 附件验收未完成；缺 L3 对话与轨迹工作台",
        "next_for_agent": "一站式向导 + 附件 OCR/ZIP；Chat Tool 调 /run",
        "tools": ["关键词匹配", "详情+附件解析", "未命中抽检", "失败重跑", "页内产品表"],
    },
    "planning-ppt": {
        "agent_level": 1,
        "agent_gap": "无对话式改图层",
        "next_for_agent": "Vision 指令编辑图层",
        "tools": ["OCR", "形状检测", "PPT 导出", "PDF 多页"],
    },
    "pm-progress-report": {
        "agent_level": 2,
        "agent_gap": "日报邮件依赖 SMTP 配置",
        "next_for_agent": "定时任务 + 全模块自动审计",
        "tools": ["PROGRESS.md", "日报邮件", "成熟度矩阵"],
    },
    "annual-report": {
        "agent_level": 2,
        "agent_gap": "L3 对话未接 /run；复盘无自动优化 API",
        "next_for_agent": "Tool calling + reflect/optimize 闭环",
        "tools": ["分章分析", "按章选页", "数字校验", "导出", "智能体工作台 UI"],
    },
}


@dataclass
class SkillAudit:
    id: str
    name: str
    category: str
    manifest_status: str
    agent_level: int
    level_label: str
    ui: bool
    api: bool
    api_ready: bool
    skill_doc: bool
    agent_gap: str
    next_for_agent: str
    tools: List[str] = field(default_factory=list)
    deviation: str = ""  # 是否偏离智能体规划


def _slug_to_pkg(slug: str) -> str:
    return slug.replace("-", "_")


def _router_path(sid: str) -> Path:
    pkg = _slug_to_pkg(sid)
    if sid == "planning-ppt":
        pkg = "image_to_ppt"
    return PORTAL_ROOT / pkg / "router.py"


def _api_ready(router_path: Path) -> bool:
    if not router_path.is_file():
        return False
    text = router_path.read_text(encoding="utf-8", errors="replace")
    if "async def run" not in text and "async def analyze" not in text:
        return False
    # 骨架：run/analyze 内直接 501
    if re.search(r"async def (run|analyze)[\s\S]*?raise HTTPException[\s\S]*?501", text):
        return False
    if 'status": "scaffold"' in text and "async def analyze" not in text:
        return False
    return True


def audit_skill(entry: dict) -> SkillAudit:
    sid = entry["id"]
    pkg = _slug_to_pkg(sid)
    ui_dir = PORTAL_ROOT / sid
    if sid == "planning-ppt":
        ui_dir = PORTAL_ROOT / "image-to-ppt"
    router_path = _router_path(sid)
    skill_doc = PORTAL_ROOT / "skills" / sid / "SKILL.md"
    if sid == "pm-progress-report":
        skill_doc = PORTAL_ROOT / "skills" / "pm-progress-report" / "SKILL.md"

    ui_ok = ui_dir.is_dir() and (ui_dir / "index.html").is_file()
    api_ok = router_path.is_file()
    api_ready = _api_ready(router_path) if api_ok else False
    doc_ok = skill_doc.is_file()

    override = AGENT_OVERRIDES.get(sid, {})
    level = override.get("agent_level", 0 if entry.get("status") == "scaffold" else 1)
    if api_ready and level < 1:
        level = 1
    if sid in ("tender-info", "planning-ppt") and level < 1:
        level = 1

    gap = override.get("agent_gap", "未定义 Agent Tools；无 NL 编排")
    nxt = override.get("next_for_agent", "定义 SKILL 工具面 + /run API")
    tools = override.get("tools", [])

    deviation = ""
    if level >= 1 and level < 3 and not gap.startswith("缺"):
        deviation = "符合 Phase1（工具层），未偏离"
    elif level == 0:
        deviation = "仅占位，尚未进入智能体工具链"
    elif level >= 1 and level < 3:
        deviation = "未偏离：先做 Tools，L3 待 Phase2"

    return SkillAudit(
        id=sid,
        name=entry.get("name", sid),
        category=entry.get("category", ""),
        manifest_status=entry.get("status", "scaffold"),
        agent_level=level,
        level_label=LEVEL_LABELS.get(level, "L0 占位"),
        ui=ui_ok,
        api=api_ok,
        api_ready=api_ready,
        skill_doc=doc_ok,
        agent_gap=gap,
        next_for_agent=nxt,
        tools=tools,
        deviation=deviation,
    )


def load_manifest() -> dict:
    return json.loads(MANIFEST_PATH.read_text(encoding="utf-8"))


def audit_all_skills() -> List[SkillAudit]:
    manifest = load_manifest()
    skills = manifest.get("skills", [])
    # 排除 pm-progress-report 从 18 业务智能体计数时可单独列
    return [audit_skill(s) for s in skills]


def summarize(audits: List[SkillAudit]) -> dict:
    business = [a for a in audits if a.id != "pm-progress-report"]
    return {
        "total": len(business),
        "l0": sum(1 for a in business if a.agent_level == 0),
        "l1": sum(1 for a in business if a.agent_level == 1),
        "l2": sum(1 for a in business if a.agent_level == 2),
        "l3": sum(1 for a in business if a.agent_level == 3),
        "api_ready": sum(1 for a in business if a.api_ready),
        "manifest_ready": sum(1 for a in business if a.manifest_status == "ready"),
    }
