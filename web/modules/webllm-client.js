// spec: consultor/consultor v2.59 — inicialização cancelável e política segura para Safari
// WebLLM mantém runtime e pesos no Cache Storage privado da origem do navegador.
export const DEFAULT_LOCAL_MODEL_ID = "Qwen2.5-1.5B-Instruct-q4f16_1-MLC";
const LOW_MEMORY_FALLBACK_MODEL_ID = "Qwen3-0.6B-q4f16_1-MLC";
const WEBLLM_VENDOR_VERSION = "0.2.89";
const WEBLLM_CACHE_BUSTER = 188;
const SUPPORTED_MODEL_IDS = new Set([
  DEFAULT_LOCAL_MODEL_ID,
  "Qwen3-0.6B-q4f16_1-MLC",
  "gemma3-1b-it-q4f16_1-MLC",
  "Llama-3.2-1B-Instruct-q4f16_1-MLC",
  "Qwen3-1.7B-q4f16_1-MLC",
  "Qwen2.5-3B-Instruct-q4f16_1-MLC",
  "Qwen3-4B-q4f16_1-MLC",
]);
// spec: consultor/consultor v2.51 — critério 71; decisão em adr/0021-janela-contexto-local-consultor v0.2
const CHAT_OPTIONS = { context_window_size: 4096 };
export const LOCAL_MODEL_PREPARE_TIMEOUT_MS = 60_000;
export const LOCAL_INFERENCE_TIMEOUT_MS = 90_000;
const WORKER_INIT_TIMEOUT_MS = 20_000;
const ENGINE_UNLOAD_TIMEOUT_MS = 3_000;
let libraryPromise;
let engine;
let enginePromise;
let engineWorker;
let pendingEngine;
let engineModelId = "";
let lowMemoryModelForSelection = "";
let engineGeneration = 0;
let enginePromiseStartedAt = 0;

function resolveModelId(value) {
  const modelId = String(value || DEFAULT_LOCAL_MODEL_ID).trim();
  return SUPPORTED_MODEL_IDS.has(modelId) ? modelId : DEFAULT_LOCAL_MODEL_ID;
}

function library() {
  libraryPromise ||= import(`../vendor/webllm/${WEBLLM_VENDOR_VERSION}/webllm.js`);
  return libraryPromise;
}

function isSafariWebGPUEnvironment() {
  const userAgent = String(globalThis.navigator?.userAgent || "");
  if (/iPhone|iPad|iPod/i.test(userAgent)) return true;
  return /AppleWebKit/i.test(userAgent) && !/(Chrome|Chromium|CriOS|Edg|FxiOS)/i.test(userAgent);
}

function supported() {
  return Boolean(globalThis.navigator?.gpu);
}

async function requireWebGPUAdapter() {
  if (!supported()) {
    const error = new Error("webgpu_unavailable");
    error.code = "webgpu_unavailable";
    throw error;
  }
  if (typeof globalThis.navigator.gpu.requestAdapter !== "function") {
    const error = new Error("webgpu_adapter_unavailable");
    error.code = "webgpu_adapter_unavailable";
    throw error;
  }
  let adapter;
  try {
    adapter = await globalThis.navigator.gpu.requestAdapter();
  } catch (requestError) {
    const error = new Error("webgpu_adapter_unavailable");
    error.code = "webgpu_adapter_unavailable";
    error.cause = requestError;
    throw error;
  }
  if (!adapter) {
    const error = new Error("webgpu_adapter_unavailable");
    error.code = "webgpu_adapter_unavailable";
    throw error;
  }
  return adapter;
}

async function hasWebGPUAdapter() {
  if (!supported()) return false;
  try {
    return Boolean(await globalThis.navigator.gpu.requestAdapter());
  } catch (error) {
    console.warn("WebGPU adapter check failed", { errorType: error?.name || typeof error });
    return false;
  }
}

function operationError(code) {
  const error = new Error(code);
  error.code = code;
  return error;
}

