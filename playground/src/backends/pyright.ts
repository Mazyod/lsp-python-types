import "remote-web-worker";
import {
  BrowserMessageReader,
  BrowserMessageWriter,
} from "vscode-jsonrpc/browser";
import {
  createMessageConnection,
  type MessageConnection,
  type Diagnostic,
  type PublishDiagnosticsParams,
} from "vscode-languageserver-protocol";
import { lspDiagnosticToInfo, lspHoverToInfo } from "../typeConversions";
import type { BackendAdapter, DiagnosticInfo, HoverInfo } from "./interface";

// We need access to monaco.MarkerSeverity at runtime, so we import it lazily
let MarkerSeverity: typeof import("monaco-editor").MarkerSeverity;

const PACKAGE = "browser-basedpyright";
const VERSION = "1.28.1";
const WORKER_URL = `https://cdn.jsdelivr.net/npm/${PACKAGE}@${VERSION}/dist/pyright.worker.js`;

const ROOT_PATH = "/src/";
const ROOT_URI = `file://${ROOT_PATH}`;
const FILE_NAME = "main.py";
const FILE_PATH = `${ROOT_PATH}${FILE_NAME}`;
const FILE_URI = `${ROOT_URI}${FILE_NAME}`;
const CONFIG_PATH = `${ROOT_PATH}pyrightconfig.json`;

const DEFAULT_CONFIG = JSON.stringify({
  typeshedPath: "/typeshed",
  pythonVersion: "3.12",
  typeCheckingMode: "standard",
});

export class PyrightBackend implements BackendAdapter {
  readonly name = "Pyright";
  private connection: MessageConnection | null = null;
  private workers: Worker[] = [];
  private version = 0;
  private latestDiagnostics: Diagnostic[] = [];
  private diagnosticsResolve: ((diags: Diagnostic[]) => void) | null = null;

  async initialize(): Promise<void> {
    const monaco = await import("monaco-editor");
    MarkerSeverity = monaco.MarkerSeverity;

    // Create foreground worker
    const foreground = new Worker(WORKER_URL, {
      name: "Pyright-foreground",
      type: "classic",
    });
    this.workers.push(foreground);

    // Boot foreground worker
    foreground.postMessage({
      type: "browser/boot",
      mode: "foreground",
    });

    // Handle background worker requests
    let bgCount = 0;
    foreground.addEventListener("message", (e: MessageEvent) => {
      if (e.data?.type === "browser/newWorker") {
        const { initialData, port } = e.data;
        const background = new Worker(WORKER_URL, {
          name: `Pyright-background-${++bgCount}`,
        });
        this.workers.push(background);
        background.postMessage(
          { type: "browser/boot", mode: "background", initialData, port },
          [port],
        );
      }
    });

    // Create LSP connection
    this.connection = createMessageConnection(
      new BrowserMessageReader(foreground),
      new BrowserMessageWriter(foreground),
    );

    // Listen for diagnostics push notifications
    this.connection.onNotification(
      "textDocument/publishDiagnostics",
      (params: PublishDiagnosticsParams) => {
        if (params.uri === FILE_URI) {
          this.latestDiagnostics = params.diagnostics;
          if (this.diagnosticsResolve) {
            this.diagnosticsResolve(params.diagnostics);
            this.diagnosticsResolve = null;
          }
        }
      },
    );

    // Handle workspace/configuration requests from the server
    this.connection.onRequest("workspace/configuration", () => {
      return [];
    });

    this.connection.listen();

    // LSP initialize handshake
    // Note: initializationOptions.files uses bare paths (not file:// URIs)
    await this.connection.sendRequest("initialize", {
      rootUri: ROOT_URI,
      rootPath: ROOT_PATH,
      processId: 1,
      capabilities: {
        textDocument: {
          publishDiagnostics: {
            tagSupport: { valueSet: [1, 2] },
            versionSupport: true,
          },
          hover: {
            contentFormat: ["markdown", "plaintext"],
          },
        },
      },
      initializationOptions: {
        files: {
          [FILE_PATH]: "",
          [CONFIG_PATH]: DEFAULT_CONFIG,
        },
      },
    });

    // Send initialized notification
    await this.connection.sendNotification("initialized", {});

    // Send didChangeConfiguration
    await this.connection.sendNotification(
      "workspace/didChangeConfiguration",
      { settings: {} },
    );
  }

  async updateCode(code: string): Promise<DiagnosticInfo[]> {
    if (!this.connection) return [];

    const version = ++this.version;

    // Create a promise that resolves when we get diagnostics back
    const diagnosticsPromise = new Promise<Diagnostic[]>((resolve) => {
      this.diagnosticsResolve = resolve;
      // Timeout after 10 seconds
      setTimeout(() => {
        if (this.diagnosticsResolve === resolve) {
          this.diagnosticsResolve = null;
          resolve(this.latestDiagnostics);
        }
      }, 10000);
    });

    // Send didOpen or didChange
    if (version === 1) {
      await this.connection.sendNotification("textDocument/didOpen", {
        textDocument: {
          uri: FILE_URI,
          languageId: "python",
          version,
          text: code,
        },
      });
    } else {
      await this.connection.sendNotification("textDocument/didChange", {
        textDocument: { uri: FILE_URI, version },
        contentChanges: [{ text: code }],
      });
    }

    const diagnostics = await diagnosticsPromise;

    // Stale check
    if (version !== this.version) return [];

    return diagnostics.map((d) =>
      lspDiagnosticToInfo(d, this.name, MarkerSeverity),
    );
  }

  async getHover(
    lineNumber: number,
    column: number,
  ): Promise<HoverInfo | null> {
    if (!this.connection) return null;

    try {
      const result = await this.connection.sendRequest("textDocument/hover", {
        textDocument: { uri: FILE_URI },
        position: {
          line: lineNumber - 1, // Monaco 1-based → LSP 0-based
          character: column - 1,
        },
      });
      return lspHoverToInfo(result as import("vscode-languageserver-protocol").Hover);
    } catch {
      return null;
    }
  }

  dispose(): void {
    if (this.connection) {
      this.connection.dispose();
      this.connection = null;
    }
    this.workers.forEach((w) => w.terminate());
    this.workers = [];
  }
}
