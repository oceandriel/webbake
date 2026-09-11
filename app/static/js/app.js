/* ============================================================
 * 后台管理 SPA（hash 路由）
 * 纯 JS 通过 REST API 与 FastAPI 交互，可整体替换为任意前端。
 * ============================================================ */

const appEl = document.getElementById("app");

/* ---------- Toast ---------- */
let toastTimer = null;
function toast(message, type) {
  const el = document.getElementById("toast");
  el.textContent = message;
  el.className = "toast show " + (type || "");
  clearTimeout(toastTimer);
  toastTimer = setTimeout(() => (el.className = "toast"), 2600);
}

function errMessage(err, fallback) {
  if (!err) return fallback || "操作失败";
  if (typeof err.detail === "string") return err.detail;
  if (Array.isArray(err.detail)) {
    return err.detail
      .map((d) => (d.loc ? d.loc.slice(1).join(".") + ": " + d.msg : d.msg))
      .join("；") || fallback;
  }
  if (err.detail && typeof err.detail === "object") {
    return Object.entries(err.detail)
      .map(([k, v]) => k + ": " + v)
      .join("；");
  }
  return fallback || err.message || "操作失败";
}

/* ---------- 弹窗 ---------- */
function openModal({ title, body, submitText, wide, onSubmit }) {
  const mask = document.createElement("div");
  mask.className = "modal-mask";
  mask.innerHTML =
    '<div class="modal' + (wide ? " wide" : "") + '">' +
    '<header><h3></h3><button class="close" type="button">&times;</button></header>' +
    '<div class="body"></div>' +
    (onSubmit ? '<footer><button class="secondary" type="button" data-act="cancel">取消</button>' +
      '<button type="button" data-act="ok"></button></footer>' : "") +
    "</div>";
  mask.querySelector("h3").textContent = title;
  mask.querySelector(".body").innerHTML = body;
  if (onSubmit) mask.querySelector('[data-act="ok"]').textContent = submitText || "保存";

  function close() {
    mask.remove();
    document.removeEventListener("keydown", onKey);
  }
  function onKey(e) {
    if (e.key === "Escape") close();
  }
  mask.addEventListener("click", (e) => {
    if (e.target === mask || e.target.classList.contains("close") ||
        e.target.getAttribute("data-act") === "cancel") close();
  });
  if (onSubmit) {
    mask.querySelector('[data-act="ok"]').addEventListener("click", async (e) => {
      const btn = e.currentTarget;
      btn.disabled = true;
      const oldText = btn.textContent;
      btn.textContent = "处理中...";
      try {
        const keepOpen = await onSubmit(mask);
        if (!keepOpen) close();
      } catch (err) {
        toast(errMessage(err), "error");
      } finally {
        btn.disabled = false;
        btn.textContent = oldText;
      }
    });
  }
  document.addEventListener("keydown", onKey);
  document.body.appendChild(mask);
  return mask;
}

