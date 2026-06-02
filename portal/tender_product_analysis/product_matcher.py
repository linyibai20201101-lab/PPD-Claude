"""Keyword + product-attribute matching for tender body and attachment text."""

from __future__ import annotations

import json
import re
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any, Dict, List, Optional, Sequence, Tuple

_ATTR_FILE = Path(__file__).resolve().parent / "product_attributes.json"

ATTRIBUTE_EXPANSIONS: Dict[str, List[str]] = {
    "工业相机": ["机器视觉", "CCD", "CMOS", "面阵", "线扫", "相机", "像素", "分辨率", "帧率"],
    "相机": ["工业相机", "机器视觉", "CCD", "CMOS", "面阵", "线扫", "像素", "分辨率"],
    "光谱": ["光谱仪", "波长", "nm", "分辨率", "单色仪", "分光"],
    "光谱仪": ["光谱", "波长", "nm", "分辨率"],
    "投影": ["投影仪", "投影机", "DLP", "LCD", "流明", "亮度", "投影"],
    "投影仪": ["投影", "投影机", "DLP", "流明"],
    "显微镜": ["光学显微镜", "电子显微镜", "物镜", "目镜", "放大倍数"],
    "传感器": ["变送器", "探测器", "灵敏度", "量程", "精度"],
    "检测仪": ["检测", "测量", "分析仪", "测试仪"],
    "半导体": ["晶圆", "封装", "光刻", "蚀刻", "工艺检测"],
    "内部通话": ["纳雅", "通话主机", "通话腰包", "矩阵主机", "调度台"],
}

PARAM_PATTERNS: List[Tuple[str, str]] = [
    ("品牌", r"(?:品牌|制造商|厂家)[：:\s]*([^\s,，;；\n]{2,40})"),
    ("型号", r"(?:规格型号|型号|Model)[：:\s]*([A-Za-z0-9\-_/\.]{2,40})"),
    ("分辨率", r"(?:分辨率|像素)[：:\s]*([^\s,，;；\n]{2,30})"),
    ("量程", r"(?:量程|测量范围)[：:\s]*([^\s,，;；\n]{2,40})"),
    ("精度", r"(?:精度|准确度)[：:\s]*([^\s,，;；\n]{2,40})"),
]

from .amount_fields import (
    detect_table_header,
    parse_tabular_product_row,
    reconcile_amounts,
)

MODEL_IN_LINE = re.compile(r"\b([A-Za-z][A-Za-z0-9\-_/]{2,24})\b")

NOISE_LINE_PATTERNS = (
    r"^(?:单价|总价|名称|规格型号|采购品目|计量单位|主要技术参数)[：:\t]",
    r"剑鱼标讯|进入工作台|公告摘要|商机推荐|附件下载|立即充值",
    r"^首页$|^全国招标",
)

MATCH_THRESHOLD = 40
MAX_LINES_PER_PROJECT = 30


def _load_external_attribute_expansions() -> Dict[str, List[str]]:
    if not _ATTR_FILE.is_file():
        return {}
    try:
        data = json.loads(_ATTR_FILE.read_text(encoding="utf-8"))
    except (json.JSONDecodeError, OSError):
        return {}
    raw = data.get("attribute_expansions") or data.get("attributes") or {}
    if not isinstance(raw, dict):
        return {}
    out: Dict[str, List[str]] = {}
    for key, vals in raw.items():
        if isinstance(vals, list):
            out[str(key)] = [str(v) for v in vals if v]
    return out


def _merged_attribute_expansions() -> Dict[str, List[str]]:
    merged = dict(ATTRIBUTE_EXPANSIONS)
    for key, vals in _load_external_attribute_expansions().items():
        merged.setdefault(key, [])
        for v in vals:
            if v not in merged[key]:
                merged[key].append(v)
    return merged


def _is_full_model_term(term: str) -> bool:
    """完整型号（如 AFDI-BS450）要求精确匹配，不用 3 字母族前缀误伤同系列其它型号。"""
    t = (term or "").strip()
    return bool(re.search(r"[A-Za-z]", t)) and ("-" in t or len(t) >= 8)


@dataclass
class MatchProfile:
    keyword: str
    primary_terms: List[str] = field(default_factory=list)
    attribute_terms: List[str] = field(default_factory=list)
    model_terms: List[str] = field(default_factory=list)

    def match_terms(self) -> List[str]:
        seen: set[str] = set()
        out: List[str] = []
        for t in self.primary_terms + self.model_terms + self.attribute_terms:
            t = t.strip()
            if len(t) < 3 or t in seen:
                continue
            seen.add(t)
            out.append(t)
        return out


def _split_keywords(keyword: str) -> List[str]:
    raw = re.split(r"[,，、\s/]+", (keyword or "").strip())
    return [t for t in raw if len(t) >= 2]


