export function createClassificationSuggestion({
  api,
  form,
  typeInput,
  categoryInput,
  subcategoryInput,
  messageElement,
  renderSubcategories,
  afterApply = () => {},
  allowedTypes = null,
  debounceMs = 300,
}) {
  let timer = null;
  let requestId = 0;
  let selectionTouched = false;

  function clearMessage() {
    if (messageElement) messageElement.textContent = "";
  }

  function reset() {
    clearTimeout(timer);
    requestId += 1;
    selectionTouched = false;
    clearMessage();
  }

  function markSelectionTouched() {
    selectionTouched = true;
    clearMessage();
  }

  function schedule() {
    clearTimeout(timer);
    const currentRequestId = ++requestId;
    clearMessage();
    const description = form.elements.description.value.trim();
    if (
      form.elements.id.value
      || selectionTouched
      || (allowedTypes && !allowedTypes.includes(typeInput.value))
      || description.length < 2
    ) return;
    timer = setTimeout(() => apply(currentRequestId), debounceMs);
  }

  async function apply(currentRequestId) {
    const description = form.elements.description.value.trim();
    const groupType = typeInput.value;
    try {
      const response = await api(
        `/api/classification-suggestion?description=${encodeURIComponent(description)}&group_type=${encodeURIComponent(groupType)}`,
      );
      if (
        currentRequestId !== requestId
        || selectionTouched
        || form.elements.id.value
        || description !== form.elements.description.value.trim()
        || groupType !== typeInput.value
        || !response.suggestion
      ) return;
      const suggestion = response.suggestion;
      if (!Array.from(categoryInput.options).some((option) => option.value === suggestion.category_name)) return;
      categoryInput.value = suggestion.category_name;
      renderSubcategories();
      if (
        suggestion.subcategory_name
        && Array.from(subcategoryInput.options).some((option) => option.value === suggestion.subcategory_name)
      ) subcategoryInput.value = suggestion.subcategory_name;
      afterApply();
      if (messageElement) {
        const path = suggestion.subcategory_name
          ? `${suggestion.category_name} › ${suggestion.subcategory_name}`
          : suggestion.category_name;
        messageElement.textContent = `Sugerido pelo histórico: ${path}`;
      }
    } catch {
      // A classificação assistida nunca bloqueia o cadastro manual.
    }
  }

  return { schedule, reset, markSelectionTouched };
}