function withLocalGuard(operation, signal, timeoutMs) {
  let timeoutId;
  let abortHandler;
  const guards = [operation];
  if (signal) {
    if (signal.aborted) return Promise.reject(operationError("local_operation_cancelled"));
    guards.push(new Promise((_, reject) => {
      abortHandler = () => reject(operationError("local_operation_cancelled"));
      signal.addEventListener("abort", abortHandler, { once: true });
    }));
  }
  guards.push(new Promise((_, reject) => {
    timeoutId = setTimeout(() => reject(operationError("local_operation_timeout")), timeoutMs);
  }));
  return Promise.race(guards).finally(() => {
    clearTimeout(timeoutId);
    if (signal && abortHandler) signal.removeEventListener("abort", abortHandler);
  });
}

// spec: consultor/consultor v2.51 — critério de perda do dispositivo GPU ("Device was lost")
const GPU_MEMORY_PATTERN = /(out of memory|memory allocation|device (was )?lost|insufficient memory|gpudevicelostinfo|gpu.*memory)/;

function classifyInferenceError(error) {
  const detail = String(error?.message || error || "").toLowerCase();
  if (/prompt tokens exceed context window|context window size/.test(detail)) {
    const promptTokens = detail.match(/number of prompt tokens:\s*(\d+)/)?.[1];
    const contextWindow = detail.match(/context window size:\s*(\d+)/)?.[1];
    return {
      category: "context_window_exceeded",
      promptTokens: promptTokens ? Number(promptTokens) : undefined,
      contextWindow: contextWindow ? Number(contextWindow) : undefined,
    };
  }
  if (GPU_MEMORY_PATTERN.test(detail)) {
    return { category: "gpu_memory_or_device_lost" };
  }
  if (/(webgpu.*(unavailable|unsupported)|navigator\.gpu)/.test(detail)) {
    return { category: "webgpu_unavailable" };
  }
  if (error instanceof Error) {
    return { category: "runtime_error" };
  }
  return { category: typeof error === "string" ? "string_error" : typeof error };
}

function normalizeError(error, stage = "initialization") {
  const detail = String(error?.message || error || "").toLowerCase();
  const diagnosis = stage === "inference" ? classifyInferenceError(error) : null;
  if (error?.code === "local_operation_cancelled") {
    return "A execução local foi cancelada.";
  }
  if (error?.code === "local_operation_timeout") {
    return stage === "inference"
      ? "A IA local excedeu 90 segundos sem concluir. Tente novamente ou use a IA remota."
      : "O preparo do modelo local excedeu 60 segundos. Verifique o cache e a conexão e tente novamente.";
  }
  if (error?.code === "worker_init_timeout") {
    return "O Worker do modelo local não respondeu em 20 segundos. O engine foi encerrado para evitar travamento; tente novamente ou use a IA remota.";
  }
  if (error?.code === "worker_runtime_error") {
    return "O Worker do modelo local falhou ao iniciar. O engine foi encerrado para evitar travamento; tente novamente ou use a IA remota.";
  }
  if (error?.code === "webgpu_adapter_unavailable") {
    return "O navegador expôs WebGPU, mas não disponibilizou um adaptador para esta página. Verifique a aceleração gráfica e tente novamente.";
  }
  if (diagnosis?.category === "context_window_exceeded") {
    const contextWindow = diagnosis.contextWindow ? ` (${diagnosis.contextWindow} tokens)` : "";
    return `O prompt da análise excedeu a janela de contexto do modelo local${contextWindow}. Isso pode ocorrer apenas em cards com mais dados, como Análise da Carteira.`;
  }
  if (!supported() || /(webgpu.*(unavailable|unsupported)|navigator\.gpu)/.test(detail)) {
    return "WebGPU não está disponível neste navegador. Atualize o navegador ou habilite a aceleração gráfica e tente novamente.";
  }
  if (GPU_MEMORY_PATTERN.test(detail)) {
    return stage === "inference"
      ? "A memória da GPU não foi suficiente para gerar a análise local."
      : "A memória da GPU não foi suficiente para carregar o modelo local.";
  }
  if (/(fetch|network|download|failed to load|cors|http.*(403|404|429|5))/.test(detail)) {
    return "Não foi possível baixar o modelo local. Verifique a conexão com a internet e tente novamente.";
  }
  if (stage === "inference") {
    return "O modelo local foi carregado, mas falhou ao gerar a análise. Isso não indica incompatibilidade geral deste navegador. Tente novamente; se persistir, envie o tipo do erro registrado no Console do navegador.";
  }
  if (supported()) {
    return "WebGPU foi detectada, mas o engine do modelo local não conseguiu iniciar. Tente novamente ou atualize o cache do modelo nas Preferências.";
  }
  return "Não foi possível iniciar o modelo local neste navegador. Tente novamente ou use um navegador com WebGPU disponível.";
}

