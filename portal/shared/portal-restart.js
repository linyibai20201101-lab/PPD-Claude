/** Shared portal restart control — include on any page under / */

async function portalFetchJson(url, options = {}) {
  const { timeoutMs = 8000, ...fetchOptions } = options;
  const controller = new AbortController();
  const timer = setTimeout(() => controller.abort(), timeoutMs);
  try {
    const res = await fetch(url, {
      cache: "no-store",
      signal: controller.signal,
      ...fetchOptions,
    });
    const data = await res.json().catch(() => ({}));
    return { res, data };
  } finally {
    clearTimeout(timer);
  }
}

async function portalGetBootId() {
  const { res, data } = await portalFetchJson("/api/portal/info");
  if (!res.ok) {
    const err = new Error(data.detail || "无法获取服务信息");
    err.status = res.status;
    throw err;
  }
  return data.boot_id;
}

function portalSleep(ms) {
  return new Promise((r) => setTimeout(r, ms));
}

async function restartPortalService(options = {}) {
  const { onToast, confirmFirst = true, onFinally } = options;

  const toast =
    onToast ||
    ((msg) => {
      if (typeof showToast === "function") showToast(msg);
      else alert(msg);
    });

  if (
    confirmFirst &&
    !confirm("确定重启 portal 服务（8080）？\n\n将加载最新代码，当前连接会短暂中断。")
  ) {
    return { ok: false, reason: "cancelled" };
  }

  let bootBefore = null;
  try {
    bootBefore = await portalGetBootId();
  } catch (e) {
    if (e.status === 404) {
      toast("当前服务版本过旧，没有重启 API。请先在终端运行: cd portal && python server.py");
      return { ok: false, reason: "no_api" };
    }
  }

  let restartAccepted = false;
  try {
    const { res, data } = await portalFetchJson("/api/portal/restart", {
      method: "POST",
      timeoutMs: 5000,
    });
    if (res.status === 404) {
      toast("当前服务版本过旧，请手动重启: python server.py");
      return { ok: false, reason: "no_api" };
    }
    if (!res.ok) {
      toast(data.detail || "重启请求失败");
      return { ok: false, reason: "request_failed" };
    }
    restartAccepted = true;
  } catch {
    // Server may die before the response finishes — treat as accepted.
    restartAccepted = true;
  }

  if (!restartAccepted) {
    return { ok: false, reason: "not_accepted" };
  }

  toast("正在重启服务，请稍候…");

  const deadline = Date.now() + 45000;
  let attempt = 0;

  while (Date.now() < deadline) {
    const waitMs = attempt < 6 ? 1000 : 2000;
    await portalSleep(waitMs);
    attempt += 1;

    try {
      const { res, data } = await portalFetchJson("/api/portal/info", { timeoutMs: 3000 });
      if (!res.ok) continue;
      if (!bootBefore || data.boot_id !== bootBefore) {
        toast("服务已重启，正在刷新页面");
        location.reload();
        return { ok: true, reason: "reloaded" };
      }
    } catch {
      /* server down during restart */
    }
  }

  toast("正在刷新页面…");
  location.reload();
  return { ok: true, reason: "timeout_reload" };
}
