"""
ccbaby 网页入口服务
启动: python server.py  或双击 start.bat
访问: http://localhost:8080
"""

import importlib
import json
import os
import subprocess
from pathlib import Path
from typing import Any, Dict, List, Optional

from dotenv import load_dotenv
from fastapi import FastAPI, HTTPException, Request
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import FileResponse, HTMLResponse
from fastapi.staticfiles import StaticFiles
from pydantic import BaseModel

from image_to_ppt.router import configure_router, router as image_to_ppt_router
from annual_report.router import configure_router as configure_annual_report_router
from llm_config import is_allowed_model, list_chat_models
from portal_admin import is_local_client, portal_info, schedule_restart

ROOT = Path(__file__).resolve().parent
PROJECT_ROOT = ROOT.parent
CHAT_DIR = ROOT / "chat"
SHARED_DIR = ROOT / "shared"
WORK_DIR = ROOT / "work"
SKILLS_DIR = ROOT / "skills"
MANIFEST_FILE = SKILLS_DIR / "manifest.json"
IMAGE_TO_PPT_DIR = ROOT / "image-to-ppt"
FAQ_DIR = PROJECT_ROOT / "faq"
DOCS_FILE = PROJECT_ROOT / "Claude-Code-安装运行复盘.md"

EXTERNAL_SKILL_URLS = {"/image-to-ppt/"}

load_dotenv(ROOT / ".env")

ANTHROPIC_API_KEY = os.getenv("ANTHROPIC_API_KEY") or os.getenv("ANTHROPIC_AUTH_TOKEN")
ANTHROPIC_BASE_URL = os.getenv("ANTHROPIC_BASE_URL")
DEFAULT_MODEL = os.getenv("ANTHROPIC_DEFAULT_MODEL", "mimo-v2.5-pro")

app = FastAPI(title="ccbaby Portal")

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

CLAUDE_CMD = Path(os.environ.get("APPDATA", "")) / "npm" / "claude.cmd"
GIT_BASH_PATHS = [
    Path(r"F:\Git\bin\bash.exe"),
    Path(r"C:\Program Files\Git\bin\bash.exe"),
    Path(r"C:\Program Files (x86)\Git\bin\bash.exe"),
]


class Message(BaseModel):
    role: str
    content: str


class ChatRequest(BaseModel):
    messages: List[Message]
    max_tokens: Optional[int] = 4096
    model: Optional[str] = None


def get_anthropic_client():
    import anthropic

    kwargs = {"api_key": ANTHROPIC_API_KEY}
    if ANTHROPIC_BASE_URL:
        kwargs["base_url"] = ANTHROPIC_BASE_URL
    return anthropic.Anthropic(**kwargs)


def extract_response_text(content) -> str:
    texts = []
    for block in content:
        if getattr(block, "type", None) == "text" and getattr(block, "text", None):
            texts.append(block.text)
    if texts:
        return "\n".join(texts)
    for block in content:
        if getattr(block, "text", None):
            return block.text
    raise ValueError("API 返回内容为空")


def find_git_bash() -> Optional[Path]:
    for path in GIT_BASH_PATHS:
        if path.exists():
            return path
    return None


def load_work_manifest() -> Dict[str, Any]:
    if not MANIFEST_FILE.exists():
        return {"version": 1, "categories": [], "skills": []}
    return json.loads(MANIFEST_FILE.read_text(encoding="utf-8"))


def slug_to_pkg(slug: str) -> str:
    return slug.replace("-", "_")


configure_router(
    get_anthropic_client=get_anthropic_client,
    default_model=DEFAULT_MODEL,
    api_key_configured=bool(ANTHROPIC_API_KEY),
)
configure_annual_report_router(
    get_anthropic_client=get_anthropic_client,
    default_model=DEFAULT_MODEL,
    api_key_configured=bool(ANTHROPIC_API_KEY),
    skills_dir=SKILLS_DIR,
    base_url=ANTHROPIC_BASE_URL,
)
app.include_router(image_to_ppt_router)


@app.get("/api/portal/info")
async def get_portal_info():
    from fastapi.responses import JSONResponse

    return JSONResponse(
        portal_info(),
        headers={"Cache-Control": "no-store"},
    )