async function unloadWithTimeout(activeEngine) {
  if (!activeEngine?.unload) return;
  try {
    await Promise.race([
      Promise.resolve().then(() => activeEngine.unload()),
      new Promise((resolve) => setTimeout(resolve, ENGINE_UNLOAD_TIMEOUT_MS)),
    ]);
  } catch (error) {
    console.warn("WebLLM local unload failure", { errorType: error?.name || typeof error });
  }
}

async function disposeEngine() {
  engineGeneration += 1;
  const activeEngine = engine || pendingEngine;
  const activeWorker = engineWorker;
  engine = undefined;
  pendingEngine = undefined;
  enginePromise = undefined;
  engineWorker = undefined;
  engineModelId = "";
  enginePromiseStartedAt = 0;
  await unloadWithTimeout(activeEngine);
  activeWorker?.terminate();
}

function workerFailure(event) {
  const error = new Error(String(event?.error?.message || event?.message || "WebLLM Worker failed"));
  error.code = "worker_runtime_error";
  return error;
}

function withWorkerGuard(operation, worker) {
  let rejectWorkerFailure;
  let timeoutId;
  const fail = (event) => rejectWorkerFailure?.(workerFailure(event));
  const workerFailurePromise = new Promise((_, reject) => {
    rejectWorkerFailure = reject;
    worker.addEventListener("error", fail, { once: true });
    worker.addEventListener("messageerror", fail, { once: true });
  });
  const timeoutPromise = new Promise((_, reject) => {
    timeoutId = setTimeout(() => reject(operationError("worker_init_timeout")), WORKER_INIT_TIMEOUT_MS);
  });
  return Promise.race([operation, workerFailurePromise, timeoutPromise]).finally(() => {
    clearTimeout(timeoutId);
    worker.removeEventListener("error", fail);
    worker.removeEventListener("messageerror", fail);
  });
}

function logInitializationFailure(modelId, stage, error) {
  console.warn("WebLLM local initialization failure", {
    modelId,
    stage,
    errorType: error?.name || typeof error,
    errorCode: error?.code || undefined,
    errorMessage: String(error?.message || error || "").slice(0, 240),
  });
}

