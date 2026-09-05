import test from "node:test";
import assert from "node:assert/strict";
import { renderCollectionRows, destroyVirtualLists } from "../web/modules/virtual-list.js";

class Element {
  constructor() {
    this.children = []; this.scrollTop = 0; this.listeners = new Map();
    this.style = { setProperty() {} }; this.classList = { add() {} };
  }
  replaceChildren(...nodes) { this.children = nodes; }
  append(...nodes) { this.children.push(...nodes); }
  setAttribute() {}
  addEventListener(name, callback) { this.listeners.set(name, callback); }
  removeEventListener(name) { this.listeners.delete(name); }
  querySelectorAll() {
    return this.children.flatMap(child => [child, ...child.querySelectorAll()])
      .filter(child => child.className === "virtual-list-surface");
  }
}
globalThis.Node = Element;
globalThis.document = { createElement: () => new Element() };
let frames = new Map(), frameId = 0;
globalThis.requestAnimationFrame = callback => { frames.set(++frameId, callback); return frameId; };
globalThis.cancelAnimationFrame = id => frames.delete(id);

test("large list invokes template only for window, including highlighted item", () => {
  const root = new Element(), seen = [];
  const items = Array.from({ length: 10000 }, (_, i) => i);
  renderCollectionRows(root, items, { rowHeight: 86, initialIndex: 9000,
    renderItem: item => { seen.push(item); return String(item); } });
  assert.ok(seen.includes(9000));
  assert.ok(seen.length <= Math.ceil(560 / 86) + 10);
  assert.equal(root.children[0].children.length, seen.length);
  destroyVirtualLists(root);
});

test("collapsed days do not invoke row template, small and compact lists preserve order", () => {
  const root = new Element();
  let calls = 0;
  renderCollectionRows(root, Array(10000).fill(1), { expanded: false, renderItem: () => { calls++; } });
  assert.equal(calls, 0);
  assert.equal(root.children.length, 0);
  renderCollectionRows(root, [3, 1, 2], { renderItem: String });
  assert.equal(root.innerHTML, "312");
  renderCollectionRows(root, Array(201).fill(1), { virtual: false, renderItem: () => { calls++; return "x"; } });
  assert.equal(calls, 201);
});

test("scroll renders next window and replacement cancels pending frame and listener", () => {
  const root = new Element(), seen = [];
  renderCollectionRows(root, Array.from({ length: 1000 }, (_, i) => i), {
    rowHeight: 86, renderItem: item => { seen.push(item); return String(item); },
  });
  seen.length = 0;
  root.scrollTop = 500 * 86;
  root.listeners.get("scroll")();
  const callback = [...frames.values()][0]; frames.clear(); callback();
  assert.ok(seen.includes(500));
  assert.ok(seen.length <= 17);
  root.listeners.get("scroll")();
  assert.equal(frames.size, 1);
  renderCollectionRows(root, [], { expanded: false, renderItem: String });
  assert.equal(frames.size, 0);
  assert.equal(root.listeners.size, 0);
});
