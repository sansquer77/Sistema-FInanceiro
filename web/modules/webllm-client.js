// spec: consultor/consultor v2.13 — critérios de preparo explícito e execução local
// WebLLM mantém runtime e pesos no Cache Storage privado da origem do navegador.
const MODEL_ID = "Qwen2.5-3B-Instruct-q4f16_1-MLC";
let libraryPromise;
let engine;
let enginePromise;
let engineWorker;

function library() {
  libraryPromise ||= import("../vendor/webllm/0.2.85/webllm.js");
  return libraryPromise;
}

function supported() {
  return Boolean(globalThis.navigator?.gpu);
}

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
  if (/(out of memory|memory allocation|device lost|gpu.*memory)/.test(detail)) {
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
  if (/(out of memory|memory allocation|device lost|gpu.*memory)/.test(detail)) {
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

async function ensureEngine(onProgress) {
  if (!supported()) {
    throw new Error("webgpu_unavailable");
  }
  if (engine) return engine;
  if (!enginePromise) {
    enginePromise = library().then(async (webllm) => {
      const engineConfig = {
        initProgressCallback: (progress) => onProgress?.(progress.text || "Baixando modelo local…"),
      };
      try {
        engineWorker = new Worker(new URL("./webllm-worker.js?v=175", import.meta.url), { type: "module" });
        return await webllm.CreateWebWorkerMLCEngine(engineWorker, MODEL_ID, engineConfig);
      } catch (workerError) {
        // spec: consultor/consultor v2.13 — critério de preparo explícito do modelo local
        // Safari pode expor WebGPU à página, mas não ao Dedicated Worker. O fallback
        // preserva a execução local e reutiliza o mesmo cache privado do navegador.
        engineWorker?.terminate();
        engineWorker = undefined;
        onProgress?.("Este navegador não iniciou a GPU no Worker. Preparando o modelo local diretamente na página…");
        try {
          return await webllm.CreateMLCEngine(MODEL_ID, engineConfig);
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
      throw error;
    });
  }
  return enginePromise;
}

export async function runLocalInference(messages, options, onProgress) {
  let localEngine;
  try {
    localEngine = await ensureEngine(onProgress);
  } catch (error) {
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
    const errorType = error instanceof Error ? error.name : typeof error;
    const diagnosis = classifyInferenceError(error);
    console.warn("WebLLM local failure", {
      stage: "inference",
      errorType,
      ...diagnosis,
    });
    throw new Error(normalizeError(error, "inference"));
  }
}

export async function getLocalModelStatus() {
  try {
    const webllm = await library();
    return {
      cached: await webllm.hasModelInCache(MODEL_ID),
      supported: supported(),
    };
  } catch (error) {
    throw new Error(normalizeError(error));
  }
}

export async function prepareLocalModel(onProgress) {
  try {
    onProgress?.("Verificando a compatibilidade WebGPU…");
    await ensureEngine(onProgress);
    return { cached: true, supported: true };
  } catch (error) {
    throw new Error(normalizeError(error));
  }
}

export async function clearLocalModel() {
  try {
    const webllm = await library();
    await engine?.unload?.();
    engineWorker?.terminate();
    engine = undefined;
    enginePromise = undefined;
    engineWorker = undefined;
    await webllm.deleteModelAllInfoInCache(MODEL_ID);
    return { cached: false };
  } catch (error) {
    throw new Error(normalizeError(error));
  }
}

export const runLocalConsultor = runLocalInference;