async function ensureEngine(modelId, onProgress, { preferMainThread = true } = {}) {
  const selectedModelId = resolveModelId(modelId);
  await requireWebGPUAdapter();
  if (engine && engineModelId === selectedModelId) return engine;
  if (enginePromise) {
    if (engineModelId === selectedModelId) return enginePromise;
    await disposeEngine();
  }
  if (engine) await disposeEngine();
  if (!enginePromise) {
    const generation = engineGeneration;
    engineModelId = selectedModelId;
    enginePromiseStartedAt = Date.now();
    enginePromise = library().then(async (webllm) => {
      const engineConfig = {
        initProgressCallback: (progress) => onProgress?.(progress.text || "Baixando modelo local…"),
      };
      let mainThreadError;
      if (preferMainThread) {
        onProgress?.("Preparando o modelo local diretamente na página…");
        const pageEngine = new webllm.MLCEngine(engineConfig);
        pendingEngine = pageEngine;
        try {
          await pageEngine.reload(selectedModelId, CHAT_OPTIONS);
          return pageEngine;
        } catch (error) {
          mainThreadError = error;
          logInitializationFailure(selectedModelId, "main-thread", error);
          await unloadWithTimeout(pageEngine);
          if (isSafariWebGPUEnvironment()) throw error;
          onProgress?.("A página não iniciou a GPU. Tentando o Worker do WebLLM…");
        } finally {
          if (pendingEngine === pageEngine) pendingEngine = undefined;
        }
      }
      try {
        onProgress?.("Preparando o modelo local no Worker do WebLLM…");
        engineWorker = new Worker(new URL(`./webllm-worker.js?v=${WEBLLM_CACHE_BUSTER}`, import.meta.url), { type: "module" });
        const workerEngine = new webllm.WebWorkerMLCEngine(engineWorker, engineConfig);
        pendingEngine = workerEngine;
        await withWorkerGuard(workerEngine.reload(selectedModelId, CHAT_OPTIONS), engineWorker);
        return workerEngine;
      } catch (workerError) {
        // spec: consultor/consultor v2.52 — critério de preparo explícito do modelo local
        // Alguns navegadores podem expor WebGPU à página, mas falhar ao inicializar o Dedicated Worker.
        // A página é a primeira tentativa; o Worker permanece como fallback compatível.
        logInitializationFailure(selectedModelId, "worker", workerError);
        engineWorker?.terminate();
        engineWorker = undefined;
        if (!preferMainThread) {
          onProgress?.("O Worker não iniciou a GPU. Preparando o modelo local diretamente na página…");
          const pageEngine = new webllm.MLCEngine(engineConfig);
          pendingEngine = pageEngine;
          try {
            await pageEngine.reload(selectedModelId, CHAT_OPTIONS);
            return pageEngine;
          } catch (fallbackMainThreadError) {
            mainThreadError = fallbackMainThreadError;
            logInitializationFailure(selectedModelId, "main-thread-fallback", fallbackMainThreadError);
            await unloadWithTimeout(pageEngine);
          } finally {
            if (pendingEngine === pageEngine) pendingEngine = undefined;
          }
        }
        const finalError = mainThreadError || (workerError instanceof Error ? workerError : new Error(String(workerError)));
        finalError.workerError = workerError;
        throw finalError;
      }
    }).then((readyEngine) => {
      if (generation !== engineGeneration) {
        Promise.resolve(readyEngine?.unload?.()).catch(() => {});
        throw operationError("local_operation_cancelled");
      }
      engine = readyEngine;
      return readyEngine;
    }).catch(async (error) => {
      const failedEngine = pendingEngine;
      pendingEngine = undefined;
      await unloadWithTimeout(failedEngine);
      engineWorker?.terminate();
      engineWorker = undefined;
      enginePromise = undefined;
      engineModelId = "";
      enginePromiseStartedAt = 0;
      throw error;
    });
  }
  return enginePromise;
}