def build_match_profile(keyword: str) -> MatchProfile:
    primary = _split_keywords(keyword)
    if not primary and keyword:
        primary = [keyword.strip()]

    expansions = _merged_attribute_expansions()
    attrs: List[str] = []
    models: List[str] = []
    for term in primary:
        if re.search(r"[A-Za-z]", term) and len(term) >= 4:
            models.append(term)
        if _is_full_model_term(term):
            attrs.extend(expansions.get(term, []))
            continue
        attrs.extend(expansions.get(term, []))
        for key, vals in expansions.items():
            if key in term or term in key:
                attrs.extend(vals)

    return MatchProfile(
        keyword=keyword or "",
        primary_terms=primary,
        attribute_terms=attrs,
        model_terms=models,
    )


def _is_noise_line(line: str) -> bool:
    if len(line) < 6:
        return True
    for pat in NOISE_LINE_PATTERNS:
        if re.search(pat, line):
            return True
    return False


def _keyword_hits_product_fields(
    profile: MatchProfile, product_name: str, brand: str, model: str
) -> bool:
    blob = f"{product_name} {brand} {model}".lower()
    model_l = (model or "").lower()
    for term in profile.primary_terms + profile.model_terms:
        tl = term.lower()
        if tl in blob:
            return True
        if _is_full_model_term(term):
            if model_l and tl in model_l:
                return True
            if tl in (product_name or "").lower():
                return True
            continue
        # 短系列词（如 AFDI）才用前缀族匹配
        m = re.match(r"^([a-z0-9]{3,})", tl)
        if m and len(term) <= 6 and m.group(1) in blob:
            return True
    for term in profile.attribute_terms:
        if len(term) >= 4 and term.lower() in blob:
            return True
    return False


def extract_params_from_context(text: str) -> Dict[str, str]:
    params: Dict[str, str] = {}
    for name, pat in PARAM_PATTERNS:
        m = re.search(pat, text, re.I)
        if m:
            params[name] = m.group(1).strip()[:80]
    return params


def _parse_gov_table_lines(text: str, profile: MatchProfile) -> List[dict]:
    """Parse 政府采购表：表头识别列 + 数量×单价≈总价校验。"""
    products: List[dict] = []
    if not profile.match_terms():
        return products

    lines = [ln.strip() for ln in text.splitlines() if ln.strip()]
    col_map = detect_table_header(lines)

    for line in lines:
        if _is_noise_line(line):
            continue
        if col_map and any(h in line for h in ("数量", "单价", "总价", "采购标的")):
            if "单价" in line and "数量" in line:
                continue
        parsed = parse_tabular_product_row(line, col_map)
        if not parsed:
            continue
        if not _keyword_hits_product_fields(
            profile,
            parsed["产品名称"],
            parsed.get("品牌", ""),
            parsed.get("型号", ""),
        ):
            continue

        conf = parsed.pop("_amount_confidence", "high")
        score = 90 if conf == "high" else 75 if conf == "medium" else 55

        products.append(
            {
                **parsed,
                "参数来源": "detail_page:table",
                "匹配得分": score,
                "匹配关键词": profile.keyword,
                "规格参数": {
                    "品牌": parsed.get("品牌", ""),
                    "型号": parsed.get("型号", ""),
                    "金额置信度": conf,
                },
            }
        )

    return products


def _parse_numbers_from_groups(groups: Sequence[str]) -> Tuple[Optional[float], Optional[float], Optional[float]]:
    nums: List[float] = []
    for g in groups:
        try:
            nums.append(float(str(g).replace(",", "")))
        except ValueError:
            continue
    if len(nums) >= 3:
        return nums[0], nums[1], nums[2]
    if len(nums) == 2:
        return nums[1], nums[0], None
    if len(nums) == 1:
        return nums[0], None, None
    return None, None, None


def _line_to_product(
    name: str,
    context: str,
    profile: MatchProfile,
    *,
    source: str,
    match_score: int,
    brand: str = "",
    model: str = "",
) -> dict:
    params = extract_params_from_context(context)
    if brand:
        params.setdefault("品牌", brand)
    if model:
        params.setdefault("型号", model)
    row: Dict[str, Any] = {
        "产品名称": name.strip()[:120],
        "品牌": brand,
        "型号": model or params.get("型号", ""),
        "数量": "",
        "单位": "",
        "单价": "",
        "总价": "",
        "参数来源": source,
        "匹配得分": match_score,
        "匹配关键词": profile.keyword,
        "规格参数": params,
    }
    return row


