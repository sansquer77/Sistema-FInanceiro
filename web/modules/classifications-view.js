export function normalizeClassificationSearch(value) {
  return String(value || "")
    .normalize("NFD")
    .replace(/[\u0300-\u036f]/g, "")
    .trim()
    .toLocaleLowerCase("pt-BR");
}

export function filterClassificationItems(items, query, { includeSubcategories = false } = {}) {
  const normalizedQuery = normalizeClassificationSearch(query);
  if (!normalizedQuery) return items;
  return items.flatMap((item) => {
    const itemMatches = normalizeClassificationSearch(item.name).includes(normalizedQuery);
    if (!includeSubcategories) return itemMatches ? [item] : [];
    const subcategories = item.subcategories || [];
    const matchingSubcategories = subcategories.filter((subcategory) => (
      normalizeClassificationSearch(subcategory.name).includes(normalizedQuery)
    ));
    if (!itemMatches && matchingSubcategories.length === 0) return [];
    return [{
      ...item,
      subcategories: itemMatches ? subcategories : matchingSubcategories,
      searchMatchedSubcategory: !itemMatches && matchingSubcategories.length > 0,
    }];
  });
}

export function registerClassificationsView({
  state,
  elements,
  api,
  formData,
  setMessage,
  emptyState,
  escapeHtml,
  classificationGroupLabel,
  onClassificationsChanged = () => {},
}) {
  const {
    categoryForm,
    categoryGroup,
    subcategoryForm,
    subcategoryCategory,
    tagForm,
    categoryMessage,
    tagMessage,
    categoryList,
    tagList,
    categorySearch,
    tagSearch,
    categoryListSummary,
    tagListSummary,
  } = elements;
  const expandedCategories = new Set();

  categoryForm.addEventListener("submit", handleCategorySubmit);
  categoryGroup.addEventListener("change", handleCategoryGroupChange);
  subcategoryForm.addEventListener("submit", handleSubcategorySubmit);
  tagForm.addEventListener("submit", handleTagSubmit);
  categorySearch.addEventListener("input", renderFilteredLists);
  tagSearch.addEventListener("input", renderFilteredLists);

  async function loadClassifications() {
    const [categoriesResponse, tagsResponse] = await Promise.all([
      api("/api/categories"),
      api("/api/tags"),
    ]);
    state.categories = categoriesResponse.categories;
    state.tags = tagsResponse.tags;
    onClassificationsChanged();
  }

  async function handleCategorySubmit(event) {
    event.preventDefault();
    categoryForm.elements.group_type.value = categoryGroup.value;
    await createClassification("categories", categoryForm, categoryMessage);
    categoryForm.elements.group_type.value = categoryGroup.value;
  }

  function handleCategoryGroupChange() {
    categoryForm.elements.group_type.value = categoryGroup.value;
    setMessage(categoryMessage, "");
    renderClassifications();
  }

  async function handleSubcategorySubmit(event) {
    event.preventDefault();
    setMessage(categoryMessage, "");
    if (filteredClassificationCategories().length === 0) {
      setMessage(categoryMessage, "Cadastre uma categoria antes de adicionar subcategorias.", "error");
      return;
    }
    try {
      await api("/api/subcategories", { method: "POST", body: formData(subcategoryForm) });
      subcategoryForm.elements.name.value = "";
      await loadClassifications();
      renderClassifications();
      setMessage(categoryMessage, "Subcategoria salva.", "success");
    } catch (error) {
      setMessage(categoryMessage, error.message, "error");
    }
  }

  async function handleTagSubmit(event) {
    event.preventDefault();
    await createClassification("tags", tagForm, tagMessage);
  }

  async function createClassification(type, form, messageElement) {
    setMessage(messageElement, "");
    try {
      await api(`/api/${type}`, { method: "POST", body: formData(form) });
      form.reset();
      await loadClassifications();
      renderClassifications();
      setMessage(messageElement, "Item salvo.", "success");
    } catch (error) {
      setMessage(messageElement, error.message, "error");
    }
  }

  async function renameClassification(type, item) {
    const label = type === "categories" ? "categoria" : "tag";
    const name = window.prompt(`Renomear ${label}`, item.name);
    if (name === null) {
      return;
    }
    try {
      await api(`/api/${type}/${item.id}`, { method: "PUT", body: { name } });
      await loadClassifications();
      renderClassifications();
    } catch (error) {
      setMessage(type === "categories" ? categoryMessage : tagMessage, error.message, "error");
    }
  }

  async function deleteClassification(type, item) {
    const messageElement = type === "categories" ? categoryMessage : tagMessage;
    setMessage(messageElement, "");
    try {
      await api(`/api/${type}/${item.id}`, { method: "DELETE" });
      await loadClassifications();
      renderClassifications();
      setMessage(messageElement, "Item excluído.", "success");
    } catch (error) {
      setMessage(messageElement, error.message, "error");
    }
  }

  async function renameSubcategory(item) {
    const name = window.prompt("Renomear subcategoria", item.name);
    if (name === null) {
      return;
    }
    try {
      await api(`/api/subcategories/${item.id}`, { method: "PUT", body: { name } });
      await loadClassifications();
      renderClassifications();
    } catch (error) {
      setMessage(categoryMessage, error.message, "error");
    }
  }

  async function deleteSubcategory(item) {
    setMessage(categoryMessage, "");
    try {
      await api(`/api/subcategories/${item.id}`, { method: "DELETE" });
      await loadClassifications();
      renderClassifications();
      setMessage(categoryMessage, "Subcategoria excluída.", "success");
    } catch (error) {
      setMessage(categoryMessage, error.message, "error");
    }
  }

  function renderClassifications() {
    renderSubcategoryOptions();
    renderFilteredLists();
  }

  function renderFilteredLists() {
    const categoryItems = filterClassificationItems(
      filteredClassificationCategories(), categorySearch.value, { includeSubcategories: true },
    );
    const tagItems = filterClassificationItems(state.tags, tagSearch.value);
    renderClassificationList(categoryList, categoryItems, "categories", Boolean(categorySearch.value.trim()));
    renderClassificationList(tagList, tagItems, "tags", Boolean(tagSearch.value.trim()));
    categoryListSummary.textContent = listSummary(categoryItems.length, "categoria", "categorias");
    tagListSummary.textContent = listSummary(tagItems.length, "tag", "tags");
  }

  function renderSubcategoryOptions() {
    const categories = filteredClassificationCategories();
    const options = categories.map((category) => (
      `<option value="${category.id}">${escapeHtml(category.name)}</option>`
    )).join("");
    subcategoryCategory.innerHTML = options || '<option value="">Cadastre uma categoria neste grupo</option>';
    subcategoryForm.querySelector('button[type="submit"]').disabled = categories.length === 0;
  }

  function filteredClassificationCategories() {
    return state.categories.filter((category) => category.group_type === categoryGroup.value);
  }

  function renderClassificationList(container, items, type, hasSearch) {
    container.innerHTML = "";
    if (items.length === 0) {
      const label = type === "categories" ? "categoria ou subcategoria" : "tag";
      container.append(emptyState(
        hasSearch ? `Nenhuma ${label} corresponde à busca.` : `Nenhuma ${label} cadastrada.`,
      ));
      return;
    }
    items.forEach((item) => {
      const row = document.createElement("article");
      row.className = "classification-item";
      const subcategories = type === "categories" ? item.subcategories || [] : [];
      row.innerHTML = `
        <div class="classification-item-copy">
          <strong>${escapeHtml(item.name)}</strong>
          <span>${type === "categories" ? `${classificationGroupLabel(item.group_type)} · ` : ""}${item.transaction_count} lançamento(s)</span>
        </div>
        ${actionMenuMarkup(item.name, "")}
        ${subcategories.length ? `
          <details class="subcategory-disclosure" ${expandedCategories.has(String(item.id)) || item.searchMatchedSubcategory ? "open" : ""}>
            <summary>${subcategories.length} ${subcategories.length === 1 ? "subcategoria" : "subcategorias"}</summary>
            <div class="subcategory-list">
            ${subcategories.map((subcategory) => `
              <div class="subcategory-item" data-subcategory-id="${subcategory.id}">
                <span>${escapeHtml(subcategory.name)} · ${subcategory.transaction_count} lançamento(s)</span>
                ${actionMenuMarkup(subcategory.name, "-subcategory")}
              </div>
            `).join("")}
            </div>
          </details>
        ` : ""}
      `;
      const disclosure = row.querySelector(".subcategory-disclosure");
      disclosure?.addEventListener("toggle", () => {
        if (disclosure.open) expandedCategories.add(String(item.id));
        else expandedCategories.delete(String(item.id));
      });
      bindAction(row, '[data-action="rename"]', () => renameClassification(type, item));
      bindAction(row, '[data-action="delete"]', () => deleteClassification(type, item));
      row.querySelectorAll("[data-subcategory-id]").forEach((element) => {
        const subcategory = subcategories.find((entry) => String(entry.id) === element.dataset.subcategoryId);
        bindAction(element, '[data-action="rename-subcategory"]', () => renameSubcategory(subcategory));
        bindAction(element, '[data-action="delete-subcategory"]', () => deleteSubcategory(subcategory));
      });
      row.querySelectorAll(".classification-actions-menu").forEach(setupActionMenuKeyboard);
      container.append(row);
    });
  }

  function bindAction(container, selector, action) {
    const button = container.querySelector(selector);
    button.addEventListener("click", () => {
      button.closest(".classification-actions-menu").open = false;
      action();
    });
  }

  function setupActionMenuKeyboard(menu) {
    menu.addEventListener("toggle", () => {
      if (!menu.open) return;
      document.querySelectorAll(".classification-actions-menu[open]").forEach((otherMenu) => {
        if (otherMenu !== menu) otherMenu.open = false;
      });
    });
    menu.addEventListener("keydown", (event) => {
      const buttons = [...menu.querySelectorAll('[role="menuitem"]')];
      const index = buttons.indexOf(document.activeElement);
      if (event.key === "Escape") {
        event.preventDefault();
        menu.open = false;
        menu.querySelector("summary").focus();
      } else if (["ArrowDown", "ArrowUp", "Home", "End"].includes(event.key)) {
        event.preventDefault();
        const nextIndex = event.key === "Home" ? 0
          : event.key === "End" ? buttons.length - 1
            : event.key === "ArrowUp" ? (index <= 0 ? buttons.length - 1 : index - 1)
              : (index + 1) % buttons.length;
        buttons[nextIndex]?.focus();
      }
    });
  }

  function actionMenuMarkup(name, suffix) {
    return `
      <details class="classification-actions-menu">
        <summary aria-label="Mais ações para ${escapeHtml(name)}" title="Mais ações">•••</summary>
        <div class="classification-actions-popover" role="menu" aria-label="Ações para ${escapeHtml(name)}">
          <button type="button" role="menuitem" data-action="rename${suffix}">Renomear</button>
          <button type="button" role="menuitem" class="danger-text" data-action="delete${suffix}">Excluir</button>
        </div>
      </details>
    `;
  }

  function listSummary(count, singular, plural) {
    return `${count} ${count === 1 ? singular : plural}`;
  }

  return {
    loadClassifications,
    renderClassifications,
  };
}
