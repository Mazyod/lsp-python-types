import type * as monaco from "monaco-editor";
import type { BackendAdapter, DiagnosticInfo, HoverInfo } from "./interface";

// ty WASM API types (from crates/ty_wasm/src/lib.rs)
interface TyPosition {
  line: number;
  column: number;
}

interface TyRange {
  start: TyPosition;
  end: TyPosition;
}

interface TyDiagnostic {
  id(): string;
  message(): string;
  severity(): number; // 0=Info, 1=Warning, 2=Error, 3=Fatal
  toRange(workspace: TyWorkspace): TyRange | null;
  free?(): void;
}

interface TyHover {
  markdown: string;
  range: TyRange;
}

interface TyFileHandle {
  free?(): void;
}

interface TyWorkspace {
  openFile(path: string, contents: string): TyFileHandle;
  updateFile(fileId: TyFileHandle, contents: string): void;
  closeFile(fileId: TyFileHandle): void;
  checkFile(fileId: TyFileHandle): TyDiagnostic[];
  hover(fileId: TyFileHandle, position: TyPositionClass): TyHover | undefined;
  free?(): void;
}

// The Position class constructor from ty_wasm
type TyPositionClass = TyPosition;

interface TyWasmModule {
  default(): Promise<void>;
  initLogging(level: number): void;
  Workspace: new (
    root: string,
    encoding: number,
    options: Record<string, unknown>,
  ) => TyWorkspace;
  Position: new (line: number, column: number) => TyPositionClass;
  PositionEncoding: { Utf16: number };
  LogLevel: { Info: number };
}

let MarkerSeverity: typeof import("monaco-editor").MarkerSeverity;

const FILENAME = "main.py";

export class TyBackend implements BackendAdapter {
  readonly name = "ty";
  private workspace: TyWorkspace | null = null;
  private fileHandle: TyFileHandle | null = null;
  private tyModule: TyWasmModule | null = null;

  async initialize(): Promise<void> {
    const monaco = await import("monaco-editor");
    MarkerSeverity = monaco.MarkerSeverity;

    this.tyModule = await loadTyWasm();

    this.workspace = new this.tyModule.Workspace(
      "/",
      this.tyModule.PositionEncoding.Utf16,
      {},
    );
    this.fileHandle = this.workspace.openFile(FILENAME, "");
  }

  async updateCode(code: string): Promise<DiagnosticInfo[]> {
    if (!this.workspace || !this.fileHandle) return [];

    this.workspace.updateFile(this.fileHandle, code);
    const diagnostics = this.workspace.checkFile(this.fileHandle);

    return diagnostics.map((d) => {
      const range = d.toRange(this.workspace!);
      return {
        // ty uses 0-based positions; Monaco uses 1-based — but ty's playground
        // shows range.start.line is already 1-based from toRange()
        startLineNumber: range?.start.line ?? 1,
        startColumn: range?.start.column ?? 1,
        endLineNumber: range?.end.line ?? 1,
        endColumn: range?.end.column ?? 1,
        message: d.message(),
        severity: mapTySeverity(d.severity()),
        source: this.name,
        code: d.id(),
      };
    });
  }

  async getHover(
    lineNumber: number,
    column: number,
  ): Promise<HoverInfo | null> {
    if (!this.workspace || !this.fileHandle || !this.tyModule) return null;

    try {
      const position = new this.tyModule.Position(lineNumber, column);
      const hover = this.workspace.hover(this.fileHandle, position);
      if (!hover) return null;

      return {
        contents: hover.markdown,
        range: {
          startLineNumber: hover.range.start.line,
          startColumn: hover.range.start.column,
          endLineNumber: hover.range.end.line,
          endColumn: hover.range.end.column,
        },
      };
    } catch {
      return null;
    }
  }

  dispose(): void {
    if (this.fileHandle?.free) this.fileHandle.free();
    if (this.workspace?.free) this.workspace.free();
    this.fileHandle = null;
    this.workspace = null;
    this.tyModule = null;
  }
}

function mapTySeverity(severity: number): monaco.MarkerSeverity {
  // ty Severity: 0=Info, 1=Warning, 2=Error, 3=Fatal
  switch (severity) {
    case 0:
      return MarkerSeverity.Info;
    case 1:
      return MarkerSeverity.Warning;
    case 2:
      return MarkerSeverity.Error;
    case 3:
      return MarkerSeverity.Error;
    default:
      return MarkerSeverity.Error;
  }
}

async function loadTyWasm(): Promise<TyWasmModule> {
  try {
    const baseUrl = new URL(/* @vite-ignore */ "../../wasm/ty/", import.meta.url).href;
    const jsUrl = `${baseUrl}ty_wasm.js`;

    const mod = (await import(/* @vite-ignore */ jsUrl)) as TyWasmModule;
    await mod.default();
    try {
      mod.initLogging(mod.LogLevel.Info);
    } catch {
      // initLogging may fail if already initialized
    }
    return mod;
  } catch (e) {
    throw new Error(
      `Failed to load ty WASM. Run "npm run fetch-wasm" first. Error: ${e}`,
    );
  }
}
