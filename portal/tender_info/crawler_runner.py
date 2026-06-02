"""Run jianyu_crawler subprocess and parse results."""

from __future__ import annotations

import csv
import json
import os
import shutil
import subprocess
import sys
from pathlib import Path
from typing import Callable, List, Optional, Tuple

from .filters import filter_and_sort_rows
from .models import BidRecord, TenderInfoRequest

PORTAL_ROOT = Path(__file__).resolve().parent.parent
CRAWLER_SCRIPT = PORTAL_ROOT / "skills" / "tender-analysis" / "scripts" / "jianyu_crawler.py"
OUTPUT_BASE = PORTAL_ROOT / "tender_raw_data"
GLOBAL_AUTH = OUTPUT_BASE / "auth_state.json"
CANCEL_EXIT_CODE = 130


class CrawlCancelledError(Exception):
    """用户主动中止爬取。"""

    def __init__(self, message: str = "任务已中止", partial_count: int = 0):
        super().__init__(message)
        self.partial_count = partial_count


def resolve_credentials(request: TenderInfoRequest) -> Tuple[str, str]:
    phone = (request.jianyu_phone or "").strip()
    password = request.jianyu_password or ""

    if request.use_saved_credentials or not phone:
        phone = phone or os.getenv("JIANYU_PHONE", "").strip()
        password = password or os.getenv("JIANYU_PASSWORD", "")

    if not phone:
        raise ValueError("请填写剑鱼标讯手机号，或勾选使用已保存账号并在 .env 中配置 JIANYU_PHONE")
    if not password and not _has_auth_state():
        raise ValueError("请填写登录密码，或确保已有有效登录态（auth_state.json）")

    return phone, password


def _has_auth_state() -> bool:
    return GLOBAL_AUTH.exists()


def _sync_auth_to_job(out_dir: Path) -> None:
    out_dir.mkdir(parents=True, exist_ok=True)
    if GLOBAL_AUTH.exists():
        shutil.copy2(GLOBAL_AUTH, out_dir / "auth_state.json")


def _sync_auth_from_job(out_dir: Path) -> None:
    job_auth = out_dir / "auth_state.json"
    if job_auth.exists():
        OUTPUT_BASE.mkdir(parents=True, exist_ok=True)
        shutil.copy2(job_auth, GLOBAL_AUTH)


def _rows_to_records(rows: List[dict]) -> List[BidRecord]:
    records: List[BidRecord] = []
    for row in rows:
        name = str(row.get("项目名称", "") or "").strip()
        if not name:
            continue
        records.append(
            BidRecord(
                project_name=name,
                buyer=str(row.get("采购单位", "") or "") or None,
                winner=str(row.get("中标单位", "") or "") or None,
                amount=str(row.get("预算金额", "") or "") or None,
                bid_date=str(row.get("发布时间", "") or "") or None,
                region=str(row.get("地区", "") or "") or None,
                project_type=str(row.get("项目类型", "") or "") or None,
                industry=str(row.get("行业类型", "") or "") or None,
                source_url=str(row.get("详情链接", "") or "") or None,
            )
        )
    return records


def _load_rows_from_output(output_dir: Path, log: Callable[[str], None]) -> List[dict]:
    partial = output_dir / "partial_results.json"
    if partial.is_file():
        data = json.loads(partial.read_text(encoding="utf-8"))
        if isinstance(data, list) and data:
            log(f"[解析] 读取部分结果: {partial.name} ({len(data)} 条)")
            return data

    json_files = sorted(output_dir.glob("jianyu_*.json"), key=lambda p: p.stat().st_mtime, reverse=True)
    if json_files:
        data = json.loads(json_files[0].read_text(encoding="utf-8"))
        log(f"[解析] 读取 JSON: {json_files[0].name} ({len(data)} 条)")
        return data if isinstance(data, list) else []

    csv_files = sorted(output_dir.glob("jianyu_*.csv"), key=lambda p: p.stat().st_mtime, reverse=True)
    if not csv_files:
        return []

    rows: List[dict] = []
    with open(csv_files[0], encoding="utf-8-sig", newline="") as f:
        reader = csv.DictReader(f)
        for row in reader:
            rows.append(dict(row))
    log(f"[解析] 读取 CSV: {csv_files[0].name} ({len(rows)} 条)")
    return rows


def _write_filtered_csv(rows: List[dict], out_dir: Path, keyword: str) -> Path:
    out_dir.mkdir(parents=True, exist_ok=True)
    path = out_dir / f"filtered_{keyword[:20]}.csv"
    if not rows:
        return path
    fieldnames = list(rows[0].keys())
    with open(path, "w", encoding="utf-8-sig", newline="") as f:
        writer = csv.DictWriter(f, fieldnames=fieldnames, extrasaction="ignore")
        writer.writeheader()
        writer.writerows(rows)
    return path


def _build_crawler_filters(request: TenderInfoRequest) -> dict:
    return {
        "publish_time_preset": request.publish_time_preset,
        "date_from": request.date_from,
        "date_to": request.date_to,
        "search_scopes": request.search_scopes,
        "info_types": request.info_types,
        "region": request.region or "全国",
    }


