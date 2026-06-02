"""LLM model registry for portal chat and vision features."""

from __future__ import annotations

from typing import Any, Dict, List, Optional

# 小米 MiMo（Anthropic 兼容 API）
# token_plan=True 表示在 Token Plan 套餐（token-plan*.xiaomimimo.com）下可用
XIAOMI_MIMO_MODELS: List[Dict[str, Any]] = [
    {
        "id": "mimo-v2.5-pro",
        "name": "MiMo V2.5 Pro",
        "description": "旗舰模型，复杂推理、代码与长文本（推荐）",
        "provider": "xiaomi",
        "token_plan": True,
        "default": True,
    },
    {
        "id": "mimo-v2.5-flash",
        "name": "MiMo V2.5 Flash",
        "description": "更快响应，适合日常对话（需小米开放平台 API，Token Plan 暂不支持）",
        "provider": "xiaomi",
        "token_plan": False,
    },
    {
        "id": "mimo-v2-pro",
        "name": "MiMo V2 Pro",
        "description": "上一代模型（将逐步迁移至 V2.5）",
        "provider": "xiaomi",
        "token_plan": False,
    },
]


def _is_token_plan_base(base_url: Optional[str]) -> bool:
    if not base_url:
        return False
    return "token-plan" in base_url.lower() or "token_plan" in base_url.lower()


def _is_xiaomi_base(base_url: Optional[str]) -> bool:
    if not base_url:
        return False
    return "xiaomimimo.com" in base_url.lower()


def list_chat_models(
    base_url: Optional[str],
    default_model: str,
    api_key_configured: bool,
) -> Dict[str, Any]:
    """Return model groups for frontend selector."""
    groups: List[Dict[str, Any]] = []

    if api_key_configured and _is_xiaomi_base(base_url):
        token_plan = _is_token_plan_base(base_url)
        models = []
        for m in XIAOMI_MIMO_MODELS:
            available = m["token_plan"] if token_plan else True
            models.append(
                {
                    "id": m["id"],
                    "name": m["name"],
                    "description": m["description"],
                    "available": available,
                    "unavailable_reason": (
                        "当前为 Token Plan 套餐，仅支持 mimo-v2.5-pro"
                        if token_plan and not m["token_plan"]
                        else None
                    ),
                }
            )
        groups.append(
            {
                "id": "xiaomi",
                "name": "小米 MiMo",
                "models": models,
            }
        )

    # 非小米端点时仍可手动扩展；默认只展示 MiMo
    default = default_model
    if not any(m["id"] == default for g in groups for m in g["models"]):
        # 确保 .env 默认模型出现在列表中
        if groups and groups[0]["models"]:
            if not any(x["id"] == default for x in groups[0]["models"]):
                groups[0]["models"].insert(
                    0,
                    {
                        "id": default,
                        "name": default,
                        "description": "来自 ANTHROPIC_DEFAULT_MODEL 配置",
                        "available": True,
                        "unavailable_reason": None,
                    },
                )

    return {
        "default_model": default,
        "provider_hint": "xiaomi" if _is_xiaomi_base(base_url) else "anthropic",
        "token_plan": _is_token_plan_base(base_url),
        "groups": groups,
    }


def is_allowed_model(model_id: str, base_url: Optional[str]) -> bool:
    """Validate model id before API call."""
    if _is_token_plan_base(base_url):
        return model_id == "mimo-v2.5-pro"
    if _is_xiaomi_base(base_url):
        allowed = {m["id"] for m in XIAOMI_MIMO_MODELS}
        allowed.add("mimo-v2.5-pro")
        return model_id in allowed
    return bool(model_id.strip())
