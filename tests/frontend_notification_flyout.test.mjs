import test from "node:test";
import assert from "node:assert/strict";
import { readFileSync } from "node:fs";
import { notificationEmptyMessage, notificationSectionLabel } from "../web/modules/notification-flyout.js";

test("severidades têm rótulos e estados vazios distintos", () => {
  assert.equal(notificationSectionLabel("critical"), "Alertas críticos");
  assert.equal(notificationSectionLabel("informational"), "Informativos");
  assert.match(notificationEmptyMessage("critical"), /Nenhum alerta crítico/);
  assert.match(notificationEmptyMessage("informational"), /Nenhum novo evento/);
});

test("flyout usa camada global, dialog modal e restaura foco", () => {
  const source = readFileSync(new URL("../web/modules/notification-flyout.js", import.meta.url), "utf8");
  assert.match(source, /document\.body\.append\(dialog\)/);
  assert.match(source, /dialog\.showModal\(\)/);
  assert.match(source, /dialog\.addEventListener\("cancel"/);
  assert.match(source, /event\.target === dialog/);
  assert.match(source, /trigger\?\.focus/);
  assert.doesNotMatch(source, /innerHTML\s*=/);
});

test("Cockpit integra indicadores separados e condensado com carregamento dedicado", () => {
  const html = readFileSync(new URL("../web/index.html", import.meta.url), "utf8");
  const view = readFileSync(new URL("../web/modules/cockpit-view.js", import.meta.url), "utf8");
  assert.match(html, /id="cockpitCriticalNotifications"/);
  assert.match(html, /id="cockpitInformationalNotifications"/);
  assert.match(html, /id="cockpitCombinedNotifications"/);
  assert.match(view, /api\("\/api\/cockpit\/notifications"\)/);
  assert.match(view, /notificationsInFlight/);
  assert.match(view, /notificationsLoadedAt/);
  assert.match(view, /\/api\/cockpit\/notifications\/mark-seen/);
  assert.match(view, /onNotificationAction/);
  assert.match(view, /body: \{ notification_ids: notificationIds \}/);
  assert.doesNotMatch(view, /body: JSON\.stringify\(\{ notification_ids/);
  assert.match(html, /id="cockpitVersionAlert"/);
});

test("orquestrador traduz ações contextuais sem calcular regras financeiras", () => {
  const app = readFileSync(new URL("../web/app.js", import.meta.url), "utf8");
  assert.match(app, /action\?\.route === "limits"/);
  assert.match(app, /action\?\.route === "transactions"/);
  assert.match(app, /action\?\.route === "cards"/);
  assert.match(app, /action\?\.route === "calendar"/);
  assert.match(app, /action\?\.route === "portfolio"/);
});
