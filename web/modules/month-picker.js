import { isValidMonthValue } from "./date-utils.js";

let monthPickerPopover = null;

export function openMonthPicker(anchor, value, onSelect) {
  if (!anchor || !isValidMonthValue(value)) {
    return;
  }
  if (!monthPickerPopover) {
    monthPickerPopover = createMonthPickerPopover();
  }
  const [year, month] = value.split("-");
  monthPickerPopover.monthSelect.value = month;
  monthPickerPopover.yearInput.value = year;
  monthPickerPopover.onSelect = onSelect;
  const rect = anchor.getBoundingClientRect();
  monthPickerPopover.popover.style.top = `${window.scrollY + rect.bottom + 6}px`;
  monthPickerPopover.popover.style.left = `${window.scrollX + rect.left}px`;
  monthPickerPopover.popover.hidden = false;
  anchor.setAttribute("aria-expanded", "true");
  monthPickerPopover.anchor = anchor;
  monthPickerPopover.monthSelect.focus();
}

export function closeMonthPicker() {
  if (!monthPickerPopover) {
    return;
  }
  if (monthPickerPopover.anchor) {
    monthPickerPopover.anchor.setAttribute("aria-expanded", "false");
  }
  monthPickerPopover.popover.hidden = true;
  monthPickerPopover.onSelect = null;
  monthPickerPopover.anchor = null;
}

function createMonthPickerPopover() {
  const popover = document.createElement("div");
  popover.className = "month-popover";
  popover.hidden = true;
  popover.innerHTML = `
    <label>Mês
      <select data-month-select>
        <option value="01">Janeiro</option>
        <option value="02">Fevereiro</option>
        <option value="03">Março</option>
        <option value="04">Abril</option>
        <option value="05">Maio</option>
        <option value="06">Junho</option>
        <option value="07">Julho</option>
        <option value="08">Agosto</option>
        <option value="09">Setembro</option>
        <option value="10">Outubro</option>
        <option value="11">Novembro</option>
        <option value="12">Dezembro</option>
      </select>
    </label>
    <label>Ano
      <input data-year-input type="number" min="1900" max="2200" step="1">
    </label>
    <div class="month-popover-actions">
      <button class="ghost small-button" type="button" data-month-cancel>Cancelar</button>
      <button class="primary small-button" type="button" data-month-apply>Aplicar</button>
    </div>
  `;
  document.body.append(popover);
  const monthSelect = popover.querySelector("[data-month-select]");
  const yearInput = popover.querySelector("[data-year-input]");
  const applyButton = popover.querySelector("[data-month-apply]");
  const cancelButton = popover.querySelector("[data-month-cancel]");
  const picker = { popover, monthSelect, yearInput, applyButton, cancelButton, onSelect: null };
  popover.addEventListener("click", (event) => event.stopPropagation());
  cancelButton.addEventListener("click", closeMonthPicker);
  applyButton.addEventListener("click", () => {
    const value = `${String(yearInput.value || "").padStart(4, "0")}-${monthSelect.value}`;
    if (isValidMonthValue(value) && picker.onSelect) {
      picker.onSelect(value);
    }
    closeMonthPicker();
  });
  document.addEventListener("click", closeMonthPicker);
  document.addEventListener("keydown", (event) => {
    if (event.key === "Escape") {
      closeMonthPicker();
    }
  });
  return picker;
}
