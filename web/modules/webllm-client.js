// spec: consultor/consultor v2.43 — critérios de preparo explícito e execução local
// WebLLM mantém runtime e pesos no Cache Storage privado da origem do navegador.
export const DEFAULT_LOCAL_MODEL_ID = "Qwen2.5-1.5B-Instruct-q4f16_1-MLC";
const LOW_MEMORY_FALLBACK_MODEL_ID = "gemma3-1b-it-q4f16_1-MLC";
const SUPPORTED_MODEL_IDS = new Set([
  DEFAULT_LOCAL_MODEL_ID,
  "Qwen3-0.6B-q4f16_1-MLC",
  "gemma3-1b-it-q4f16_1-MLC",
  "Llama-3.2-1B-Instruct-q4f16_1-MLC",
  "Qwen3-1.7B-q4f16_1-MLC",
  "Qwen2.5-3B-Instruct-q4f16_1-MLC",
  "Qwen3-4B-q4f16_1-MLC",
]);
// spec: consultor/consultor v2.43 — critério 71; decisão em adr/0021-janela-contexto-local-consultor v0.2
const CHAT_OPTIONS = { context_window_size: 4096 };
let libraryPromise;
let engine;
let enginePromise;
let engineWorker;
let engineModelId = "";
let lowMemoryModelForSelection = "";

function resolveModelId(value) {
  const modelId = String(value || DEFAULT_LOCAL_MODEL_ID).trim();
  return SUPPORTED_MODEL_IDS.has(modelId) ? modelId : DEFAULT_LOCAL_MODEL_ID;
}

function library() {
  libraryPromise ||= import("../vendor/webllm/0.2.85/webllm.js");
  return libraryPromise;
}

function supported() {
  return Boolean(globalThis.navigator?.gpu);
}

// spec: consultor/consultor v2.43 — critério de perda do dispositivo GPU ("Device was lost")
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
    return "O modelo local foi carregado, mas falhou ao gerar a análise. Isso não indica incompatibilidade geral com o Safari. Tente novamente; se persistir, envie o tipo do erro registrado no Console do navegador.";
  }
  return "Não foi possível iniciar o modelo local neste navegador. Tente novamente ou use um navegador com WebGPU disponível.";
}

async function disposeEngine() {
  const activeEngine = engine;
  const activeWorker = engineWorker;
  engine = undefined;
  enginePromise = undefined;
  engineWorker = undefined;
  engineModelId = "";
  try {
    await activeEngine?.unload?.();
  } catch (error) {
    console.warn("WebLLM local unload failure", error);
  }
  activeWorker?.terminate();
}

async function ensureEngine(modelId, onProgress, { preferMainThread = false } = {}) {
  const selectedModelId = resolveModelId(modelId);
  if (!supported()) {
    throw new Error("webgpu_unavailable");
  }
  if (engine && engineModelId === selectedModelId) return engine;
  if (engine || enginePromise) await disposeEngine();
  if (!enginePromise) {
    engineModelId = selectedModelId;
    enginePromise = library().then(async (webllm) => {
      const engineConfig = {
        initProgressCallback: (progress) => onProgress?.(progress.text || "Baixando modelo local…"),
      };
      if (preferMainThread) {
        onProgress?.("Preparando o modelo local diretamente na página…");
        return webllm.CreateMLCEngine(selectedModelId, engineConfig, CHAT_OPTIONS);
      }
      try {
        engineWorker = new Worker(new URL("./webllm-worker.js?v=182", import.meta.url), { type: "module" });
        return await webllm.CreateWebWorkerMLCEngine(engineWorker, selectedModelId, engineConfig, CHAT_OPTIONS);
      } catch (workerError) {
        // spec: consultor/consultor v2.43 — critério de preparo explícito do modelo local
        // Safari pode expor WebGPU à página, mas não ao Dedicated Worker. O fallback
        // preserva a execução local e reutiliza o mesmo cache privado do navegador.
        engineWorker?.terminate();
        engineWorker = undefined;
        onProgress?.("Este navegador não iniciou a GPU no Worker. Preparando o modelo local diretamente na página…");
        try {
          return await webllm.CreateMLCEngine(selectedModelId, engineConfig, CHAT_OPTIONS);
        } catch (mainThreadError) {
          mainThreadError.workerError = workerError;
          throw mainThreadError;
        }
      }
    }).then((readyEngine) => {
      engine = readyEngine;
      return readyEngine;
    }).catch((error) => {
      engineWorker?.terminate();
      engineWorker = undefined;
      enginePromise = undefined;
      engineModelId = "";
      throw error;
    });
  }
  return enginePromise;
}

export async function runLocalInference(messages, options, onProgress) {
  const configuredModelId = resolveModelId(options?.local_model_id || options?.modelId);
  const selectedModelId = lowMemoryModelForSelection === configuredModelId
    ? LOW_MEMORY_FALLBACK_MODEL_ID
    : configuredModelId;
  const modelCandidates = [selectedModelId];
  if (selectedModelId !== LOW_MEMORY_FALLBACK_MODEL_ID) {
    modelCandidates.push(LOW_MEMORY_FALLBACK_MODEL_ID);
  }
  let lastError;
  let preferMainThread = false;
  for (let index = 0; index < modelCandidates.length; index += 1) {
    const modelId = modelCandidates[index];
    let localEngine;
    try {
      localEngine = await ensureEngine(modelId, onProgress, { preferMainThread });
    } catch (error) {
      lastError = error;
      const diagnosis = classifyInferenceError(error);
      if (index === 0 && diagnosis.category === "gpu_memory_or_device_lost") {
        lowMemoryModelForSelection = configuredModelId;
        await disposeEngine();
        onProgress?.("O modelo selecionado excedeu a memória disponível. Tentando um modelo local mais leve…");
        continue;
      }
      throw new Error(normalizeError(error, "initialization"));
    }
    try {
      const result = await localEngine.chat.completions.create({
        messages,
        temperature: options?.temperature ?? 0.2,
        max_tokens: options?.maxTokens ?? options?.max_tokens ?? 700,
      });
      return result.choices?.[0]?.message?.content || "";
    } catch (error) {
      lastError = error;
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
      throw new Error(normalizeError(error, "inference"));
    }
  }
  throw new Error(normalizeError(lastError, "inference"));
}

export async function getLocalModelStatus(modelId) {
  const selectedModelId = resolveModelId(modelId);
  try {
    const webllm = await library();
    return {
      modelId: selectedModelId,
      cached: await webllm.hasModelInCache(selectedModelId),
      supported: supported(),
    };
  } catch (error) {
    throw new Error(normalizeError(error));
  }
}

export async function prepareLocalModel(onProgress, modelId) {
  const selectedModelId = resolveModelId(modelId);
  try {
    onProgress?.("Verificando a compatibilidade WebGPU…");
    await ensureEngine(selectedModelId, onProgress);
    return { cached: true, supported: true, modelId: selectedModelId };
  } catch (error) {
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