def _finalize_rows(
    raw_rows: List[dict],
    request: TenderInfoRequest,
    log: Callable[[str], None],
    out_dir: Path,
    *,
    cancelled: bool = False,
) -> Tuple[List[BidRecord], Optional[str], dict]:
    if not raw_rows:
        if cancelled:
            raise CrawlCancelledError("任务已中止，尚未抓取到数据")
        raise RuntimeError("未抓取到数据，请检查关键词或账号权限")

    filtered, stats = filter_and_sort_rows(raw_rows, request)
    mode = "含预告/招标" if request.include_pending else "仅中标/成交"
    log(
        f"[筛选] 原始 {len(raw_rows)} 条 → 匹配 {stats['total_raw']} 条 "
        f"（已中标 {stats['total_awarded']} / 未中标 {stats['total_pending']}）→ 输出 {len(filtered)} 条 [{mode}]"
    )

    if not filtered:
        if cancelled:
            raise CrawlCancelledError(
                f"任务已中止。共抓到 {stats['total_raw']} 条，筛选后无符合记录。",
                partial_count=len(raw_rows),
            )
        raise RuntimeError(
            f"筛选后无记录。共抓到 {stats['total_raw']} 条，其中已中标 {stats['total_awarded']} 条。"
            "可勾选「包含招标/预告」或放宽日期/地区条件。"
        )

    csv_path = _write_filtered_csv(filtered, out_dir, request.keywords.strip())
    log(f"[导出] 筛选结果 CSV: {csv_path.name}")
    records = _rows_to_records(filtered)
    return records, str(csv_path), stats


def run_crawl(
    request: TenderInfoRequest,
    log: Callable[[str], None],
    output_subdir: Optional[str] = None,
    *,
    job_id: Optional[str] = None,
    should_cancel: Optional[Callable[[], bool]] = None,
    on_proc_started: Optional[Callable[[subprocess.Popen], None]] = None,
) -> Tuple[List[BidRecord], Optional[str], dict]:
    if not CRAWLER_SCRIPT.exists():
        raise FileNotFoundError(f"爬虫脚本不存在: {CRAWLER_SCRIPT}")

    phone, password = resolve_credentials(request)
    out_dir = OUTPUT_BASE / (output_subdir or "default")
    out_dir.mkdir(parents=True, exist_ok=True)
    _sync_auth_to_job(out_dir)

    cancel_file = out_dir / "cancel.flag"
    if cancel_file.exists():
        cancel_file.unlink()

    cmd = [
        sys.executable,
        "-u",
        str(CRAWLER_SCRIPT),
        request.keywords.strip(),
        "--username",
        phone,
        "--password",
        password,
        "--max-pages",
        str(request.max_pages),
        "--output",
        str(out_dir),
        "--cancel-file",
        str(cancel_file),
    ]
    if request.skip_detail:
        cmd.append("--no-detail")
    if request.headless:
        cmd.append("--headless")
    cmd.append("--screenshots")

    filters = _build_crawler_filters(request)
    cmd.extend(["--filters", json.dumps(filters, ensure_ascii=False)])

    log("[启动] 正在登录剑鱼标讯并检索，请稍候…")
    log("[提示] 下方将实时显示爬取日志；右侧可预览浏览器截图")
    log(f"[命令] {' '.join(cmd[:4])} ... --output {out_dir.name}")
    if not request.headless:
        log("[提示] 已打开浏览器窗口；若出现验证码请在窗口内手动完成")

    env = os.environ.copy()
    env["PYTHONUNBUFFERED"] = "1"

    proc = subprocess.Popen(
        cmd,
        stdout=subprocess.PIPE,
        stderr=subprocess.STDOUT,
        text=True,
        encoding="utf-8",
        errors="replace",
        cwd=str(PORTAL_ROOT),
        env=env,
        bufsize=1,
    )
    if on_proc_started:
        on_proc_started(proc)

    assert proc.stdout is not None
    cancelled = False
    for line in proc.stdout:
        if should_cancel and should_cancel():
            cancelled = True
            cancel_file.write_text("1", encoding="utf-8")
            log("[中止] 收到中止请求，正在停止爬虫…")
            try:
                proc.terminate()
            except Exception:
                pass
            break
        line = line.rstrip()
        log(line)

    if not cancelled and should_cancel and should_cancel():
        cancelled = True
        cancel_file.write_text("1", encoding="utf-8")

    if proc.poll() is None:
        try:
            proc.wait(timeout=25)
        except subprocess.TimeoutExpired:
            proc.kill()
            proc.wait()

    code = proc.returncode

    _sync_auth_from_job(out_dir)

    if cancelled or code == CANCEL_EXIT_CODE or cancel_file.exists():
        log("[中止] 爬虫已停止，正在整理已抓取数据…")
        raw_rows = _load_rows_from_output(out_dir, log)
        return _finalize_rows(raw_rows, request, log, out_dir, cancelled=True)

    if code != 0:
        raise RuntimeError(f"爬虫执行失败（退出码 {code}），请查看上方日志")

    raw_rows = _load_rows_from_output(out_dir, log)
    return _finalize_rows(raw_rows, request, log, out_dir, cancelled=False)
