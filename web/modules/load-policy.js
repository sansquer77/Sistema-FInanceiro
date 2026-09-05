export function createLoadPolicy({ maxAgeMs = 30_000 } = {}) {
  let dirty = true;
  let loadedAt = 0;
  let loadedKey = "";
  let inFlight = null;
  let inFlightKey = "";
  let revision = 0;

  async function run(loader, { force = false, key = "default" } = {}) {
    const normalizedKey = String(key);
    if (!force && !dirty && loadedKey === normalizedKey && Date.now() - loadedAt < maxAgeMs) return;
    if (inFlight) {
      if (inFlightKey === normalizedKey) return inFlight;
      await inFlight;
      return run(loader, { force, key: normalizedKey });
    }
    inFlightKey = normalizedKey;
    const loadRevision = revision;
    inFlight = Promise.resolve().then(loader).then((value) => {
      if (revision === loadRevision) {
        dirty = false;
        loadedAt = Date.now();
        loadedKey = normalizedKey;
      }
      return value;
    }).finally(() => {
      inFlight = null;
      inFlightKey = "";
    });
    return inFlight;
  }

  function markDirty() { dirty = true; revision += 1; }
  function reset() { markDirty(); loadedAt = 0; loadedKey = ""; }
  return { markDirty, reset, run };
}
