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
const failedBackends = new Set<BackendName>();

function createBackend(name: BackendName): BackendAdapter {
  switch (name) {
    case "Pyright":
      return new PyrightBackend();
    case "Pyrefly":
      return new PyreflyBackend();
    case "ty":
      return new TyBackend();
  }
}

async function switchBackend(name: BackendName): Promise<void> {
  if (failedBackends.has(name)) return;

  // Dispose current adapter
  if (currentAdapter) {
    currentAdapter.dispose();
    currentAdapter = null;
  }

  setStatus(`Loading ${name}...`, "loading");

  try {
    const adapter = createBackend(name);
    await adapter.initialize();
    currentAdapter = adapter;
    setAdapter(adapter);
    setStatus(name, "ready");
  } catch (err) {
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
  await switchBackend("Pyright");
}

main();
