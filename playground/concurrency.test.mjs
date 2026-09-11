import assert from "node:assert/strict";
// Run against "npm run dev"; use the same external Playwright module as browser.test.mjs.
const { chromium } = await import(
  process.env.PLAYWRIGHT_MODULE || "playwright"
);
const browser = await chromium.launch({ headless: true });
try {
  const page = await browser.newPage();
  await page.goto("http://127.0.0.1:5173/lsp-python-types/");
  await page.waitForFunction(
    () => document.querySelector("#status").textContent === "basedpyright",
  );
  const snapshots = await page.evaluate(async () => {
    const mainSource = await (await fetch("/lsp-python-types/src/main.ts")).text();
    const editorUrl = mainSource.match(/from "([^"]*\/editor\.ts[^"]*)"/)[1];
    const { setAdapter } = await import(editorUrl);
    // Import Vite's exact bundled Monaco instance, including its cache query.
    const editorSource = await (await fetch(editorUrl)).text();
    const monaco = await import(
      editorSource.match(/import \* as monaco from "([^"]+)"/)[1]
    );
    const model = monaco.editor.getModels()[0];
    const nextTurn = () => new Promise((resolve) => setTimeout(resolve, 0));
    const pending = [];
    const adapter = (name) => ({
      name,
      updateCode: () => new Promise((resolve) => pending.push(resolve)),
      getHover: async () => null,
      dispose() {},
    });
    const diagnostic = (message) => [
      {
        startLineNumber: 1,
        startColumn: 1,
        endLineNumber: 1,
        endColumn: 2,
        message,
        severity: 8,
      },
    ];
    const markers = () =>
      monaco.editor
        .getModelMarkers({ resource: model.uri })
        .map((marker) => ({ owner: marker.owner, message: marker.message }));
    setAdapter(adapter("first"));
    model.setValue("value: int = 42\n");
    pending.shift()(diagnostic("before edit"));
    await nextTurn();
    const duringDebounce = markers();
    setAdapter(adapter("old"));
    const finishOld = pending.shift();
    setAdapter(adapter("new"));
    pending.shift()(diagnostic("new result"));
    await nextTurn();
    finishOld(diagnostic("old result"));
    await nextTurn();
    const afterSwitch = markers();
    setAdapter(adapter("detached"));
    setAdapter(null);
    pending.shift()(diagnostic("after disposal"));
    await nextTurn();
    return { duringDebounce, afterSwitch, afterDetach: markers() };
  });
  assert.deepEqual(snapshots, {
    duringDebounce: [],
    afterSwitch: [{ owner: "new", message: "new result" }],
    afterDetach: [],
  });
  console.log(
    "Editor ignores results during debounce, after switching, and after detaching: PASS",
  );

  const diagnostics = await page.evaluate(async () => {
    const { PyrightBackend } =
      await import("/lsp-python-types/src/backends/pyright.ts");
    const adapter = new PyrightBackend();
    await adapter.initialize();
    // Control the real transport's incoming publications without asking the server to analyze.
    adapter.connection.sendNotification = async () => {};
    const publish = (version, message) =>
      adapter.workers[0].dispatchEvent(
        new MessageEvent("message", {
          data: {
            jsonrpc: "2.0",
            method: "textDocument/publishDiagnostics",
            params: {
              uri: "file:///src/main.py",
              version,
              diagnostics: [
                {
                  range: {
                    start: { line: 0, character: 0 },
                    end: { line: 0, character: 1 },
                  },
                  message,
                  severity: 1,
                },
              ],
            },
          },
        }),
      );
    try {
      const first = adapter.updateCode("first");
      let secondFinished = false;
      const second = adapter.updateCode("second").then((result) => {
        secondFinished = true;
        return result;
      });
      publish(1, "stale");
      await new Promise((resolve) => setTimeout(resolve, 0));
      const ignoredOldVersion = !secondFinished;
      publish(2, "current");
      const results = {
        first: await first,
        second: (await second).map((item) => item.message),
        ignoredOldVersion,
      };
      const originalTimeout = window.setTimeout;
      window.setTimeout = (callback, delay, ...args) =>
        originalTimeout(callback, delay === 10000 ? 0 : delay, ...args);
      try {
        results.timedOut = await adapter.updateCode("no response");
      } finally {
        window.setTimeout = originalTimeout;
      }
      const disposed = adapter.updateCode("disposed");
      adapter.dispose();
      results.disposed = await disposed;
      return results;
    } finally {
      adapter.dispose();
    }
  });
  assert.deepEqual(diagnostics, {
    first: [],
    second: ["current"],
    ignoredOldVersion: true,
    timedOut: [],
    disposed: [],
  });
  console.log(
    "basedpyright ignores stale versions and settles superseded, timed-out and disposed requests: PASS",
  );
} finally {
  await browser.close();
}
