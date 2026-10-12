// O protocolo do WebLLM mantém WebGPU e os pesos fora da thread da interface.
import { WebWorkerMLCEngineHandler } from "../vendor/webllm/0.2.85/webllm.js";

const handler = new WebWorkerMLCEngineHandler();

self.onmessage = (event) => handler.onmessage(event);
