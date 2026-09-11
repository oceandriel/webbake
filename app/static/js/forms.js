/* 动态表单引擎：根据后端返回的字段配置渲染表单并收集/校验数据。
   后端字段不写死，前端同样不写死任何业务字段。 */

function esc(value) {
  return String(value === null || value === undefined ? "" : value).replace(
    /[&<>"']/g,
    (c) =>
      ({
        "&": "&amp;",
        "<": "&lt;",
        ">": "&gt;",
        '"': "&quot;",
        "'": "&#39;",
      }[c])
  );
}

const TYPE_LABELS = {
  text: "单行文本",
  textarea: "多行文本",
  number: "数字",
  email: "邮箱",
  phone: "电话",
  date: "日期",
  datetime: "日期时间",
  select: "下拉单选",
  radio: "单选按钮",
  multiselect: "多选",
  boolean: "是 / 否",
};

const CHOICE_TYPES = ["select", "radio", "multiselect"];

function isChoiceType(type) {
  return CHOICE_TYPES.indexOf(type) >= 0;
}

function renderDynamicForm(fields, values) {
  values = values || {};
  return fields
    .map((f) => {
      const val = values[f.key];
      const star = f.required ? ' <span class="req">*</span>' : "";
      const desc = f.description ? `<small>${esc(f.description)}</small>` : "";
      return (
        `<div class="dy-field" data-key="${esc(f.key)}" data-type="${esc(f.type)}">` +
        `<label>${esc(f.label)}${star}</label>` +
        renderInput(f, val) +
        desc +
        `<div class="field-error"></div>` +
        `</div>`
      );
    })
    .join("");
}

function renderInput(f, val) {
  const name = "dyn_" + f.key;
  const ph = f.placeholder ? ` placeholder="${esc(f.placeholder)}"` : "";
  const rules = f.validation || {};

  switch (f.type) {
    case "textarea":
      return `<textarea name="${name}" rows="4"${ph}>${esc(val)}</textarea>`;

    case "number": {
      const min = rules.min !== undefined && rules.min !== null ? ` min="${esc(rules.min)}"` : "";
      const max = rules.max !== undefined && rules.max !== null ? ` max="${esc(rules.max)}"` : "";
      return `<input type="number" name="${name}" value="${esc(val)}"${ph}${min}${max} />`;
    }

    case "email":
      return `<input type="email" name="${name}" value="${esc(val)}"${ph} />`;
    case "phone":
      return `<input type="tel" name="${name}" value="${esc(val)}"${ph} />`;
    case "date":
      return `<input type="date" name="${name}" value="${esc(val)}"${ph} />`;
    case "datetime":
      return `<input type="datetime-local" name="${name}" step="1" value="${esc(val)}"${ph} />`;

    case "select":
      return (
        `<select name="${name}">` +
        `<option value="">${esc(f.placeholder || "请选择")}</option>` +
        (f.options || [])
          .map(
            (o) =>
              `<option value="${esc(o)}"${o === val ? " selected" : ""}>${esc(o)}</option>`
          )
          .join("") +
        `</select>`
      );

    case "radio":
      return (
        `<div class="radio-group">` +
        (f.options || [])
          .map(
            (o) =>
              `<label><input type="radio" name="${name}" value="${esc(o)}"${
                o === val ? " checked" : ""
              } /> ${esc(o)}</label>`
          )
          .join("") +
        `</div>`
      );

    case "multiselect": {
      const selected = Array.isArray(val) ? val : [];
      return (
        `<div class="checkbox-group">` +
        (f.options || [])
          .map(
            (o) =>
              `<label><input type="checkbox" name="${name}" value="${esc(o)}"${
                selected.indexOf(o) >= 0 ? " checked" : ""
              } /> ${esc(o)}</label>`
          )
          .join("") +
        `</div>`
      );
    }

    case "boolean":
      return `<div class="switch-line"><label><input type="checkbox" name="${name}"${
        val ? " checked" : ""
      } /> ${esc(f.placeholder || "勾选表示“是”")}</label></div>`;

    default:
      return `<input type="text" name="${name}" value="${esc(val)}"${ph} />`;
  }
}

/* 从容器中收集动态表单数据。
   返回 { data, valid }，valid=false 时错误已渲染到对应字段下方。 */
function collectDynamicForm(container, fields) {
  const data = {};
  let valid = true;

  fields.forEach((f) => {
    const wrap = container.querySelector('.dy-field[data-key="' + cssEscape(f.key) + '"]');
    if (!wrap) return;
    wrap.classList.remove("invalid");
    const errBox = wrap.querySelector(".field-error");
    if (errBox) errBox.textContent = "";

    const name = "dyn_" + f.key;
    let value;

    if (f.type === "multiselect") {
      value = Array.prototype.slice
        .call(container.querySelectorAll('input[name="' + name + '"]:checked'))
        .map((el) => el.value);
    } else if (f.type === "boolean") {
      value = !!container.querySelector('input[name="' + name + '"]').checked;
    } else if (f.type === "radio") {
      const checked = container.querySelector('input[name="' + name + '"]:checked');
      value = checked ? checked.value : "";
    } else {
      value = container.querySelector('[' + 'name="' + name + '"]').value;
      if (f.type !== "textarea" && f.type !== "number") value = value.trim();
    }

    const empty =
      value === "" ||
      value === null ||
      value === undefined ||
      (Array.isArray(value) && value.length === 0);

    if (empty) {
      if (f.required) {
        valid = false;
        wrap.classList.add("invalid");
        if (errBox) errBox.textContent = "该字段为必填项";
      }
      return;
    }
    data[f.key] = value;
  });

  return { data, valid };
}

/* 将后端 422 返回的 {字段key: 消息} 显示到表单上。 */
function showFieldErrors(container, errors) {
  if (!errors || typeof errors !== "object") return;
  Object.keys(errors).forEach((key) => {
    const wrap = container.querySelector('.dy-field[data-key="' + cssEscape(key) + '"]');
    if (wrap) {
      wrap.classList.add("invalid");
      const errBox = wrap.querySelector(".field-error");
      if (errBox) errBox.textContent = String(errors[key]);
    }
  });
}

function cssEscape(value) {
  return String(value).replace(/(["\\])/g, "\\$1");
}

/* 表格单元格展示客户数据。 */
function formatCell(value) {
  if (value === null || value === undefined) return '<span class="muted">—</span>';
  if (Array.isArray(value)) return esc(value.join("、"));
  if (typeof value === "boolean") return value ? "是" : "否";
  if (typeof value === "object") return esc(JSON.stringify(value));
  return esc(value);
}