def extract_products_from_text(
    text: str,
    keyword: str,
    *,
    source: str = "detail_page",
    min_score: int = MATCH_THRESHOLD,
) -> List[dict]:
    if not text or len(text.strip()) < 20:
        return []

    profile = build_match_profile(keyword)
    if not profile.match_terms() and not profile.keyword:
        return []

    table_products = _parse_gov_table_lines(text, profile)
    if table_products:
        return _dedupe_products(table_products)[:MAX_LINES_PER_PROJECT]

    lines = [ln.strip() for ln in text.splitlines() if ln.strip() and not _is_noise_line(ln)]
    candidates: List[dict] = []

    for i, line in enumerate(lines):
        if "\t" in line and parse_tabular_product_row(line):
            continue
        if not _keyword_hits_product_fields(profile, line, "", ""):
            continue

        ctx_start = max(0, i - 2)
        ctx_end = min(len(lines), i + 3)
        context = "\n".join(lines[ctx_start:ctx_end])

        tail = re.search(
            r"([\d,.]+(?:\([^)]+\))?)\s+([\d,.]+)\s+([\d,.]+)\s*$", line
        )
        name = line[: tail.start()].strip() if tail else line[:80]
        prod = _line_to_product(
            name, context, profile, source=source, match_score=50
        )
        if tail:
            amounts = reconcile_amounts(tail.group(1), tail.group(2), tail.group(3))
            prod["数量"] = amounts["数量"]
            prod["单位"] = amounts["单位"]
            prod["单价"] = amounts["单价"]
            prod["总价"] = amounts["总价"]
            if amounts.get("_amount_confidence") == "low":
                prod["匹配得分"] = 40
        candidates.append(prod)

    return _dedupe_products(candidates)[:15]


def _dedupe_products(products: List[dict]) -> List[dict]:
    best: Dict[str, dict] = {}
    for p in products:
        name = str(p.get("产品名称", "")).strip()
        model = str(p.get("型号", "")).strip()
        key = f"{name}|{model}"
        if key not in best or p.get("匹配得分", 0) > best[key].get("匹配得分", 0):
            best[key] = p
    return sorted(best.values(), key=lambda x: x.get("匹配得分", 0), reverse=True)


def extract_products_from_attachment_names(
    attachments: List[dict],
    keyword: str,
) -> List[dict]:
    profile = build_match_profile(keyword)
    out: List[dict] = []
    for att in attachments or []:
        name = str(att.get("name") or att.get("文件名") or "").strip()
        if not name or not _keyword_hits_product_fields(profile, name, "", ""):
            continue
        out.append(
            {
                "产品名称": name[:80],
                "型号": "",
                "数量": "",
                "单价": "",
                "总价": "",
                "参数来源": "attachment_meta",
                "匹配得分": 30,
                "匹配关键词": profile.keyword,
                "附件URL": att.get("url", ""),
                "规格参数": {},
            }
        )
    return out


def merge_product_lists(
    *sources: List[dict],
    prefer_source_prefix: str = "attachment",
) -> List[dict]:
    merged: Dict[str, dict] = {}

    def rank_source(src: str) -> int:
        if src.startswith(prefer_source_prefix):
            return 3
        if "table" in src:
            return 3
        if src == "detail_page":
            return 2
        if src == "attachment_meta":
            return 1
        return 0

    for products in sources:
        for p in products or []:
            if not isinstance(p, dict):
                continue
            key = f"{p.get('产品名称','')}|{p.get('型号','')}"
            if key not in merged:
                merged[key] = dict(p)
                continue
            old = merged[key]
            if rank_source(str(p.get("参数来源", ""))) >= rank_source(
                str(old.get("参数来源", ""))
            ):
                for k, v in p.items():
                    if v not in (None, "", [], {}):
                        old[k] = v
            merged[key] = old

    return _dedupe_products(list(merged.values()))


def enrich_project_products(
    item: dict,
    keyword: str,
    body_text: str = "",
) -> dict:
    detail_products = extract_products_from_text(
        body_text, keyword, source="detail_page"
    )
    att_products = extract_products_from_attachment_names(
        item.get("附件列表") or [], keyword
    )
    att_text_products: List[dict] = []
    for block in item.get("附件解析文本") or []:
        if isinstance(block, dict) and block.get("text"):
            att_text_products.extend(
                extract_products_from_text(
                    block["text"],
                    keyword,
                    source=f"attachment:{block.get('name', 'file')}",
                )
            )

    merged = merge_product_lists(detail_products, att_text_products, att_products)
    if merged:
        item["产品明细"] = merged
        item["产品数量"] = len(merged)
        item["总数量"] = sum(
            p.get("数量", 0)
            for p in merged
            if isinstance(p.get("数量"), (int, float))
        )
        item["匹配策略"] = "keyword_table"
    else:
        item["匹配策略"] = "keyword_no_hit"
    return item
