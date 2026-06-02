"""Parse and reconcile quantity / unit price / line total from tender product tables."""

from __future__ import annotations

import re
from typing import Any, Dict, List, Optional, Sequence, Tuple

# 数量：1.00(套) | 1(台) | 1套 | 数量：2
QTY_UNIT_PATTERNS = (
    re.compile(r"^([\d,.]+)\s*[\(（]([^)）]+)[\)）]\s*$"),
    re.compile(r"^([\d,.]+)\s*([台套个件只组批辆平方米m²㎡]+)\s*$", re.I),
    re.compile(r"^([\d,.]+)\s*$"),
)

MONEY_CELL = re.compile(
    r"^[\s¥￥$]*([\d,.]+)\s*(万?元|万元)?\s*$", re.I
)

HEADER_ALIASES: Dict[str, Tuple[str, ...]] = {
    "product": ("采购标的", "标的名称", "货物名称", "产品名称", "名称", "标的"),
    "brand": ("品牌", "制造商", "厂家"),
    "model": ("规格型号", "型号", "规格"),
    "qty": ("数量", "采购数量", "数目"),
    "unit_price": ("单价", "含税单价", "投标单价", "单价(元)", "单价（元）"),
    "total": ("总价", "合价", "金额", "小计", "行金额", "总价(元)", "总价（元）"),
}


def _to_float(s: Any) -> Optional[float]:
    if s is None:
        return None
    t = str(s).strip().replace(",", "").replace("，", "")
    if not t or t in ("—", "-", "/", "无"):
        return None
    m = MONEY_CELL.match(t)
    if m:
        val = float(m.group(1))
        if m.group(2) and "万" in m.group(2):
            return val * 10000
        return val
    try:
        return float(t)
    except ValueError:
        return None


def parse_qty_unit(raw: str) -> Tuple[Any, str]:
    s = (raw or "").strip()
    if not s:
        return "", ""
    for pat in QTY_UNIT_PATTERNS:
        m = pat.match(s)
        if m:
            qty_raw, unit = m.group(1), (m.group(2) if m.lastindex and m.lastindex >= 2 else "")
            q = _to_float(qty_raw)
            if q is not None:
                return (int(q) if q == int(q) else q), (unit or "").strip()
            return qty_raw, (unit or "").strip()
    return s, ""


def parse_money_cell(raw: str) -> Optional[float]:
    return _to_float(raw)


def _find_col_index(headers: Sequence[str], keys: Tuple[str, ...]) -> Optional[int]:
    """Prefer longest exact header match; avoid 品目名称 hitting alias 「名称」."""
    ordered = sorted(keys, key=len, reverse=True)
    for k in ordered:
        for i, h in enumerate(headers):
            h_clean = re.sub(r"\s+", "", str(h))
            if h_clean == k:
                return i
    for k in ordered:
        for i, h in enumerate(headers):
            h_clean = re.sub(r"\s+", "", str(h))
            if k in h_clean:
                if k == "名称" and ("品目" in h_clean or "项目" in h_clean):
                    continue
                return i
    return None


def detect_table_header(lines: List[str]) -> Optional[Dict[str, int]]:
    """Find 品目|标的|数量|单价|总价 header row and return column indices."""
    for line in lines[:40]:
        if "\t" not in line:
            continue
        parts = [p.strip() for p in line.split("\t")]
        if not any("数量" in p or "单价" in p for p in parts):
            continue
        idx = {}
        for key, aliases in HEADER_ALIASES.items():
            col = _find_col_index(parts, aliases)
            if col is not None:
                idx[key] = col
        if "qty" in idx or "unit_price" in idx:
            return idx
    return None


