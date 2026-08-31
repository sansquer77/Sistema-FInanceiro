const DEFAULT_THRESHOLD = 200;
const DEFAULT_OVERSCAN = 5;

export function renderVirtualList(container, items, { rowHeight, renderItem, overscan = DEFAULT_OVERSCAN, threshold = DEFAULT_THRESHOLD, viewportHeight = 560 } = {}) {
  if (!container || items.length <= threshold) {
    return false;
  }
  container.replaceChildren();
  container.classList.add("virtual-list");
  container.setAttribute("aria-rowcount", String(items.length));
  container.style.setProperty("--virtual-row-height", `${rowHeight}px`);
  const surface = document.createElement("div");
  surface.className = "virtual-list-surface";
  surface.style.height = `${items.length * rowHeight}px`;
  const renderWindow = () => {
    const scrollTop = container.scrollTop;
    const visibleCount = Math.ceil(viewportHeight / rowHeight) + 2 * overscan;
    const startIndex = Math.max(0, Math.floor(scrollTop / rowHeight) - overscan);
    const endIndex = Math.min(items.length, startIndex + visibleCount);
    surface.replaceChildren(...items.slice(startIndex, endIndex).map((item, offset) => {
      const wrapper = document.createElement("div");
      wrapper.className = "virtual-list-item";
      wrapper.style.top = `${(startIndex + offset) * rowHeight}px`;
      wrapper.setAttribute("aria-rowindex", String(startIndex + offset + 1));
      const rendered = renderItem(item, startIndex + offset);
      if (rendered instanceof Node) {
        wrapper.append(rendered);
      } else {
        wrapper.innerHTML = String(rendered);
      }
      return wrapper;
    }));
  };
  let frame = 0;
  const scheduleRender = () => {
    if (frame) return;
    frame = requestAnimationFrame(() => {
      frame = 0;
      renderWindow();
    });
  };
  container.addEventListener("scroll", scheduleRender, { passive: true });
  surface._virtualCleanup = () => {
    container.removeEventListener("scroll", scheduleRender);
    if (frame) cancelAnimationFrame(frame);
  };
  container.append(surface);
  renderWindow();
  return true;
}

export function renderVirtualTableBody(tbody, rows, { rowHeight, threshold = DEFAULT_THRESHOLD } = {}) {
  if (!tbody || rows.length <= threshold) {
    return false;
  }
  const table = tbody.closest("table");
  const columnCount = table?.querySelectorAll("thead th").length || 1;
  const viewport = document.createElement("div");
  viewport.className = "virtual-table-viewport";
  viewport.style.height = `min(70vh, 720px)`;
  viewport.style.overflowY = "auto";
  const list = document.createElement("div");
  viewport.append(list);
  const fragment = document.createDocumentFragment();
  const spacer = document.createElement("tr");
  spacer.innerHTML = `<td colspan="${columnCount}"></td>`;
  spacer.firstElementChild.style.height = `${rows.length * rowHeight}px`;
  fragment.append(spacer);
  tbody.replaceChildren(fragment);
  tbody.parentElement.replaceWith(viewport);
  renderVirtualList(viewport, rows, {
    rowHeight,
    renderItem: (row) => {
      const wrapper = document.createElement("table");
      wrapper.className = table.className;
      wrapper.innerHTML = `<tbody>${row}</tbody>`;
      return wrapper.querySelector("tr");
    },
  });
  return true;
}
