/* 极简 API 客户端：后台接口使用 JWT Bearer，与前端框架完全解耦。 */
(function () {
  const TOKEN_KEY = "cims_token";
  const USER_KEY = "cims_user";

  function token() {
    return localStorage.getItem(TOKEN_KEY) || "";
  }

  async function request(path, opts = {}) {
    const headers = Object.assign({}, opts.headers || {});
    let body;
    if (opts.form) {
      headers["Content-Type"] = "application/x-www-form-urlencoded";
      body = new URLSearchParams(opts.form);
    } else if (opts.body !== undefined) {
      headers["Content-Type"] = "application/json";
      body = JSON.stringify(opts.body);
    }
    if (token()) headers["Authorization"] = "Bearer " + token();

    const res = await fetch(path, { method: opts.method || "GET", headers, body });
    if (res.status === 204) return null;

    const contentType = res.headers.get("content-type") || "";
    const data = contentType.includes("json")
      ? await res.json().catch(() => null)
      : await res.text();

    if (!res.ok) {
      const err = new Error("请求失败");
      err.status = res.status;
      err.detail = data && data.detail !== undefined ? data.detail : data;
      throw err;
    }
    return data;
  }

  async function download(path) {
    const res = await fetch(path, { headers: { Authorization: "Bearer " + token() } });
    if (!res.ok) throw new Error("下载失败：HTTP " + res.status);
    const blob = await res.blob();
    const disposition = res.headers.get("content-disposition") || "";
    const matched = /filename="?([^"]+)"?/.exec(disposition);
    const filename = matched ? matched[1] : path.split("/").pop() || "download";
    triggerBlobDownload(blob, filename);
  }

  async function upload(path, formData) {
    // 注意：multipart 不要手动设置 Content-Type，浏览器会自动带 boundary
    const res = await fetch(path, {
      method: "POST",
      headers: { Authorization: "Bearer " + token() },
      body: formData,
    });
    const data = await res.json().catch(() => null);
    if (!res.ok) {
      const err = new Error("上传失败");
      err.status = res.status;
      err.detail = data && data.detail !== undefined ? data.detail : data;
      throw err;
    }
    return data;
  }

  function triggerBlobDownload(blob, filename) {
    const url = URL.createObjectURL(blob);
    const a = document.createElement("a");
    a.href = url;
    a.download = filename;
    document.body.appendChild(a);
    a.click();
    a.remove();
    setTimeout(() => URL.revokeObjectURL(url), 1000);
  }

  function qs(params) {
    const usp = new URLSearchParams();
    Object.entries(params || {}).forEach(([k, v]) => {
      if (v !== undefined && v !== null && v !== "") usp.append(k, v);
    });
    const s = usp.toString();
    return s ? "?" + s : "";
  }

  window.API = {
    request,
    download,
    upload,
    qs,
    get: (p, opts) => request(p, Object.assign({ method: "GET" }, opts)),
    post: (p, b) => request(p, { method: "POST", body: b }),
    put: (p, b) => request(p, { method: "PUT", body: b }),
    del: (p) => request(p, { method: "DELETE" }),

    async login(username, password) {
      const data = await request("/api/auth/login", {
        method: "POST",
        form: { username, password },
      });
      localStorage.setItem(TOKEN_KEY, data.access_token);
      localStorage.setItem(USER_KEY, JSON.stringify(data.user));
      return data;
    },
    logout() {
      localStorage.removeItem(TOKEN_KEY);
      localStorage.removeItem(USER_KEY);
    },
    getUser() {
      try {
        return JSON.parse(localStorage.getItem(USER_KEY) || "null");
      } catch (e) {
        return null;
      }
    },
    isAuthed() {
      return !!token();
    },
  };
})();