def reconcile_amounts(
    qty: Any,
    unit_price: Any,
    line_total: Any,
    *,
    tolerance: float = 0.02,
) -> Dict[str, Any]:
    """
    Fix swapped 单价/总价 or infer missing field when qty*price≈total.
    Returns dict with 数量, 单价, 总价, 单位, _amount_confidence.
    """
    qty_parsed, unit_from_qty = parse_qty_unit(str(qty)) if qty not in (None, "") else ("", "")
    q = _to_float(qty_parsed) if qty_parsed not in ("", None) else (
        _to_float(qty) if not isinstance(qty, (int, float)) else float(qty)
    )
    p = parse_money_cell(str(unit_price)) if unit_price not in (None, "") else _to_float(unit_price)
    t = parse_money_cell(str(line_total)) if line_total not in (None, "") else _to_float(line_total)

    confidence = "high"
    notes: List[str] = []

    if q and p and t and q > 0 and p > 0 and t > 0:
        expected = q * p
        rel_err = abs(expected - t) / max(t, 1)
        if rel_err <= tolerance:
            pass
        elif abs(q * t - p) / max(p, 1) <= tolerance:
            p, t = t, p
            notes.append("swapped_unit_price_total")
            confidence = "medium"
        else:
            confidence = "low"
            notes.append("qty_price_total_mismatch")
    elif q and p and not t and q > 0:
        t = round(q * p, 2)
        notes.append("inferred_total")
        confidence = "medium"
    elif q and t and not p and q > 0:
        p = round(t / q, 2)
        notes.append("inferred_unit_price")
        confidence = "medium"
    elif p and t and not q and p > 0:
        q_calc = t / p
        if abs(q_calc - round(q_calc)) < 0.01:
            q = int(round(q_calc))
            notes.append("inferred_qty")
            confidence = "medium"

    out_qty = qty_parsed if qty_parsed not in ("", None) else ""
    unit = unit_from_qty
    if q is not None and not out_qty:
        out_qty = int(q) if q == int(q) else q

    return {
        "数量": out_qty if out_qty != "" else (q if q is not None else ""),
        "单位": unit,
        "单价": p if p is not None else unit_price,
        "总价": t if t is not None else line_total,
        "_amount_confidence": confidence,
        "_amount_notes": notes,
    }


def parse_gov_row_strict(line: str) -> Optional[Tuple[str, str, str, str, str, str]]:
    """Legacy 品目\\t品目名\\t标的\\t品牌\\t型号\\t数量\\t单价\\t总价."""
    m = re.match(
        r"^(?:\d+-\d+)\t[^\t]+\t([^\t]+)\t([^\t]*)\t([^\t]+)\t"
        r"([\d,.]+(?:\([^)]+\))?)\t([\d,.]+)\t([\d,.]+)\s*$",
        line.strip(),
    )
    if not m:
        return None
    return m.groups()


def parse_gov_row_by_columns(
    parts: List[str], col_map: Dict[str, int]
) -> Optional[Tuple[str, str, str, str, str, str]]:
    def cell(key: str, default: str = "") -> str:
        i = col_map.get(key)
        if i is None or i >= len(parts):
            return default
        return parts[i].strip()

    product = cell("product")
    if not product:
        if len(parts) >= 3 and re.match(r"^\d+-\d+", parts[0]):
            product = parts[2]
        else:
            return None
    brand = cell("brand")
    model = cell("model")
    qty_raw = cell("qty")
    price_raw = cell("unit_price")
    total_raw = cell("total")

    if not qty_raw and not price_raw and not total_raw:
        nums = []
        for p in reversed(parts):
            if parse_money_cell(p) is not None or QTY_UNIT_PATTERNS[0].match(p):
                nums.insert(0, p)
            elif nums:
                break
        if len(nums) >= 3:
            qty_raw, price_raw, total_raw = nums[0], nums[1], nums[2]
        elif len(nums) == 2:
            qty_raw, price_raw = nums[0], nums[1]

    if not product:
        return None
    return product, brand, model, qty_raw, price_raw, total_raw


def parse_tabular_product_row(
    line: str,
    col_map: Optional[Dict[str, int]] = None,
) -> Optional[Dict[str, Any]]:
    """Parse one TSV product line with optional header column map."""
    line = line.strip()
    if not line or "\t" not in line:
        return None

    parts = line.split("\t")

    row_tuple: Optional[Tuple[str, str, str, str, str, str]] = None
    if col_map:
        row_tuple = parse_gov_row_by_columns(parts, col_map)
    if not row_tuple:
        strict = parse_gov_row_strict(line)
        if strict:
            row_tuple = strict
        elif re.match(r"^\d+-\d+", parts[0]) and len(parts) >= 7:
            row_tuple = (
                parts[2] if len(parts) > 2 else "",
                parts[3] if len(parts) > 3 else "",
                parts[4] if len(parts) > 4 else "",
                parts[5] if len(parts) > 5 else "",
                parts[6] if len(parts) > 6 else "",
                parts[7] if len(parts) > 7 else "",
            )

    if not row_tuple:
        return None

    product_name, brand, model, qty_raw, unit_price, line_total = row_tuple
    amounts = reconcile_amounts(qty_raw, unit_price, line_total)
    return {
        "产品名称": product_name[:120],
        "品牌": brand,
        "型号": model,
        "数量": amounts["数量"],
        "单位": amounts["单位"],
        "单价": amounts["单价"],
        "总价": amounts["总价"],
        "_amount_confidence": amounts["_amount_confidence"],
    }