export async function runLocalInference(messages, options, onProgress, signal) {
  const configuredModelId = resolveModelId(options?.local_model_id || options?.modelId);
  const selectedModelId = lowMemoryModelForSelection === configuredModelId
    ? LOW_MEMORY_FALLBACK_MODEL_ID
    : configuredModelId;
  const modelCandidates = [selectedModelId];
  if (selectedModelId !== LOW_MEMORY_FALLBACK_MODEL_ID) {
    modelCandidates.push(LOW_MEMORY_FALLBACK_MODEL_ID);
  }
  let lastError;
  let preferMainThread = true;
  for (let index = 0; index < modelCandidates.length; index += 1) {
    const modelId = modelCandidates[index];
    let localEngine;
    try {
      localEngine = await withLocalGuard(
        ensureEngine(modelId, onProgress, { preferMainThread }),
        signal,
        LOCAL_MODEL_PREPARE_TIMEOUT_MS,
      );
    } catch (error) {
      lastError = error;
      if (error?.code === "local_operation_cancelled" || error?.code === "local_operation_timeout") {
        await disposeEngine();
        throw new Error(normalizeError(error, "initialization"));
      }
      const diagnosis = classifyInferenceError(error);
      if (index === 0 && diagnosis.category === "gpu_memory_or_device_lost") {
        lowMemoryModelForSelection = configuredModelId;
        await disposeEngine();
        onProgress?.("O modelo selecionado excedeu a memória disponível. Tentando um modelo local mais leve…");
        continue;
      }
      await disposeEngine();
      throw new Error(normalizeError(error, "initialization"));
    }
    try {
      const result = await withLocalGuard(
        localEngine.chat.completions.create({
          messages,
          temperature: options?.temperature ?? 0.2,
          max_tokens: options?.maxTokens ?? options?.max_tokens ?? 700,
        }),
        signal,
        LOCAL_INFERENCE_TIMEOUT_MS,
      );
      return result.choices?.[0]?.message?.content || "";
    } catch (error) {
      lastError = error;
      if (error?.code === "local_operation_cancelled" || error?.code === "local_operation_timeout") {
        await disposeEngine();
        throw new Error(normalizeError(error, "inference"));
      }
      const errorType = error instanceof Error ? error.name : typeof error;
      const diagnosis = classifyInferenceError(error);
      console.warn("WebLLM local failure", {
        stage: "inference",
        modelId,
        errorType,
        ...diagnosis,
      });
      if (diagnosis.category === "gpu_memory_or_device_lost") {
        await disposeEngine();
      }
      // WebLLM serializa exceções do Worker como strings. No Safari, a perda do
      // dispositivo pode aparecer assim mesmo quando o Console registra GPUDeviceLostInfo.
      const workerRuntimeFailure = diagnosis.category === "string_error";
      if (index === 0 && (diagnosis.category === "gpu_memory_or_device_lost" || workerRuntimeFailure)) {
        lowMemoryModelForSelection = configuredModelId;
        preferMainThread = true;
        onProgress?.("A GPU perdeu o dispositivo com este modelo. Tentando um modelo local mais leve…");
        await disposeEngine();
        continue;
      }
      await disposeEngine();
      throw new Error(normalizeError(error, "inference"));
    }
  }
  throw new Error(normalizeError(lastError, "inference"));
}

export async function getLocalModelStatus(modelId) {
  const selectedModelId = resolveModelId(modelId);
  try {
    const webllm = await library();
    const adapterAvailable = await hasWebGPUAdapter();
    const preparationPending = Boolean(enginePromise && !engine);
    let timedOut = false;
    if (preparationPending && Date.now() - enginePromiseStartedAt >= LOCAL_MODEL_PREPARE_TIMEOUT_MS) {
      await disposeEngine();
      timedOut = true;
    }
    return {
      modelId: selectedModelId,
      cached: await webllm.hasModelInCache(selectedModelId),
      supported: supported(),
      adapter_available: adapterAvailable,
      ready: Boolean(engine && engineModelId === selectedModelId),
      loading: Boolean(enginePromise && !engine),
      timed_out: timedOut,
    };
  } catch (error) {
    throw new Error(normalizeError(error));
  }
}

export async function prepareLocalModel(onProgress, modelId) {
  const selectedModelId = resolveModelId(modelId);
  try {
    onProgress?.("Verificando a compatibilidade WebGPU…");
    await withLocalGuard(
      ensureEngine(selectedModelId, onProgress),
      undefined,
      LOCAL_MODEL_PREPARE_TIMEOUT_MS,
    );
    return { cached: true, supported: true, ready: true, modelId: selectedModelId };
  } catch (error) {
    if (error?.code === "local_operation_timeout") await disposeEngine();
    throw new Error(normalizeError(error));
  }
}

export async function clearLocalModel(modelId) {
  const selectedModelId = resolveModelId(modelId);
  try {
    if (lowMemoryModelForSelection === selectedModelId) lowMemoryModelForSelection = "";
    const webllm = await library();
    if (engineModelId === selectedModelId) await disposeEngine();
    await webllm.deleteModelAllInfoInCache(selectedModelId);
    return { cached: false, modelId: selectedModelId };
  } catch (error) {
    throw new Error(normalizeError(error));
  }
}

export async function refreshLocalModel(onProgress, modelId) {
  const selectedModelId = resolveModelId(modelId);
  await clearLocalModel(selectedModelId);
  return prepareLocalModel(onProgress, selectedModelId);
}

export const runLocalConsultor = runLocalInference;
