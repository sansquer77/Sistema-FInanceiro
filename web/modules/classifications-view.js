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
  } = elements;

  categoryForm.addEventListener("submit", handleCategorySubmit);
  categoryGroup.addEventListener("change", handleCategoryGroupChange);
  subcategoryForm.addEventListener("submit", handleSubcategorySubmit);
  tagForm.addEventListener("submit", handleTagSubmit);

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
    renderClassificationList(categoryList, filteredClassificationCategories(), "categories");
    renderClassificationList(tagList, state.tags, "tags");
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

  function renderClassificationList(container, items, type) {
    container.innerHTML = "";
    if (items.length === 0) {
      container.append(emptyState(type === "categories" ? "Nenhuma categoria cadastrada." : "Nenhuma tag cadastrada."));
      return;
    }
    items.forEach((item) => {
      const row = document.createElement("article");
      row.className = "classification-item";
      const subcategories = type === "categories" ? item.subcategories || [] : [];
      row.innerHTML = `
        <div>
          <strong>${escapeHtml(item.name)}</strong>
          <span>${type === "categories" ? `${classificationGroupLabel(item.group_type)} · ` : ""}${item.transaction_count} lançamento(s)</span>
        </div>
        <div class="card-actions">
          <button class="ghost small-button" type="button" data-action="rename">Renomear</button>
          <button class="danger small-button" type="button" data-action="delete">Excluir</button>
        </div>
        ${subcategories.length ? `
          <div class="subcategory-list">
            ${subcategories.map((subcategory) => `
              <div class="subcategory-item" data-subcategory-id="${subcategory.id}">
                <span>${escapeHtml(subcategory.name)} · ${subcategory.transaction_count} lançamento(s)</span>
                <div class="card-actions">
                  <button class="ghost small-button" type="button" data-action="rename-subcategory">Renomear</button>
                  <button class="danger small-button" type="button" data-action="delete-subcategory">Excluir</button>
                </div>
              </div>
            `).join("")}
          </div>
        ` : ""}
      `;
      row.querySelector('[data-action="rename"]').addEventListener("click", () => renameClassification(type, item));
      row.querySelector('[data-action="delete"]').addEventListener("click", () => deleteClassification(type, item));
      row.querySelectorAll("[data-subcategory-id]").forEach((element) => {
        const subcategory = subcategories.find((entry) => String(entry.id) === element.dataset.subcategoryId);
        element.querySelector('[data-action="rename-subcategory"]').addEventListener("click", () => renameSubcategory(subcategory));
        element.querySelector('[data-action="delete-subcategory"]').addEventListener("click", () => deleteSubcategory(subcategory));
      });
      container.append(row);
    });
  }

  return {
    loadClassifications,
    renderClassifications,
  };
}