@app.post("/api/portal/restart")
async def restart_portal(request: Request):
    client_host = request.client.host if request.client else ""
    if not is_local_client(client_host):
        raise HTTPException(status_code=403, detail="仅允许本机 (127.0.0.1) 重启服务")

    schedule_restart(ROOT)
    return {
        "ok": True,
        "message": "正在重启 portal 服务，约 5 秒后可刷新页面",
    }


@app.get("/api/status")
async def status():
    return {
        "status": "ok",
        "claude_installed": CLAUDE_CMD.exists(),
        "git_bash": str(find_git_bash()) if find_git_bash() else None,
        "api_key_configured": bool(ANTHROPIC_API_KEY),
        "base_url": ANTHROPIC_BASE_URL or "https://api.anthropic.com",
        "default_model": DEFAULT_MODEL,
        "project_dir": str(PROJECT_ROOT),
        "llm": list_chat_models(ANTHROPIC_BASE_URL, DEFAULT_MODEL, bool(ANTHROPIC_API_KEY)),
    }


@app.get("/api/models")
async def get_models():
    """可选大模型列表（供对话页等前端使用）。"""
    if not ANTHROPIC_API_KEY:
        raise HTTPException(status_code=503, detail="未配置 API Key，请在 portal/.env 设置 ANTHROPIC_API_KEY")
    return list_chat_models(ANTHROPIC_BASE_URL, DEFAULT_MODEL, True)


@app.post("/api/launch-claude")
async def launch_claude():
    if not CLAUDE_CMD.exists():
        raise HTTPException(
            status_code=404,
            detail="未找到 claude.cmd，请先运行: npm install -g @anthropic-ai/claude-code@latest",
        )

    bat_path = PROJECT_ROOT / "run-claude.bat"
    if bat_path.exists():
        subprocess.Popen(
            ["cmd", "/c", "start", "", str(bat_path)],
            cwd=str(PROJECT_ROOT),
            creationflags=subprocess.CREATE_NEW_CONSOLE,
        )
        return {"ok": True, "message": "Claude Code 已在新终端窗口中启动"}

    env = os.environ.copy()
    git_bash = find_git_bash()
    if git_bash:
        env["CLAUDE_CODE_GIT_BASH_PATH"] = str(git_bash)

    subprocess.Popen(
        ["cmd", "/c", "start", "Claude Code", str(CLAUDE_CMD)],
        cwd=str(PROJECT_ROOT),
        env=env,
        creationflags=subprocess.CREATE_NEW_CONSOLE,
    )
    return {"ok": True, "message": "Claude Code 已在新终端窗口中启动"}


@app.post("/api/chat")
async def chat(request: ChatRequest):
    if not ANTHROPIC_API_KEY:
        raise HTTPException(
            status_code=500,
            detail="API Key 未配置。请复制 .env.example 为 .env 并填入 Key。",
        )

    model = request.model or DEFAULT_MODEL
    if not is_allowed_model(model, ANTHROPIC_BASE_URL):
        raise HTTPException(
            status_code=400,
            detail=f"当前 API 端点不支持模型「{model}」。Token Plan 请使用 mimo-v2.5-pro",
        )

    try:
        client = get_anthropic_client()
        response = client.messages.create(
            model=model,
            max_tokens=request.max_tokens,
            messages=[{"role": m.role, "content": m.content} for m in request.messages],
        )
        return {
            "content": extract_response_text(response.content),
            "model": model,
            "usage": {
                "input_tokens": response.usage.input_tokens,
                "output_tokens": response.usage.output_tokens,
            },
        }
    except ImportError:
        raise HTTPException(status_code=500, detail="请安装 anthropic: pip install anthropic")
    except Exception as e:
        err = str(e)
        if "401" in err or "invalid_key" in err.lower() or "Invalid API Key" in err:
            raise HTTPException(
                status_code=401,
                detail=(
                    "MiMo API Key 无效或已过期。请在 portal/.env 更新 ANTHROPIC_API_KEY，"
                    "并在小米 MiMo 开放平台重新生成 Key；Claude Code 需同步 ANTHROPIC_AUTH_TOKEN。"
                ),
            )
        raise HTTPException(status_code=500, detail=err)


@app.get("/api/health")
async def health_check():
    return {"status": "ok", "api_key_configured": bool(ANTHROPIC_API_KEY)}


@app.get("/api/work/manifest")
async def work_manifest():
    return load_work_manifest()


