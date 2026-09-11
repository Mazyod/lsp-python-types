import { createEditor, setAdapter } from "./editor";
import { PyrightBackend } from "./backends/pyright";
import { PyreflyBackend } from "./backends/pyrefly";
import { TyBackend } from "./backends/ty";
import {
  initUI,
  setStatus,
  setBackendDisabled,
  type BackendName,
} from "./ui";
import type { BackendAdapter } from "./backends/interface";

let currentAdapter: BackendAdapter | null = null;
let switchVersion = 0;
const failedBackends = new Set<BackendName>();

function createBackend(name: BackendName): BackendAdapter {
  switch (name) {
    case "basedpyright":
      return new PyrightBackend();
    case "Pyrefly":
      return new PyreflyBackend();
    case "ty":
      return new TyBackend();
  }
}

async function switchBackend(name: BackendName): Promise<void> {
  if (failedBackends.has(name)) return;
  const version = ++switchVersion;
  setAdapter(null);

  // Dispose current adapter
  if (currentAdapter) {
    currentAdapter.dispose();
    currentAdapter = null;
  }

  setStatus(`Loading ${name}...`, "loading");

  const adapter = createBackend(name);
  try {
    await adapter.initialize();
    if (version !== switchVersion) {
      adapter.dispose();
      return;
    }
    currentAdapter = adapter;
    setAdapter(adapter);
    setStatus(name, "ready");
  } catch (err) {
    adapter.dispose();
    if (version !== switchVersion) return;
    console.error(`Failed to initialize ${name}:`, err);
    failedBackends.add(name);
    setBackendDisabled(name, true);
    setStatus(`${name} unavailable`, "error");
  }
}

async function main(): Promise<void> {
  createEditor();

  initUI({
    onBackendSelect: (name) => switchBackend(name),
  });

  // Load default backend
  await switchBackend("basedpyright");
}

main();
