import assert from "node:assert/strict";
// Keep Playwright outside the project's dependencies, e.g. install it under /tmp.
// Run against "npm run preview" with PLAYWRIGHT_MODULE=/absolute/path/to/playwright/index.mjs.
const { chromium } = await import(
  process.env.PLAYWRIGHT_MODULE || "playwright"
);
const browser = await chromium.launch({ headless: true });
const page = await browser.newPage();
const errors = [];
page.on("pageerror", (e) => errors.push(e.message));
page.on("console", (m) => {
  if (m.type() === "error") errors.push(m.text());
});
try {
  await page.goto("http://127.0.0.1:4173/lsp-python-types/");
  for (const name of [
    "basedpyright",
    "Pyrefly",
    "ty",
    "Pyrefly",
    "ty",
    "basedpyright",
  ]) {
    await page.getByRole("button", { name, exact: true }).click();
    await page.waitForFunction(
      (name) => document.querySelector("#status").textContent === name,
      name,
    );
    await page.locator(".view-lines").click({ position: { x: 90, y: 12 } });
    await page.keyboard.press("Control+KeyA");
    await page.keyboard.insertText('value: int = "wrong"\n');
    await page.waitForFunction(
      () => document.querySelectorAll(".squiggly-error").length === 1,
    );
    await page.keyboard.press("Control+Home");
    await page.keyboard.press("ArrowRight");
    await page.keyboard.press("Control+KeyK");
    await page.keyboard.press("Control+KeyI");
    await page.locator(".monaco-hover:visible").waitFor({ state: "visible" });
    assert.match(
      await page.locator(".monaco-hover:visible").innerText(),
      name === "ty" ? /Literal/ : /int/,
    );
    await page.keyboard.press("Escape");
    await page.keyboard.press("Control+KeyA");
    await page.keyboard.insertText("value: int = 42\n");
    await page.waitForFunction(
      () => document.querySelectorAll(".squiggly-error").length === 0,
    );
    console.log(`${name}: production markers, hover and clearing errors PASS`);
  }
  // Do not wait for initialization between selections: only the final choice may win.
  await page.evaluate(() => {
    for (const name of ["Pyrefly", "basedpyright", "ty"]) {
      document.querySelector(`button[data-backend="${name}"]`).click();
    }
  });
  await page.waitForFunction(
    () => document.querySelector("#status").textContent === "ty",
  );
  await page.waitForTimeout(1500);
  assert.equal(await page.locator("#status").textContent(), "ty");
  assert.equal(
    await page.locator("#backend-selector .active").textContent(),
    "ty",
  );
  console.log("Rapid backend selections preserve the final choice: PASS");
  assert.deepEqual(errors, []);
} finally {
  await browser.close();
}
