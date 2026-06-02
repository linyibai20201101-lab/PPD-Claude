"""剑鱼标讯工作台查询维度（与 jianyu360 搜索页对齐）."""

from __future__ import annotations

from typing import Any, Dict, List

# 发布时间快捷选项（页面文案与剑鱼一致）
PUBLISH_TIME_PRESETS: List[Dict[str, str]] = [
    {"id": "7d", "label": "近7天"},
    {"id": "30d", "label": "近30天"},
    {"id": "1y", "label": "近1年"},
    {"id": "3y", "label": "近3年"},
    {"id": "5y", "label": "近5年"},
    {"id": "custom", "label": "自定义"},
]

# 搜索范围（多选）
SEARCH_SCOPES: List[Dict[str, Any]] = [
    {"id": "title", "label": "标题", "default": True},
    {"id": "body", "label": "正文", "default": True},
    {"id": "attachment", "label": "附件", "default": False},
    {"id": "subject", "label": "项目名称/标的物", "default": False},
    {"id": "brand", "label": "品牌", "default": False},
    {"id": "buyer", "label": "采购单位", "default": False},
    {"id": "winner", "label": "中标企业", "default": False},
    {"id": "agency", "label": "招标代理机构", "default": False},
]

SCOPE_ID_TO_LABEL = {s["id"]: s["label"] for s in SEARCH_SCOPES}

# 信息类型分组（对标剑鱼「全部 + 分类下拉」）
INFO_TYPE_GROUPS: List[Dict[str, Any]] = [
    {
        "id": "preview",
        "label": "招标预告",
        "items": ["预告", "拟建项目"],
    },
    {
        "id": "announce",
        "label": "招标公告",
        "items": ["招标", "招标公告", "公开招标", "邀请招标", "询价", "竞价", "竞争性谈判", "竞争性磋商", "单一来源"],
    },
    {
        "id": "result",
        "label": "中标结果",
        "items": ["成交", "中标", "中标公告", "中标公示", "成交公告", "结果公示"],
    },
    {
        "id": "other",
        "label": "其他",
        "items": ["变更公告", "废标", "流标", "合同公告", "验收公告", "资格预审", "资格后审"],
    },
]

# 扁平化可选信息类型（供前端 checkbox）
INFO_TYPE_OPTIONS: List[Dict[str, str]] = []
for grp in INFO_TYPE_GROUPS:
    for item in grp["items"]:
        INFO_TYPE_OPTIONS.append({"id": item, "label": item, "group": grp["label"]})

# 地区：默认全国，以下为省级选项
REGIONS: List[Dict[str, str]] = [{"id": "全国", "label": "全国"}] + [
    {"id": name, "label": name}
    for name in [
        "北京市", "天津市", "河北省", "山西省", "内蒙古自治区",
        "辽宁省", "吉林省", "黑龙江省",
        "上海市", "江苏省", "浙江省", "安徽省", "福建省", "江西省", "山东省",
        "河南省", "湖北省", "湖南省",
        "广东省", "广西壮族自治区", "海南省",
        "重庆市", "四川省", "贵州省", "云南省", "西藏自治区",
        "陕西省", "甘肃省", "青海省", "宁夏回族自治区", "新疆维吾尔自治区",
    ]
]

DEFAULT_SEARCH_SCOPES = [s["id"] for s in SEARCH_SCOPES if s.get("default")]


def default_query_options() -> Dict[str, Any]:
    return {
        "publish_time_presets": PUBLISH_TIME_PRESETS,
        "search_scopes": SEARCH_SCOPES,
        "info_type_groups": INFO_TYPE_GROUPS,
        "info_type_options": INFO_TYPE_OPTIONS,
        "regions": REGIONS,
        "defaults": {
            "publish_time_preset": "1y",
            "search_scopes": DEFAULT_SEARCH_SCOPES,
            "info_types": [],  # 空 = 全部
            "region": "全国",
        },
    }
