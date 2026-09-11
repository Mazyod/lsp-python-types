import assert from "node:assert/strict";
import { readFile } from "node:fs/promises";
import test from "node:test";

const invalid = 'value: int = "wrong"\n';
const valid = "value: int = 42\n";

async function load(name) {
  const module = await import(`./wasm/${name}/${name}_wasm.js`);
  await module.default({
    module_or_path: await readFile(
      new URL(`./wasm/${name}/${name}_wasm_bg.wasm`, import.meta.url),
    ),
  });
  return module;
}

test("Pyrefly release WASM diagnoses edits and supplies hover", async () => {
  const { State } = await load("pyrefly");
  const state = new State("3.12");
  try {
    state.updateSandboxFiles({ "main.py": "" }, true);
    state.setActiveFile("main.py");
    state.updateSingleFile("main.py", invalid);
    const errors = state.getErrors();
    assert.ok(
      errors.some(
        (error) => error.startLineNumber === 1 && error.severity === 8,
      ),
    );
    assert.match(JSON.stringify(state.hover(1, 2)), /int/);
    state.updateSingleFile("main.py", valid);
    assert.equal(state.getErrors().length, 0);
  } finally {
    state.free();
  }
});

test("ty release WASM diagnoses edits and supplies 1-based hover", async () => {
  const { Workspace, Position, PositionEncoding } = await load("ty");
  const workspace = new Workspace("/", PositionEncoding.Utf16, {
    environment: { "python-version": "3.12" },
  });
  const file = workspace.openFile("main.py", "");
  try {
    workspace.updateFile(file, invalid);
    const diagnostics = workspace.checkFile(file);
    assert.ok(diagnostics.some((diagnostic) => diagnostic.severity() === 2));
    const range = diagnostics[0].toRange(workspace);
    assert.equal(range.start.line, 1);
    assert.ok(range.start.column >= 1);
    for (const diagnostic of diagnostics) diagnostic.free();
    const hover = workspace.hover(file, new Position(1, 2));
    assert.match(hover.markdown, /Literal\["wrong"\]/);
    assert.equal(hover.range.start.line, 1);
    workspace.updateFile(file, valid);
    assert.equal(workspace.checkFile(file).length, 0);
  } finally {
    workspace.closeFile(file);
    workspace.free();
  }
});