/* ---------- 路由 ---------- */
function navigate() {
  const hash = location.hash || "#/projects";

  const publicMatch = hash.match(/^#\/form\/([\w-]+)/);
  if (publicMatch) return renderPublicForm(publicMatch[1]);
  if (hash === "#/forms") return renderPublicProjectList();

  if (hash === "#/login") return renderLogin();

  if (!API.isAuthed()) {
    location.hash = "#/login";
    return;
  }

  renderShell(hash);
}
window.addEventListener("hashchange", navigate);

/* ---------- 登录 ---------- */
function renderLogin() {
  appEl.innerHTML =
    '<div class="auth-wrap"><div class="card auth-card">' +
    '<div class="logo2">▤</div><h1>客户信息管理系统</h1>' +
    '<div class="sub">请使用管理员账号登录后台</div>' +
    '<form id="loginForm">' +
    '<div class="form-row"><label class="field-label">账号</label>' +
    '<input name="username" autocomplete="username" required value="admin" /></div>' +
    '<div class="form-row"><label class="field-label">密码</label>' +
    '<input name="password" type="password" autocomplete="current-password" required /></div>' +
    '<button type="submit" style="width:100%;padding:10px">登 录</button>' +
    '<div class="auth-foot"><a href="#/forms">客户填报入口 →</a></div>' +
    "</form></div></div>";

  document.getElementById("loginForm").addEventListener("submit", async (e) => {
    e.preventDefault();
    const fd = new FormData(e.target);
    const btn = e.target.querySelector("button");
    btn.disabled = true;
    btn.textContent = "登录中...";
    try {
      await API.login(fd.get("username"), fd.get("password"));
      location.hash = "#/projects";
    } catch (err) {
      toast(errMessage(err, "登录失败"), "error");
      btn.disabled = false;
      btn.textContent = "登 录";
    }
  });
  e_focus();
}
function e_focus() {
  const input = document.querySelector('#loginForm input[name="password"]');
  if (input) input.focus();
}

/* ---------- 后台外壳 ---------- */
const NAV_ITEMS = [
  { hash: "#/projects", icon: "▤", label: "项目管理" },
  { hash: "#/email", icon: "✉", label: "邮件提醒" },
  { hash: "#/backup", icon: "⤓", label: "备份与恢复" },
  { hash: "#/contract", icon: "{ }", label: "接口契约" },
];

function renderShell(hash) {
  const user = API.getUser();
  const active = hash.startsWith("#/projects") ? "#/projects" : hash.split("?")[0];
  appEl.innerHTML =
    '<div class="layout">' +
    '<aside class="sidebar">' +
    '<div class="brand"><span class="logo">C</span>客户信息管理</div>' +
    "<nav>" +
    NAV_ITEMS.map(
      (n) =>
        `<a href="${n.hash}" class="${active === n.hash ? "active" : ""}">${n.icon} ${n.label}</a>`
    ).join("") +
    "</nav>" +
    '<div class="foot">登录账号：' + esc(user ? user.username : "") +
    '<button class="secondary" id="logoutBtn" type="button">退出登录</button></div>' +
    "</aside>" +
    '<div class="main"><header class="topbar"><h1 id="pageTitle"></h1></header>' +
    '<div class="content" id="view"></div></div></div>';

  document.getElementById("logoutBtn").addEventListener("click", () => {
    API.logout();
    location.hash = "#/login";
  });

  if (hash === "#/projects" || hash === "#/" || hash === "") return projectsView();
  const m = hash.match(/^#\/projects\/(\d+)/);
  if (m) return projectView(Number(m[1]));
  if (hash === "#/email") return emailView();
  if (hash === "#/backup") return backupView();
  if (hash === "#/contract") return contractView();
  return projectsView();
}

/* ---------- 项目列表 ---------- */
const projState = { page: 1, pageSize: 10, q: "" };

function projectsView() {
  document.getElementById("pageTitle").textContent = "项目管理";
  const view = document.getElementById("view");
  view.innerHTML =
    '<div class="toolbar"><div class="left">' +
    '<input id="projSearch" style="width:240px" placeholder="按项目名称 / slug 搜索" />' +
    '<button class="secondary" id="projSearchBtn">查询</button></div>' +
    '<button id="projCreate">+ 新建项目</button></div>' +
    '<div class="card"><div class="table-wrap"><table><thead><tr>' +
    "<th>ID</th><th>项目名称</th><th>Slug</th><th>状态</th><th>创建时间</th><th>操作</th>" +
    "</tr></thead><tbody id='projBody'></tbody></table></div>" +
    '<div class="pager"><span class="muted" id="projTotal"></span>' +
    '<button class="secondary" id="projPrev">上一页</button>' +
    '<button class="secondary" id="projNext">下一页</button></div></div>';

  document.getElementById("projSearch").value = projState.q;
  document.getElementById("projSearchBtn").onclick = () => {
    projState.q = document.getElementById("projSearch").value.trim();
    projState.page = 1;
    loadProjects();
  };
  document.getElementById("projSearch").addEventListener("keydown", (e) => {
    if (e.key === "Enter") document.getElementById("projSearchBtn").click();
  });
  document.getElementById("projCreate").onclick = () => projectDialog(null, loadProjects);
  document.getElementById("projPrev").onclick = () => {
    if (projState.page > 1) { projState.page--; loadProjects(); }
  };
  document.getElementById("projNext").onclick = () => {
    projState.page++;
    loadProjects();
  };
  loadProjects();
}

async function loadProjects() {
  const body = document.getElementById("projBody");
  body.innerHTML = '<tr><td colspan="6" class="empty">加载中...</td></tr>';
  try {
    const res = await API.get(
      "/api/admin/projects" + API.qs({ page: projState.page, page_size: projState.pageSize, q: projState.q })
    );
    renderProjects(res);
  } catch (err) {
    if (err.status === 401) return forceLogout();
    body.innerHTML = '<tr><td colspan="6" class="empty">加载失败：' + esc(errMessage(err)) + "</td></tr>";
  }
}

function renderProjects(res) {
  const body = document.getElementById("projBody");
  if (!res.items.length) {
    body.innerHTML = '<tr><td colspan="6" class="empty">暂无项目，点击右上角“新建项目”开始</td></tr>';
  } else {
    body.innerHTML = res.items
      .map(
        (p) =>
          `<tr>
            <td>${p.id}</td>
            <td><a href="#/projects/${p.id}">${esc(p.name)}</a>${
              p.notify_enabled ? ' <span title="已开启邮件提醒">✉</span>' : ""
            }</td>
            <td class="muted">${p.slug ? esc(p.slug) : "—"}</td>
            <td>${p.is_active ? '<span class="badge on">启用</span>' : '<span class="badge off">停用</span>'}</td>
            <td class="muted">${fmtTime(p.created_at)}</td>
            <td class="ops">
              <a class="btn secondary" href="#/projects/${p.id}">管理</a>
              <button class="ghost" data-act="edit" data-id="${p.id}">编辑</button>
              <button class="ghost danger" data-act="del" data-id="${p.id}">删除</button>
            </td>
          </tr>`
      )
      .join("");
    body.querySelectorAll("[data-act='edit']").forEach((btn) => {
      const item = res.items.find((p) => p.id === Number(btn.dataset.id));
      btn.onclick = () => projectDialog(item, loadProjects);
    });
    body.querySelectorAll("[data-act='del']").forEach((btn) => {
      const item = res.items.find((p) => p.id === Number(btn.dataset.id));
      btn.onclick = () => deleteProject(item, loadProjects);
    });
  }
  document.getElementById("projTotal").textContent =
    "共 " + res.total + " 条，第 " + res.page + " 页";
  document.getElementById("projPrev").disabled = res.page <= 1;
  document.getElementById("projNext").disabled = res.page * res.page_size >= res.total;
}

function projectDialog(project, onSaved) {
  const p = project || {};
  openModal({
    title: project ? "编辑项目" : "新建项目",
    body:
      '<div class="form-row"><label class="field-label">项目名称 <span class="req">*</span></label>' +
      `<input id="fName" value="${esc(p.name || "")}" placeholder="例如：展会客户登记" /></div>` +
      '<div class="form-row"><label class="field-label">Slug（可选，用于公开链接）</label>' +
      `<input id="fSlug" value="${esc(p.slug || "")}" placeholder="例如：expo-2026" />` +
      "<small>只能是小写字母、数字与连字符</small></div>" +
      '<div class="form-row"><label class="field-label">项目描述</label>' +
      `<textarea id="fDesc" rows="3">${esc(p.description || "")}</textarea></div>` +
      '<div class="form-row"><label class="switch-line"><label>' +
      `<input type="checkbox" id="fActive" ${p.is_active !== false ? "checked" : ""} /> 启用项目（停用后客户无法访问表单）</label></label></div>` +
      '<div style="border-top:1px solid var(--border);margin:18px 0 14px"></div>' +
      '<div class="form-row"><label class="switch-line"><label>' +
      `<input type="checkbox" id="fNotify" ${p.notify_enabled ? "checked" : ""} /> ` +
      "收到客户表单提交时发送邮件提醒</label></label>" +
      "<small>需先在「邮件提醒」页面配置好 SMTP 服务（环境变量）</small></div>" +
      '<div class="form-row"><label class="field-label">提醒收件人（多个邮箱用逗号或换行分隔）</label>' +
      `<textarea id="fNotifyEmails" rows="2" placeholder="sales@example.com, boss@example.com">${esc(
        (p.notify_emails || []).join("\n")
      )}</textarea></div>`,
    submitText: project ? "保存修改" : "创建",
    async onSubmit() {
      const payload = {
        name: document.getElementById("fName").value.trim(),
        slug: document.getElementById("fSlug").value.trim(),
        description: document.getElementById("fDesc").value,
        is_active: document.getElementById("fActive").checked,
        notify_enabled: document.getElementById("fNotify").checked,
        notify_emails: splitEmails(document.getElementById("fNotifyEmails").value),
      };
      if (!payload.name) return toast("请填写项目名称", "error"), true;
      if (payload.notify_enabled && !payload.notify_emails.length) {
        toast("已开启邮件提醒，请至少填写一个收件人邮箱", "error");
        return true;
      }
      if (project) await API.put("/api/admin/projects/" + project.id, payload);
      else await API.post("/api/admin/projects", payload);
      toast(project ? "已保存" : "项目已创建", "success");
      onSaved && onSaved();
    },
  });
}

function splitEmails(text) {
  return text
    .split(/[,，;；\n\r\s]+/)
    .map((s) => s.trim())
    .filter(Boolean);
}

async function deleteProject(project, onDone) {
  if (!confirm(`确定删除项目「${project.name}」吗？其下所有字段与客户信息将一并删除，不可恢复。`)) return;
  await API.del("/api/admin/projects/" + project.id);
  toast("项目已删除", "success");
  onDone && onDone();
}

/* ---------- 项目详情：字段 + 客户 ---------- */
let detailTab = "fields";

async function projectView(id) {
  document.getElementById("pageTitle").textContent = "项目管理";
  const view = document.getElementById("view");
  view.innerHTML = '<div class="card empty">加载中...</div>';
  let project;
  try {
    project = await API.get("/api/admin/projects/" + id);
  } catch (err) {
    if (err.status === 401) return forceLogout();
    view.innerHTML = '<div class="card empty">项目不存在或已删除，<a href="#/projects">返回列表</a></div>';
    return;
  }

  const publicUrl = location.origin + "/#/form/" + (project.slug || project.id);
  view.innerHTML =
    '<div class="card"><div class="toolbar" style="margin-bottom:0">' +
    "<div><h2 style='margin-bottom:4px'>" + esc(project.name) +
    (project.is_active ? ' <span class="badge on">启用中</span>' : ' <span class="badge off">已停用</span>') +
    (project.notify_enabled
      ? ` <span class="badge type" title="${esc((project.notify_emails || []).join(", "))}">✉ 邮件提醒 · ${
          (project.notify_emails || []).length
        } 个收件人</span>`
      : "") +
    "</h2>" +
    '<div class="muted">客户填报链接：<a href="' + esc(publicUrl) + '" target="_blank">' + esc(publicUrl) + "</a></div></div>" +
    '<div class="left"><button class="secondary" id="copyLink">复制链接</button>' +
    '<button class="secondary" id="editProj">编辑项目</button>' +
    '<button class="danger" id="delProj">删除项目</button></div></div></div>' +
    '<div class="tabs">' +
    '<button id="tabFields">表单字段</button>' +
    '<button id="tabCustomers">客户信息</button></div>' +
    '<div id="tabBody"></div>';

  document.getElementById("copyLink").onclick = () => {
    navigator.clipboard.writeText(publicUrl).then(
      () => toast("填报链接已复制", "success"),
      () => toast("复制失败，请手动选择链接复制", "error")
    );
  };
  document.getElementById("editProj").onclick = () =>
    projectDialog(project, () => projectView(id));
  document.getElementById("delProj").onclick = async () => {
    await deleteProject(project);
    location.hash = "#/projects";
  };
  document.getElementById("tabFields").onclick = () => {
    detailTab = "fields";
    renderTab(id);
  };
  document.getElementById("tabCustomers").onclick = () => {
    detailTab = "customers";
    renderTab(id);
  };
  renderTab(id);
}

function renderTab(id) {
  document.getElementById("tabFields").classList.toggle("active", detailTab === "fields");
  document.getElementById("tabCustomers").classList.toggle("active", detailTab === "customers");
  if (detailTab === "fields") fieldsTab(id);
  else customersTab(id);
}

/* ----- 字段管理 ----- */
async function fieldsTab(id) {
  const box = document.getElementById("tabBody");
  box.innerHTML = '<div class="card empty">加载中...</div>';
  let fields;
  try {
    fields = await API.get(`/api/admin/projects/${id}/fields`);
  } catch (err) {
    box.innerHTML = '<div class="card empty">加载失败：' + esc(errMessage(err)) + "</div>";
    return;
  }
  box.innerHTML =
    '<div class="toolbar"><div class="left muted">字段顺序、类型与选项均为动态配置，前端表单实时按此配置生成</div>' +
    '<button id="addField">+ 新增字段</button></div>' +
    '<div class="card"><div class="table-wrap"><table><thead><tr>' +
    "<th>排序</th><th>字段名称</th><th>键名</th><th>类型</th><th>必填</th><th>选项</th><th>状态</th><th>操作</th>" +
    "</tr></thead><tbody id='fieldBody'></tbody></table></div></div>";
  document.getElementById("addField").onclick = () => fieldDialog(id, null, fields, () => fieldsTab(id));

  const body = document.getElementById("fieldBody");
  if (!fields.length) {
    body.innerHTML = '<tr><td colspan="8" class="empty">还没有字段，点击“新增字段”设计客户表单</td></tr>';
    return;
  }
  body.innerHTML = fields
    .map(
      (f) =>
        `<tr>
          <td>${f.sort_order}</td>
          <td>${esc(f.label)}</td>
          <td><code>${esc(f.key)}</code></td>
          <td><span class="badge type">${TYPE_LABELS[f.type] || esc(f.type)}</span></td>
          <td>${f.required ? '<span class="req">是</span>' : "否"}</td>
          <td class="muted">${isChoiceType(f.type) ? esc((f.options || []).join("、")) : "—"}</td>
          <td>${f.is_active ? '<span class="badge on">启用</span>' : '<span class="badge off">停用</span>'}</td>
          <td class="ops">
            <button class="ghost" data-act="edit" data-id="${f.id}">编辑</button>
            <button class="ghost danger" data-act="del" data-id="${f.id}">删除</button>
          </td>
        </tr>`
    )
    .join("");
  body.querySelectorAll("[data-act='edit']").forEach((btn) => {
    const item = fields.find((f) => f.id === Number(btn.dataset.id));
    btn.onclick = () => fieldDialog(id, item, fields, () => fieldsTab(id));
  });
  body.querySelectorAll("[data-act='del']").forEach((btn) => {
    const item = fields.find((f) => f.id === Number(btn.dataset.id));
    btn.onclick = async () => {
      if (!confirm(`确定删除字段「${item.label}」吗？历史客户数据中该键会保留但不再展示为列。`)) return;
      await API.del("/api/admin/fields/" + item.id);
      toast("字段已删除", "success");
      fieldsTab(id);
    };
  });
}

function fieldDialog(projectId, field, allFields, onSaved) {
  const f = field || {};
  const typeOptions = Object.keys(TYPE_LABELS)
    .map((t) => `<option value="${t}" ${f.type === t ? "selected" : ""}>${TYPE_LABELS[t]}</option>`)
    .join("");
  const rules = f.validation || {};

  const mask = openModal({
    title: field ? "编辑字段" : "新增字段",
    wide: true,
    body:
      '<div class="grid2">' +
      '<div class="form-row"><label class="field-label">字段名称 <span class="req">*</span></label>' +
      `<input id="ffLabel" value="${esc(f.label || "")}" placeholder="客户看到的名称，如：姓名" /></div>` +
      '<div class="form-row"><label class="field-label">键名 key <span class="req">*</span></label>' +
      `<input id="ffKey" value="${esc(f.key || "")}" placeholder="英文标识，如：name" />` +
      "<small>提交数据 JSON 中的键，字母/数字/下划线</small></div>" +
      '<div class="form-row"><label class="field-label">字段类型</label>' +
      `<select id="ffType">${typeOptions}</select></div>` +
      '<div class="form-row"><label class="field-label">排序值</label>' +
      `<input type="number" id="ffSort" value="${f.sort_order !== undefined ? f.sort_order : 0}" /></div>` +
      "</div>" +
      '<div class="form-row" id="optRow" style="display:none"><label class="field-label">选项（每行一个）</label>' +
      `<textarea id="ffOptions" rows="3" placeholder="选项A&#10;选项B">${esc((f.options || []).join("\n"))}</textarea></div>` +
      '<div class="grid2">' +
      '<div class="form-row" id="phRow"><label class="field-label">占位提示</label>' +
      `<input id="ffPlaceholder" value="${esc(f.placeholder || "")}" /></div>` +
      '<div class="form-row"><label class="field-label">字段说明（可选）</label>' +
      `<input id="ffDesc" value="${esc(f.description || "")}" /></div></div>` +
      '<div class="grid2" id="numRules" style="display:none">' +
      '<div class="form-row"><label class="field-label">最小值</label>' +
      `<input type="number" id="ffMin" value="${rules.min !== undefined && rules.min !== null ? esc(rules.min) : ""}" /></div>` +
      '<div class="form-row"><label class="field-label">最大值</label>' +
      `<input type="number" id="ffMax" value="${rules.max !== undefined && rules.max !== null ? esc(rules.max) : ""}" /></div></div>` +
      '<div class="grid2" id="strRules" style="display:none">' +
      '<div class="form-row"><label class="field-label">最小长度</label>' +
      `<input type="number" id="ffMinLen" value="${rules.min_length !== undefined && rules.min_length !== null ? esc(rules.min_length) : ""}" /></div>` +
      '<div class="form-row"><label class="field-label">最大长度</label>' +
      `<input type="number" id="ffMaxLen" value="${rules.max_length !== undefined && rules.max_length !== null ? esc(rules.max_length) : ""}" /></div></div>` +
      '<div class="form-row" id="patRow" style="display:none"><label class="field-label">正则校验 pattern（可选）</label>' +
      `<input id="ffPattern" value="${esc(rules.pattern || "")}" placeholder="如 ^1[3-9]\\d{9}$" /></div>` +
      '<div class="grid2">' +
      '<div class="form-row"><label class="switch-line"><label>' +
      `<input type="checkbox" id="ffRequired" ${f.required ? "checked" : ""} /> 必填字段</label></label></div>` +
      '<div class="form-row"><label class="switch-line"><label>' +
      `<input type="checkbox" id="ffActive" ${f.is_active !== false ? "checked" : ""} /> 启用字段</label></label></div></div>`,
    submitText: field ? "保存修改" : "创建字段",
    async onSubmit() {
      const type = document.getElementById("ffType").value;
      const payload = {
        label: document.getElementById("ffLabel").value.trim(),
        key: document.getElementById("ffKey").value.trim(),
        type,
        sort_order: Number(document.getElementById("ffSort").value || 0),
        placeholder: document.getElementById("ffPlaceholder").value,
        description: document.getElementById("ffDesc").value,
        required: document.getElementById("ffRequired").checked,
        is_active: document.getElementById("ffActive").checked,
        options: null,
        validation: null,
      };
      if (!payload.label || !payload.key) {
        toast("字段名称和键名必填", "error");
        return true;
      }
      if (!field && allFields.some((x) => x.key === payload.key)) {
        toast("键名 " + payload.key + " 已存在", "error");
        return true;
      }
      if (isChoiceType(type)) {
        payload.options = document.getElementById("ffOptions").value
          .split("\n").map((s) => s.trim()).filter(Boolean);
        if (!payload.options.length) {
          toast("选项类型至少配置一个选项", "error");
          return true;
        }
      }
      const validation = {};
      if (type === "number") {
        const min = document.getElementById("ffMin").value;
        const max = document.getElementById("ffMax").value;
        if (min !== "") validation.min = Number(min);
        if (max !== "") validation.max = Number(max);
      } else if (["text", "textarea", "email", "phone"].includes(type)) {
        const minLen = document.getElementById("ffMinLen").value;
        const maxLen = document.getElementById("ffMaxLen").value;
        const pattern = document.getElementById("ffPattern").value.trim();
        if (minLen !== "") validation.min_length = Number(minLen);
        if (maxLen !== "") validation.max_length = Number(maxLen);
        if (pattern) validation.pattern = pattern;
      }
      if (Object.keys(validation).length) payload.validation = validation;

      if (field) await API.put("/api/admin/fields/" + field.id, payload);
      else await API.post(`/api/admin/projects/${projectId}/fields`, payload);
      toast(field ? "字段已保存" : "字段已创建", "success");
      onSaved && onSaved();
    },
  });

  function syncType() {
    const type = document.getElementById("ffType").value;
    document.getElementById("optRow").style.display = isChoiceType(type) ? "" : "none";
    document.getElementById("numRules").style.display = type === "number" ? "" : "none";
    document.getElementById("strRules").style.display =
      ["text", "textarea", "email", "phone"].includes(type) ? "" : "none";
    document.getElementById("patRow").style.display =
      ["text", "textarea", "email", "phone"].includes(type) ? "" : "none";
  }
  document.getElementById("ffType").addEventListener("change", syncType);
  syncType();
}

/* ----- 客户信息 ----- */
const custState = { page: 1, pageSize: 10, q: "" };

function customersTab(projectId) {
  const box = document.getElementById("tabBody");
  box.innerHTML =
    '<div class="toolbar"><div class="left">' +
    '<input id="custSearch" style="width:240px" placeholder="在提交内容中关键字搜索" />' +
    '<button class="secondary" id="custSearchBtn">查询</button></div>' +
    '<button id="custCreate">+ 手动新增</button></div>' +
    '<div class="card"><div class="table-wrap" id="custTableWrap">加载中...</div>' +
    '<div class="pager"><span class="muted" id="custTotal"></span>' +
    '<button class="secondary" id="custPrev">上一页</button>' +
    '<button class="secondary" id="custNext">下一页</button></div></div>';
  document.getElementById("custSearch").value = custState.q;
  document.getElementById("custSearchBtn").onclick = () => {
    custState.q = document.getElementById("custSearch").value.trim();
    custState.page = 1;
    loadCustomers(projectId);
  };
  document.getElementById("custSearch").addEventListener("keydown", (e) => {
    if (e.key === "Enter") document.getElementById("custSearchBtn").click();
  });
  document.getElementById("custCreate").onclick = () => customerDialog(projectId, null);
  document.getElementById("custPrev").onclick = () => {
    if (custState.page > 1) { custState.page--; loadCustomers(projectId); }
  };
  document.getElementById("custNext").onclick = () => {
    custState.page++;
    loadCustomers(projectId);
  };
  loadCustomers(projectId);
}

async function loadCustomers(projectId) {
  const wrap = document.getElementById("custTableWrap");
  wrap.innerHTML = "加载中...";
  let fields, res;
  try {
    const allFields = await API.get(`/api/admin/projects/${projectId}/fields`);
    fields = allFields.filter((f) => f.is_active);
    res = await API.get(
      `/api/admin/projects/${projectId}/customers` +
        API.qs({ page: custState.page, page_size: custState.pageSize, q: custState.q })
    );
  } catch (err) {
    wrap.innerHTML = "加载失败：" + esc(errMessage(err));
    return;
  }

  if (!res.items.length) {
    wrap.innerHTML = '<div class="empty">暂无客户信息</div>';
  } else {
    const cols = fields.length
      ? fields.map((f) => "<th>" + esc(f.label) + "</th>").join("")
      : "<th>数据</th>";
    wrap.innerHTML =
      "<table><thead><tr><th>ID</th>" + cols + "<th>提交时间</th><th>操作</th></tr></thead><tbody></tbody></table>";
    const tbody = wrap.querySelector("tbody");
    tbody.innerHTML = res.items
      .map((c) => {
        const cells = fields.length
          ? fields.map((f) => "<td>" + formatCell(c.data[f.key]) + "</td>").join("")
          : "<td>" + esc(JSON.stringify(c.data)) + "</td>";
        return (
          `<tr><td>${c.id}</td>${cells}<td class="muted">${fmtTime(c.created_at)}</td>` +
          `<td class="ops"><button class="ghost" data-act="edit" data-id="${c.id}">编辑</button>` +
          `<button class="ghost danger" data-act="del" data-id="${c.id}">删除</button></td></tr>`
        );
      })
      .join("");
    tbody.querySelectorAll("[data-act='edit']").forEach((btn) => {
      const item = res.items.find((c) => c.id === Number(btn.dataset.id));
      btn.onclick = () => customerDialog(projectId, item, fields);
    });
    tbody.querySelectorAll("[data-act='del']").forEach((btn) => {
      const item = res.items.find((c) => c.id === Number(btn.dataset.id));
      btn.onclick = async () => {
        if (!confirm("确定删除该条客户信息吗？")) return;
        await API.del("/api/admin/customers/" + item.id);
        toast("已删除", "success");
        loadCustomers(projectId);
      };
    });
  }
  document.getElementById("custTotal").textContent = "共 " + res.total + " 条，第 " + res.page + " 页";
  document.getElementById("custPrev").disabled = res.page <= 1;
  document.getElementById("custNext").disabled = res.page * res.page_size >= res.total;
}

async function customerDialog(projectId, customer) {
  let fields;
  try {
    const all = await API.get(`/api/admin/projects/${projectId}/fields`);
    fields = all.filter((f) => f.is_active);
  } catch (err) {
    return toast(errMessage(err), "error");
  }
  if (!fields.length) return toast("请先为项目配置至少一个启用的字段", "error");

  const values = customer ? customer.data : {};
  const mask = openModal({
    title: customer ? "编辑客户信息（#" + customer.id + "）" : "新增客户信息",
    wide: true,
    body: '<div id="custFormBody">' + renderDynamicForm(fields, values) + "</div>",
    submitText: customer ? "保存修改" : "提交",
    async onSubmit() {
      const collected = collectDynamicForm(mask.querySelector("#custFormBody"), fields);
      if (!collected.valid) {
        toast("请检查必填项", "error");
        return true;
      }
      try {
        if (customer)
          await API.put("/api/admin/customers/" + customer.id, { data: collected.data });
        else
          await API.post(`/api/admin/projects/${projectId}/customers`, { data: collected.data });
        toast(customer ? "已保存" : "客户信息已创建", "success");
        loadCustomers(projectId);
      } catch (err) {
        if (err.status === 422) showFieldErrors(mask.querySelector("#custFormBody"), err.detail);
        throw err;
      }
    },
  });
}

/* ---------- 邮件提醒 ---------- */
function emailView() {
  document.getElementById("pageTitle").textContent = "邮件提醒";
  const view = document.getElementById("view");
  view.innerHTML =
    '<div class="card"><h2>工作方式</h2>' +
    "<ul>" +
    "<li><b>第一步（服务器配置）：</b>SMTP 服务器信息通过环境变量配置（<code>SMTP_HOST / SMTP_PORT / SMTP_USER / SMTP_PASSWORD / SMTP_SECURITY</code>），" +
    "修改后重启服务生效。凭据不会出现在页面或数据库中。</li>" +
    "<li><b>第二步（按项目开启）：</b>在「项目管理 → 编辑项目」中勾选“收到客户表单提交时发送邮件提醒”，并填写收件人邮箱。</li>" +
    "<li>客户每次成功提交表单后，系统会<b>异步</b>向该项目的收件人发送一封包含全部填写内容的邮件；邮件服务故障不影响客户提交。</li>" +
    "</ul></div>" +
    '<div class="card" id="mailStatus"><h2>SMTP 服务状态</h2><div class="empty">加载中...</div></div>' +
    '<div class="card"><h2>发送测试邮件</h2>' +
    '<div class="toolbar" style="margin-bottom:0">' +
    '<input id="testEmail" style="max-width:320px" placeholder="输入接收测试邮件的邮箱" />' +
    '<button id="btnTestEmail">发送测试邮件</button></div></div>';

  document.getElementById("btnTestEmail").onclick = async () => {
    const email = document.getElementById("testEmail").value.trim();
    if (!email) return toast("请输入邮箱地址", "error");
    const btn = document.getElementById("btnTestEmail");
    btn.disabled = true;
    btn.textContent = "发送中...";
    try {
      const res = await API.post("/api/admin/settings/email/test", { email });
      toast(res.message || "测试邮件已发送", "success");
    } catch (err) {
      toast(errMessage(err, "发送失败"), "error");
    } finally {
      btn.disabled = false;
      btn.textContent = "发送测试邮件";
    }
  };

  loadMailStatus();
}

async function loadMailStatus() {
  const box = document.getElementById("mailStatus");
  let s;
  try {
    s = await API.get("/api/admin/settings/email");
  } catch (err) {
    if (err.status === 401) return forceLogout();
    box.innerHTML = "<h2>SMTP 服务状态</h2>" +
      '<div class="empty">加载失败：' + esc(errMessage(err)) + "</div>";
    return;
  }

  const statusBadge = s.smtp_configured
    ? '<span class="badge on">已配置</span>'
    : '<span class="badge off">未配置</span>';
  const rows = [
    ["状态", statusBadge],
    ["SMTP 服务器", esc(s.smtp_host || "—") + (s.smtp_host ? ":" + esc(String(s.smtp_port)) : "")],
    ["加密方式", esc(s.smtp_security || "—")],
    ["登录账号", esc(s.smtp_user || "—")],
    ["发件人", esc(s.mail_from || "—")],
  ]
    .map(([k, v]) => `<tr><th style="width:130px">${k}</th><td>${v}</td></tr>`)
    .join("");

  const enabledList = s.enabled_projects.length
    ? s.enabled_projects
        .map(
          (p) =>
            `<tr><td><a href="#/projects/${p.id}">${esc(p.name)}</a></td>` +
            `<td>${esc((p.notify_emails || []).join("、"))}</td></tr>`
        )
        .join("")
    : '<tr><td colspan="2" class="empty">暂无开启提醒的项目</td></tr>';

  box.innerHTML =
    "<h2>SMTP 服务状态</h2>" +
    (s.smtp_configured
      ? ""
      : '<p class="muted">未检测到 SMTP 配置。请在服务器的 .env（或 docker compose 环境变量）中设置后重启服务，可参考 .env.example 中的常见服务商参数。</p>') +
    '<div class="table-wrap"><table>' + rows + "</table></div>" +
    '<h2 style="margin-top:20px">已开启提醒的项目</h2>' +
    '<div class="table-wrap"><table><thead><tr><th>项目</th><th>收件人</th></tr></thead><tbody>' +
    enabledList +
    "</tbody></table></div>";
}

/* ---------- 备份与恢复 ---------- */
function backupView() {
  document.getElementById("pageTitle").textContent = "备份与恢复";
  const view = document.getElementById("view");
  view.innerHTML =
    '<div class="card"><h2>工作方式</h2>' +
    "<p>SQLite 数据库文件运行在服务器容器的数据卷中（容器路径 <code>/data/cims.db</code>）。</p>" +
    "<ul>" +
    "<li><b>备份到本地：</b>点击下方按钮，系统生成一致性快照并通过浏览器下载 <code>.db</code> 文件，请妥善保存到本地磁盘。</li>" +
    "<li><b>从本地恢复：</b>选择此前下载的 <code>.db</code> 备份文件上传，系统校验通过后会热替换当前数据库（当前数据将被覆盖，请谨慎操作）。</li>" +
    "</ul></div>" +
    '<div class="card"><h2>数据库备份</h2>' +
    '<button id="btnBackup">⤓ 下载数据库备份 (.db)</button></div>' +
    '<div class="card"><h2>从本地恢复</h2>' +
    '<div class="form-row"><input type="file" id="restoreFile" accept=".db,.sqlite,.sqlite3,application/octet-stream" /></div>' +
    '<button class="danger" id="btnRestore">上传并恢复</button></div>';

  document.getElementById("btnBackup").onclick = async () => {
    try {
      await API.download("/api/admin/database/backup");
      toast("备份已开始下载", "success");
    } catch (err) {
      toast(errMessage(err, "备份失败"), "error");
    }
  };
  document.getElementById("btnRestore").onclick = async () => {
    const input = document.getElementById("restoreFile");
    const file = input.files && input.files[0];
    if (!file) return toast("请先选择备份文件", "error");
    if (!confirm("恢复将用备份文件覆盖当前全部数据，确定继续吗？")) return;
    const fd = new FormData();
    fd.append("file", file);
    try {
      const res = await API.upload("/api/admin/database/restore", fd);
      toast(res.message || "恢复成功", "success");
      input.value = "";
    } catch (err) {
      toast(errMessage(err, "恢复失败"), "error");
    }
  };
}

/* ---------- 接口契约 ---------- */
function contractView() {
  document.getElementById("pageTitle").textContent = "接口契约";
  const view = document.getElementById("view");
  const base = location.origin;
  view.innerHTML =
    '<div class="card"><h2>OpenAPI 契约</h2>' +
    '<p class="muted">FastAPI 自动生成，接口变更后契约同步更新，可直接用于生成任意语言/框架的客户端。</p>' +
    '<div class="left" style="display:flex;gap:10px;flex-wrap:wrap">' +
    '<a class="btn" href="/docs" target="_blank">Swagger UI</a>' +
    '<a class="btn secondary" href="/redoc" target="_blank">Redoc</a>' +
    '<a class="btn secondary" href="/openapi.json" target="_blank" download="openapi.json">下载 openapi.json</a>' +
    "</div></div>" +
    '<div class="card"><h2>鉴权说明</h2>' +
    "<p><b>后台接口</b> <code>/api/admin/*</code>：先调用 <code>POST /api/auth/login</code> 用账号密码换取 JWT，" +
    "之后请求头携带 <code>Authorization: Bearer &lt;token&gt;</code>。</p>" +
    "<p><b>集成接口</b> <code>/api/v1/*</code>：供替换/独立部署的前端使用，请求头携带：</p>" +
    '<div class="code-block">X-API-Token: &lt;API_TOKEN&gt;</div>' +
    "<p>Token 由服务器环境变量 <code>API_TOKEN</code> 配置，修改环境变量并重启服务即可更换，无需操作界面。</p>" +
    "<p><b>公开填报</b> <code>/api/public/*</code>：无需鉴权。</p></div>" +
    '<div class="card"><h2>快速调用示例</h2>' +
    '<div class="code-block"># 获取项目字段配置\n' +
    `curl -H "X-API-Token: $API_TOKEN" ${base}/api/v1/projects/1/fields\n\n` +
    "# 提交一条客户信息\n" +
    `curl -X POST ${base}/api/v1/projects/1/customers \\\n` +
    '  -H "X-API-Token: $API_TOKEN" -H "Content-Type: application/json" \\\n' +
    '  -d \'{"data":{"name":"张三","phone":"13800000000"}}\'</div></div>';
}

/* ---------- 客户公开填报 ---------- */
async function renderPublicProjectList() {
  appEl.innerHTML =
    '<div class="public-wrap"><div class="card"><h1>客户填报</h1>' +
    '<div id="plist" class="muted">加载中...</div></div></div>';
  try {
    const rows = await API.get("/api/public/projects");
    const box = document.getElementById("plist");
    if (!rows.length) {
      box.className = "empty";
      box.textContent = "当前没有可填报的项目";
      return;
    }
    box.innerHTML = rows
      .map(
        (p) =>
          `<div style="padding:14px 0;border-bottom:1px solid var(--border)">` +
          `<a href="#/form/${p.slug || p.id}" style="font-size:15px;font-weight:600">${esc(p.name)}</a>` +
          (p.description ? `<div class="muted" style="margin-top:4px">${esc(p.description)}</div>` : "") +
          `</div>`
      )
      .join("");
  } catch (err) {
    document.getElementById("plist").textContent = "加载失败：" + errMessage(err);
  }
}

async function renderPublicForm(key) {
  appEl.innerHTML =
    '<div class="public-wrap"><div class="card" id="formCard">加载中...</div>' +
    '<div style="text-align:center;margin-top:14px"><a href="#/login">后台登录</a></div></div>';
  let form;
  try {
    form = await API.get("/api/public/projects/" + encodeURIComponent(key) + "/form");
  } catch (err) {
    document.getElementById("formCard").innerHTML =
      '<div class="empty">表单不存在或项目已停用</div>';
    return;
  }

  const card = document.getElementById("formCard");
  if (!form.fields.length) {
    card.innerHTML =
      `<h1>${esc(form.project.name)}</h1><div class="empty">该项目暂未配置任何字段</div>`;
    return;
  }
  card.innerHTML =
    `<h1>${esc(form.project.name)}</h1>` +
    (form.project.description ? `<p class="muted">${esc(form.project.description)}</p>` : "") +
    '<form id="publicForm">' +
    renderDynamicForm(form.fields, {}) +
    '<button type="submit" style="width:100%;padding:11px">提交</button>' +
    "</form>";

  document.getElementById("publicForm").addEventListener("submit", async (e) => {
    e.preventDefault();
    const formEl = e.target;
    const collected = collectDynamicForm(formEl, form.fields);
    if (!collected.valid) return toast("请完善必填项", "error");
    const btn = formEl.querySelector("button");
    btn.disabled = true;
    btn.textContent = "提交中...";
    try {
      await API.post(
        "/api/public/projects/" + encodeURIComponent(key) + "/submissions",
        { data: collected.data }
      );
      card.innerHTML =
        '<div class="success-box"><div class="icon">✅</div>' +
        "<h2>提交成功</h2><p class='muted'>感谢您的填写，信息已保存。</p>" +
        '<button id="again" style="margin-top:10px">再填一份</button></div>';
      document.getElementById("again").onclick = () => renderPublicForm(key);
    } catch (err) {
      if (err.status === 422) showFieldErrors(formEl, err.detail);
      toast(errMessage(err, "提交失败"), "error");
      btn.disabled = false;
      btn.textContent = "提交";
    }
  });
}

/* ---------- 工具 ---------- */
function fmtTime(t) {
  if (!t) return "—";
  const d = new Date(t);
  if (isNaN(d.getTime())) return esc(String(t));
  const pad = (n) => String(n).padStart(2, "0");
  return `${d.getFullYear()}-${pad(d.getMonth() + 1)}-${pad(d.getDate())} ${pad(d.getHours())}:${pad(d.getMinutes())}`;
}

function forceLogout() {
  API.logout();
  toast("登录已过期，请重新登录", "error");
  location.hash = "#/login";
}

/* 全局捕获后台接口 401 */
const origFetch = window.fetch;
window.fetch = function (...args) {
  return origFetch.apply(this, args).then((res) => {
    if (res.status === 401) {
      const url = typeof args[0] === "string" ? args[0] : args[0].url;
      if (url && url.indexOf("/api/admin/") >= 0 && API.isAuthed() &&
          !location.hash.startsWith("#/form") && location.hash !== "#/login") {
        setTimeout(forceLogout, 300);
      }
    }
    return res;
  });
};

/* 启动 */
navigate();
