import type * as monaco from "monaco-editor";

export interface DiagnosticInfo {
  startLineNumber: number;
  startColumn: number;
  endLineNumber: number;
  endColumn: number;
  message: string;
  severity: monaco.MarkerSeverity;
  source: string;
  code?: string;
}

export interface HoverInfo {
  contents: string;
  range?: monaco.IRange;
}

export interface BackendAdapter {
  readonly name: string;
  initialize(): Promise<void>;
  updateCode(code: string): Promise<DiagnosticInfo[]>;
  getHover(
    lineNumber: number,
    column: number,
  ): Promise<HoverInfo | null>;
  dispose(): void;
}
