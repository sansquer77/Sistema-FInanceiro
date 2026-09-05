import assert from "node:assert/strict";
import test from "node:test";

import {
  filterClassificationItems,
  normalizeClassificationSearch,
} from "../web/modules/classifications-view.js";

test("classification search ignores accents and filters locally", () => {
  assert.equal(normalizeClassificationSearch("  Alimentação  "), "alimentacao");
  const items = [
    { id: 1, name: "Alimentação", subcategories: [] },
    { id: 2, name: "Moradia", subcategories: [] },
  ];
  assert.deepEqual(filterClassificationItems(items, "alimentacao").map((item) => item.id), [1]);
});

test("subcategory match keeps its parent and marks disclosure to open", () => {
  const items = [{
    id: 1,
    name: "Casa",
    subcategories: [{ id: 10, name: "Manutenção" }, { id: 11, name: "Condomínio" }],
  }];
  const result = filterClassificationItems(items, "manutencao", { includeSubcategories: true });
  assert.equal(result.length, 1);
  assert.equal(result[0].searchMatchedSubcategory, true);
  assert.deepEqual(result[0].subcategories.map((item) => item.id), [10]);
});

test("category match preserves its subcategories", () => {
  const items = [{ id: 1, name: "Casa", subcategories: [{ id: 10, name: "Condomínio" }] }];
  const result = filterClassificationItems(items, "casa", { includeSubcategories: true });
  assert.deepEqual(result[0].subcategories, items[0].subcategories);
  assert.equal(result[0].searchMatchedSubcategory, false);
});
