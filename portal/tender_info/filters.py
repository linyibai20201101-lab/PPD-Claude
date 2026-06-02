"""Record classification, date parsing, and filtering for tender-info."""



from __future__ import annotations



import re

from datetime import date, datetime, timedelta

from typing import List, Optional, Tuple



from .models import TenderInfoRequest



# 项目类型 → 展示优先级（越小越靠前）

TYPE_ORDER = {

    "成交": 0,

    "中标": 0,

    "结果": 1,

    "公示": 1,

    "竞价": 2,

    "招标": 3,

    "询价": 3,

    "预告": 4,

}



AWARDED_TYPE_KEYWORDS = ("成交", "中标", "结果公示", "成交公告", "中标公告")

PENDING_TYPE_KEYWORDS = ("预告", "招标", "询价", "竞价")





def resolve_date_range(request: TenderInfoRequest) -> Tuple[Optional[str], Optional[str]]:

    """根据发布时间预设解析起止日期。"""

    preset = (request.publish_time_preset or "1y").strip()

    if preset == "custom":

        return request.date_from, request.date_to

    if preset in ("", "all", "不限"):

        return request.date_from, request.date_to



    today = date.today()

    days_map = {"7d": 7, "30d": 30, "1y": 365, "3y": 365 * 3, "5y": 365 * 5}

    days = days_map.get(preset)

    if days is None:

        return request.date_from, request.date_to

    start = (today - timedelta(days=days)).isoformat()

    return start, today.isoformat()





def is_awarded_row(row: dict) -> bool:

    winner = str(row.get("中标单位", "") or "").strip()

    if winner:

        return True

    ptype = str(row.get("项目类型", "") or "").strip()

    if ptype in ("成交", "中标", "结果", "公示"):

        return True

    name = str(row.get("项目名称", "") or "")

    return any(k in name for k in ("成交公告", "中标公告", "中标结果", "成交结果"))





def type_sort_key(row: dict) -> Tuple[int, str]:

    ptype = str(row.get("项目类型", "") or "").strip()

    order = TYPE_ORDER.get(ptype, 5)

    if is_awarded_row(row) and order > 1:

        order = 1

    return (order, str(row.get("发布时间", "") or ""))





def parse_jianyu_date(text: str, ref: Optional[date] = None) -> Optional[date]:

    """Parse 剑鱼 list date: '1小时前' / '05-28' / '2025-12-01'."""

    if not text:

        return None

    ref = ref or date.today()

    s = str(text).strip()



    if re.search(r"(小时前|分钟前|刚刚|今天)", s):

        return ref

    m = re.match(r"(\d+)天前", s)

    if m:

        return ref - timedelta(days=int(m.group(1)))



    m = re.match(r"(\d{4})-(\d{1,2})-(\d{1,2})", s)

    if m:

        return date(int(m.group(1)), int(m.group(2)), int(m.group(3)))



    m = re.match(r"(\d{1,2})-(\d{1,2})", s)

    if m:

        return date(ref.year, int(m.group(1)), int(m.group(2)))



    return None





def row_in_date_range(

    row: dict,

    date_from: Optional[str],

    date_to: Optional[str],

    ref: Optional[date] = None,

) -> bool:

    if not date_from and not date_to:

        return True

    parsed = parse_jianyu_date(str(row.get("发布时间", "") or ""), ref=ref)

    if not parsed:

        return True  # 无法解析时保留，避免误删



    if date_from:

        start = datetime.strptime(date_from, "%Y-%m-%d").date()

        if parsed < start:

            return False

    if date_to:

        end = datetime.strptime(date_to, "%Y-%m-%d").date()

        if parsed > end:

            return False

    return True





def row_matches_info_types(row: dict, info_types: List[str]) -> bool:

    """按信息类型筛选；空列表表示全部。"""

    if not info_types:

        return True

    ptype = str(row.get("项目类型", "") or "").strip()

    name = str(row.get("项目名称", "") or "")

    for t in info_types:

        t = t.strip()

        if not t:

            continue

        if t in ptype or t in name:

            return True

        # 模糊：如「询价」匹配「询价采购」

        if ptype and (ptype in t or t in ptype):

            return True

    return False





def row_matches_region(row: dict, region: str) -> bool:

    if not region or region in ("全国", "全部"):

        return True

    area = str(row.get("地区", "") or "")

    # 剑鱼地区格式如「河北-邯郸」

    short = region.replace("省", "").replace("市", "").replace("自治区", "").replace("壮族", "").replace("回族", "").replace("维吾尔", "")

    return region in area or short in area





def filter_and_sort_rows(

    rows: List[dict],

    request: TenderInfoRequest,

) -> Tuple[List[dict], dict]:

    """Apply region/date/info_type filters; sort awarded first."""

    filtered = list(rows)

    date_from, date_to = resolve_date_range(request)



    if request.info_types:

        filtered = [r for r in filtered if row_matches_info_types(r, request.info_types)]



    filtered = [r for r in filtered if row_matches_region(r, request.region or "全国")]



    ref = date.today()

    if date_from:

        try:

            ref = datetime.strptime(date_from, "%Y-%m-%d").date()

        except ValueError:

            pass

    filtered = [r for r in filtered if row_in_date_range(r, date_from, date_to, ref=ref)]



    total_raw = len(filtered)

    awarded = [r for r in filtered if is_awarded_row(r)]

    pending = [r for r in filtered if not is_awarded_row(r)]



    if request.include_pending:

        filtered = sorted(filtered, key=type_sort_key)

    elif request.only_awarded:

        filtered = sorted(awarded, key=type_sort_key)

    else:

        filtered = sorted(filtered, key=type_sort_key)



    stats = {

        "total_raw": total_raw,

        "total_awarded": len(awarded),

        "total_pending": len(pending),

    }

    return filtered, stats

