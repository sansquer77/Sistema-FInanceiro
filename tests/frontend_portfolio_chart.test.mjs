import test from "node:test";
import assert from "node:assert/strict";

import { portfolioCoverageNotice } from "../web/modules/portfolio-chart.js";

test("coverage notice distinguishes observed, approximate and future months", () => {
  const notice = portfolioCoverageNotice({
    observed_months: ["2026-07", "2026-08"],
    approximate_months: ["2026-01"],
    future_months: ["2026-10", "2026-11", "2026-12"],
    coverage_percent: 66.67,
  });
  assert.match(notice, /2 de 3 meses decorridos usam snapshot observado \(66,7%\)/);
  assert.match(notice, /1 mês permanece aproximado/);
  assert.match(notice, /3 meses futuros permanecem zerados/);
});

test("coverage notice handles a new portfolio without elapsed snapshots", () => {
  assert.equal(
    portfolioCoverageNotice({ future_months: ["2026-12"] }),
    "Ainda não há mês decorrido com snapshot observado. 1 mês futuro permanece zerado.",
  );
});
