import type * as monaco from "monaco-editor";
import type {
  Diagnostic,
  Range as LspRange,
  Hover,
} from "vscode-languageserver-protocol";
import type { DiagnosticInfo, HoverInfo } from "./backends/interface";

/**
 * Convert LSP 0-based range to Monaco 1-based range.
 */
export function lspRangeToMonaco(range: LspRange): monaco.IRange {
  return {
    startLineNumber: range.start.line + 1,
    startColumn: range.start.character + 1,
    endLineNumber: range.end.line + 1,
    endColumn: range.end.character + 1,
  };
}

/**
 * Map LSP DiagnosticSeverity to Monaco MarkerSeverity.
 * LSP: 1=Error, 2=Warning, 3=Information, 4=Hint
 * Monaco: 8=Error, 4=Warning, 2=Info, 1=Hint
 */
export function lspSeverityToMonaco(
  severity: number | undefined,
  MarkerSeverity: typeof monaco.MarkerSeverity,
): monaco.MarkerSeverity {
  switch (severity) {
    case 1:
      return MarkerSeverity.Error;
    case 2:
      return MarkerSeverity.Warning;
    case 3:
      return MarkerSeverity.Info;
    case 4:
      return MarkerSeverity.Hint;
    default:
      return MarkerSeverity.Error;
  }
}

/**
 * Convert an LSP Diagnostic to a Monaco marker-compatible DiagnosticInfo.
 */
export function lspDiagnosticToInfo(
  diag: Diagnostic,
  source: string,
  MarkerSeverity: typeof monaco.MarkerSeverity,
): DiagnosticInfo {
  const range = lspRangeToMonaco(diag.range);
  return {
    ...range,
    message: diag.message,
    severity: lspSeverityToMonaco(diag.severity, MarkerSeverity),
    source,
    code:
      typeof diag.code === "number" ? String(diag.code) : diag.code ?? undefined,
  };
}

/**
 * Convert LSP Hover to HoverInfo.
 */
export function lspHoverToInfo(hover: Hover): HoverInfo | null {
  if (!hover || !hover.contents) return null;

  let contents: string;
  if (typeof hover.contents === "string") {
    contents = hover.contents;
  } else if ("value" in hover.contents) {
    // MarkupContent
    contents = hover.contents.value;
  } else if (Array.isArray(hover.contents)) {
    contents = hover.contents
      .map((c) => (typeof c === "string" ? c : c.value))
      .join("\n\n");
  } else {
    contents = String(hover.contents);
  }

  return {
    contents,
    range: hover.range ? lspRangeToMonaco(hover.range) : undefined,
  };
}