@app.get("/docs/setup")
async def setup_doc():
    if not DOCS_FILE.exists():
        raise HTTPException(status_code=404, detail="文档不存在")
    content = DOCS_FILE.read_text(encoding="utf-8")
    content_json = json.dumps(content, ensure_ascii=False)
    html = f"""<!DOCTYPE html>
<html lang="zh-CN">
<head>
  <meta charset="UTF-8">
  <meta name="viewport" content="width=device-width, initial-scale=1.0">
  <title>安装复盘 - ccbaby</title>
  <style>
    body {{
      font-family: -apple-system, BlinkMacSystemFont, "Segoe UI", Roboto, sans-serif;
      max-width: 860px; margin: 0 auto; padding: 32px 24px;
      background: #f8fafc; color: #1e293b; line-height: 1.7;
    }}
    a {{ color: #667eea; }}
    pre {{ background: #1e293b; color: #e2e8f0; padding: 16px; border-radius: 8px; overflow-x: auto; }}
    code {{ background: #e2e8f0; padding: 2px 6px; border-radius: 4px; font-size: 0.9em; }}
    pre code {{ background: none; padding: 0; }}
    h1,h2,h3 {{ margin-top: 1.5em; }}
    table {{ border-collapse: collapse; width: 100%; margin: 1em 0; }}
    th, td {{ border: 1px solid #cbd5e1; padding: 8px 12px; text-align: left; }}
    th {{ background: #e2e8f0; }}
    .back {{ display: inline-block; margin-bottom: 24px; text-decoration: none; }}
  </style>
  <script src="https://cdn.jsdelivr.net/npm/marked/marked.min.js"></script>
</head>
<body>
  <a class="back" href="/">← 返回工作台</a>
  <div id="content"></div>
  <script>
    document.getElementById('content').innerHTML = marked.parse({content_json});
  </script>
</body>
</html>"""
    return HTMLResponse(html)


@app.get("/")
async def root():
    return FileResponse(ROOT / "index.html")


if WORK_DIR.exists():
    app.mount("/work", StaticFiles(directory=str(WORK_DIR), html=True), name="work")
if SKILLS_DIR.exists():
    app.mount("/skills", StaticFiles(directory=str(SKILLS_DIR)), name="skills")

_manifest = load_work_manifest()
_registered_ui: set = set()
for _skill in _manifest.get("skills", []):
    _url = _skill.get("url", "")
    if _url in EXTERNAL_SKILL_URLS:
        continue
    _slug = _skill.get("id", "")
    if not _slug or _slug in _registered_ui:
        continue
    _ui_dir = ROOT / _slug
    if _ui_dir.is_dir():
        app.mount(f"/{_slug}", StaticFiles(directory=str(_ui_dir), html=True), name=f"skill-{_slug}")
        _registered_ui.add(_slug)

    _pkg = slug_to_pkg(_slug)
    _router_mod = ROOT / _pkg / "router.py"
    if _router_mod.exists():
        try:
            _mod = importlib.import_module(f"{_pkg}.router")
            app.include_router(_mod.router)
        except ImportError as exc:
            print(f"警告: 无法加载 SKILL API {_pkg}: {exc}")

app.mount("/chat", StaticFiles(directory=str(CHAT_DIR), html=True), name="chat")
if SHARED_DIR.exists():
    app.mount("/shared", StaticFiles(directory=str(SHARED_DIR)), name="shared")
if IMAGE_TO_PPT_DIR.exists():
    app.mount("/image-to-ppt", StaticFiles(directory=str(IMAGE_TO_PPT_DIR), html=True), name="image-to-ppt")
if FAQ_DIR.exists():
    app.mount("/faq", StaticFiles(directory=str(FAQ_DIR), html=True), name="faq")


if __name__ == "__main__":
    import uvicorn

    print("ccbaby 工作台已启动")
    print("访问地址: http://localhost:8080")
    if WORK_DIR.exists():
        print("工作门户: http://localhost:8080/work/")
    if not ANTHROPIC_API_KEY:
        print("提示: portal/.env 中未配置 API Key，网页对话不可用")
    else:
        print(f"对话 API 已就绪 · 模型 {DEFAULT_MODEL}")
        if ANTHROPIC_BASE_URL:
            print(f"Base URL: {ANTHROPIC_BASE_URL}")
    uvicorn.run(app, host="0.0.0.0", port=8080)
