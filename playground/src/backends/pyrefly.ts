import type * as monaco from "monaco-editor";
import type { BackendAdapter, DiagnosticInfo, HoverInfo } from "./interface";

// Pyrefly returns diagnostics with Monaco-compatible severity values directly
// (8=Error, 4=Warning, 2=Info, 1=Hint)
interface PyreflyError {
  startLineNumber: number;
  startColumn: number;
  endLineNumber: number;
  endColumn: number;
  message_header: string;
  message_details: string;
  kind: string;
  severity: number;
  filename: string;
}

interface PyreflyHover {
  contents: Array<{ value: string }>;
  range?: {
    startLineNumber: number;
    startColumn: number;
    endLineNumber: number;
    endColumn: number;
  };
}

interface PyreflyState {
  updateSandboxFiles(
    files: Record<string, string>,
    force_update: boolean,
  ): string | null;
  updateSingleFile(filename: string, content: string): void;
  setActiveFile(filename: string): void;
  getErrors(): ReadonlyArray<PyreflyError>;
  hover(line: number, column: number): PyreflyHover | null;
  free?(): void;
}

interface PyreflyWasmModule {
  default(): Promise<void>;
  State: new (pythonVersion: string) => PyreflyState;
}

let MarkerSeverity: typeof import("monaco-editor").MarkerSeverity;

const FILENAME = "main.py";

export class PyreflyBackend implements BackendAdapter {
  readonly name = "Pyrefly";
  private state: PyreflyState | null = null;

  async initialize(): Promise<void> {
    const monaco = await import("monaco-editor");
    MarkerSeverity = monaco.MarkerSeverity;

    const wasmModule = await loadPyreflyWasm();
    this.state = new wasmModule.State("3.12");
    this.state.updateSandboxFiles({ [FILENAME]: "" }, true);
    this.state.setActiveFile(FILENAME);
  }

  async updateCode(code: string): Promise<DiagnosticInfo[]> {
    if (!this.state) return [];

    this.state.updateSingleFile(FILENAME, code);
    this.state.setActiveFile(FILENAME);

    const errors = this.state.getErrors();
    return Array.from(errors).map((e) => ({
      startLineNumber: e.startLineNumber,
      startColumn: e.startColumn,
      endLineNumber: e.endLineNumber,
      endColumn: e.endColumn,
      message: e.message_details
        ? `${e.message_header}\n${e.message_details}`
        : e.message_header,
      severity: mapPyreflySeverity(e.severity),
      source: this.name,
      code: e.kind,
    }));
  }

  async getHover(
    lineNumber: number,
    column: number,
  ): Promise<HoverInfo | null> {
    if (!this.state) return null;

    // Pyrefly uses 1-based positions (same as Monaco)
    const result = this.state.hover(lineNumber, column);
    if (!result || !result.contents || result.contents.length === 0)
      return null;

    return {
      contents: result.contents.map((c) => c.value).join("\n\n"),
      range: result.range
        ? {
            startLineNumber: result.range.startLineNumber,
            startColumn: result.range.startColumn,
            endLineNumber: result.range.endLineNumber,
            endColumn: result.range.endColumn,
          }
        : undefined,
    };
  }

  dispose(): void {
    if (this.state?.free) {
      this.state.free();
    }
    this.state = null;
  }
}

function mapPyreflySeverity(
  severity: number,
): monaco.MarkerSeverity {
  // Pyrefly uses Monaco-compatible severity values directly
  switch (severity) {
    case 8:
      return MarkerSeverity.Error;
    case 4:
      return MarkerSeverity.Warning;
    case 2:
      return MarkerSeverity.Info;
    case 1:
      return MarkerSeverity.Hint;
    default:
      return MarkerSeverity.Error;
  }
}

async function loadPyreflyWasm(): Promise<PyreflyWasmModule> {
  // Try loading from local static assets (built by CI or fetch-wasm.sh)
  try {
    const baseUrl = new URL(/* @vite-ignore */ "../../wasm/pyrefly/", import.meta.url).href;
    const jsUrl = `${baseUrl}pyrefly_wasm.js`;

    const mod = (await import(/* @vite-ignore */ jsUrl)) as PyreflyWasmModule;
    await mod.default();
    return mod;
  } catch (e) {
    throw new Error(
      `Failed to load Pyrefly WASM. Run "npm run fetch-wasm" first. Error: ${e}`,
    );
  }
}
