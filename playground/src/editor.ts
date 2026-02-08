import * as monaco from "monaco-editor";
import type { BackendAdapter, DiagnosticInfo } from "./backends/interface";

// Configure Monaco workers
self.MonacoEnvironment = {
  getWorker(_workerId: string, label: string) {
    switch (label) {
      case "editorWorkerService":
        return new Worker(
          new URL(
            "monaco-editor/esm/vs/editor/editor.worker.js",
            import.meta.url,
          ),
          { type: "module" },
        );
      default:
        return new Worker(
          new URL(
            "monaco-editor/esm/vs/editor/editor.worker.js",
            import.meta.url,
          ),
          { type: "module" },
        );
    }
  },
};

const DEFAULT_CODE = `def greet(name: str) -> str:
    return "Hello, " + name

result: int = greet("world")  # Type error: str assigned to int

numbers: list[int] = [1, 2, 3]
total: str = sum(numbers)  # Type error: int assigned to str
`;

let editor: monaco.editor.IStandaloneCodeEditor;
let currentAdapter: BackendAdapter | null = null;
let currentVersion = 0;
let debounceTimer: ReturnType<typeof setTimeout> | null = null;
let hoverDisposable: monaco.IDisposable | null = null;

export function createEditor(): monaco.editor.IStandaloneCodeEditor {
  const container = document.getElementById("editor-container")!;

  editor = monaco.editor.create(container, {
    value: DEFAULT_CODE,
    language: "python",
    theme: "vs-dark",
    selectOnLineNumbers: true,
    minimap: { enabled: false },
    fixedOverflowWidgets: true,
    hover: { enabled: true },
    scrollBeyondLastLine: false,
    autoIndent: "full",
    fontFamily: 'Monaco, Menlo, Consolas, "Courier New", monospace',
    fontSize: 14,
    showUnused: true,
    wordBasedSuggestions: "off",
    "semanticHighlighting.enabled": true,
    automaticLayout: true,
    padding: { top: 12, bottom: 12 },
  });

  // Listen for content changes (debounced 500ms) — registered once
  editor.onDidChangeModelContent(() => {
    if (debounceTimer) clearTimeout(debounceTimer);
    debounceTimer = setTimeout(() => runDiagnostics(), 500);
  });

  return editor;
}

export function setAdapter(adapter: BackendAdapter): void {
  // Clear old markers and hover provider
  if (currentAdapter) {
    monaco.editor.setModelMarkers(
      editor.getModel()!,
      currentAdapter.name,
      [],
    );
  }
  if (hoverDisposable) {
    hoverDisposable.dispose();
    hoverDisposable = null;
  }

  currentAdapter = adapter;
  currentVersion = 0;

  // Register hover provider
  hoverDisposable = monaco.languages.registerHoverProvider("python", {
    provideHover: async (_model, position) => {
      if (!currentAdapter) return null;
      const info = await currentAdapter.getHover(
        position.lineNumber,
        position.column,
      );
      if (!info) return null;
      return {
        range: info.range,
        contents: [{ value: info.contents }],
      };
    },
  });

  // Run diagnostics immediately for initial code
  runDiagnostics();
}

async function runDiagnostics(): Promise<void> {
  if (!currentAdapter) return;

  const version = ++currentVersion;
  const code = editor.getValue();

  const diagnostics = await currentAdapter.updateCode(code);

  // Stale check — a newer version was triggered
  if (version !== currentVersion) return;

  setMarkers(currentAdapter.name, diagnostics);
}

function setMarkers(owner: string, diagnostics: DiagnosticInfo[]): void {
  const model = editor.getModel();
  if (!model) return;

  const markers: monaco.editor.IMarkerData[] = diagnostics.map((d) => ({
    startLineNumber: d.startLineNumber,
    startColumn: d.startColumn,
    endLineNumber: d.endLineNumber,
    endColumn: d.endColumn,
    message: d.message,
    severity: d.severity,
    source: d.source,
    code: d.code,
  }));

  monaco.editor.setModelMarkers(model, owner, markers);
}
