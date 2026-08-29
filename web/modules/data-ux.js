export function initializeDataUX(root = document) {
  enhance(root);
  new MutationObserver((records) => records.forEach((record) => record.addedNodes.forEach((node) => {
    if (node.nodeType === Node.ELEMENT_NODE) enhance(node);
  }))).observe(root.body || root, { childList: true, subtree: true });
  root.addEventListener("change", (event) => renderFilterChips(event.target.closest(".filter-toolbar")));
  root.addEventListener("input", (event) => renderFilterChips(event.target.closest(".filter-toolbar")));
}

function enhance(scope) {
  const tables = scope.matches?.("table.report-table") ? [scope] : [...scope.querySelectorAll?.("table.report-table") || []];
  tables.forEach(enhanceTable);
  const toolbars = scope.matches?.(".filter-toolbar") ? [scope] : [...scope.querySelectorAll?.(".filter-toolbar") || []];
  toolbars.forEach(renderFilterChips);
}

function enhanceTable(table) {
  if (table.dataset.dataUx === "true") return;
  table.dataset.dataUx = "true";
  const headers = [...table.querySelectorAll("thead th")];
  headers.forEach((header, index) => {
    if (header.colSpan > 1 || /aç(ão|ões)/i.test(header.textContent)) return;
    header.classList.add("sortable-column");
    header.tabIndex = 0;
    header.setAttribute("aria-sort", "none");
    const sort = () => sortTable(table, index, header, headers);
    header.addEventListener("click", sort);
    header.addEventListener("keydown", (event) => {
      if (["Enter", " "].includes(event.key)) { event.preventDefault(); sort(); }
    });
  });
  const wrapper = table.closest(".report-table-wrap");
  if (wrapper && !wrapper.previousElementSibling?.classList.contains("data-table-count")) {
    const count = document.createElement("p");
    count.className = "data-table-count";
    count.textContent = `${table.tBodies[0]?.rows.length || 0} item(ns) exibido(s)`;
    wrapper.before(count);
  }
}

function sortTable(table, index, header, headers) {
  const ascending = header.getAttribute("aria-sort") !== "ascending";
  headers.forEach((item) => item.setAttribute("aria-sort", "none"));
  header.setAttribute("aria-sort", ascending ? "ascending" : "descending");
  const body = table.tBodies[0];
  if (!body) return;
  [...body.rows].sort((left, right) => compare(cellValue(left, index), cellValue(right, index)) * (ascending ? 1 : -1))
    .forEach((row) => body.append(row));
}

function cellValue(row, index) { return row.cells[index]?.textContent.trim() || ""; }
function compare(left, right) {
  const number = (value) => Number(value.replace(/[^0-9,.-]/g, "").replace(/\./g, "").replace(",", "."));
  const a = number(left); const b = number(right);
  return Number.isFinite(a) && Number.isFinite(b) ? a - b : left.localeCompare(right, "pt-BR", { numeric: true });
}

function renderFilterChips(toolbar) {
  if (!toolbar) return;
  let container = toolbar.nextElementSibling;
  if (!container?.classList.contains("active-filter-chips")) {
    container = document.createElement("div");
    container.className = "active-filter-chips";
    toolbar.after(container);
  }
  const controls = [...toolbar.querySelectorAll("input:not([type='hidden']), select")];
  const active = controls.filter((control) => control.value && control.type !== "submit");
  container.replaceChildren(...active.map((control) => {
    const chip = document.createElement("button");
    chip.type = "button";
    chip.className = "active-filter-chip";
    const label = control.closest("label")?.childNodes[0]?.textContent.trim() || "Filtro";
    const value = control.selectedOptions?.[0]?.textContent || control.value;
    chip.textContent = `${label}: ${value} ×`;
    chip.addEventListener("click", () => {
      control.value = "";
      control.dispatchEvent(new Event(control.tagName === "SELECT" ? "change" : "input", { bubbles: true }));
    });
    return chip;
  }));
  container.hidden = !active.length;
}
