export function createAssetAutocomplete({ input, nameInput, getPositions, onSelect = () => {} }) {
  const list = document.createElement("datalist");
  list.id = `${input.id || input.name}-asset-options`;
  document.body.appendChild(list);
  input.setAttribute("list", list.id);
  input.setAttribute("autocomplete", "off");

  function catalog() {
    const assets = new Map();
    for (const position of getPositions() || []) {
      const identifier = String(position.asset_identifier || "").trim();
      if (!identifier) continue;
      const key = identifier.toLocaleUpperCase("pt-BR");
      if (!assets.has(key)) assets.set(key, position);
    }
    return [...assets.values()].sort((left, right) => (
      String(left.asset_identifier).localeCompare(String(right.asset_identifier), "pt-BR", { sensitivity: "base" })
    ));
  }

  function refresh() {
    list.replaceChildren(...catalog().map((asset) => {
      const option = document.createElement("option");
      option.value = asset.asset_identifier;
      option.label = asset.asset_name && asset.asset_name !== asset.asset_identifier
        ? `${asset.asset_name} · já cadastrado`
        : "Já cadastrado";
      return option;
    }));
  }

  function applyExactMatch() {
    const value = String(input.value || "").trim().toLocaleUpperCase("pt-BR");
    const selected = catalog().find((asset) => String(asset.asset_identifier || "").trim().toLocaleUpperCase("pt-BR") === value);
    if (!selected) return;
    input.value = selected.asset_identifier;
    if (nameInput) nameInput.value = selected.asset_name || selected.asset_identifier;
    onSelect(selected);
  }

  input.addEventListener("focus", refresh);
  input.addEventListener("change", applyExactMatch);
  return { refresh, applyExactMatch };
}
