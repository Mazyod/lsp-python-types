export type BackendName = "Pyright" | "Pyrefly" | "ty";

const ALL_BACKENDS: BackendName[] = ["Pyright", "Pyrefly", "ty"];

export interface UICallbacks {
  onBackendSelect: (name: BackendName) => void;
}

let currentBackend: BackendName = "Pyright";

export function initUI(callbacks: UICallbacks): void {
  const selector = document.getElementById("backend-selector")!;

  for (const name of ALL_BACKENDS) {
    const btn = document.createElement("button");
    btn.textContent = name;
    btn.dataset.backend = name;
    if (name === currentBackend) btn.classList.add("active");
    btn.addEventListener("click", () => {
      if (name === currentBackend) return;
      selectBackend(name);
      callbacks.onBackendSelect(name);
    });
    selector.appendChild(btn);
  }
}

export function selectBackend(name: BackendName): void {
  currentBackend = name;
  const buttons = document.querySelectorAll("#backend-selector button");
  buttons.forEach((btn) => {
    const el = btn as HTMLButtonElement;
    el.classList.toggle("active", el.dataset.backend === name);
  });
}

export function setStatus(
  text: string,
  state: "loading" | "ready" | "error" = "loading",
): void {
  const el = document.getElementById("status")!;
  el.textContent = text;
  el.className = state;
}

export function setBackendDisabled(name: BackendName, disabled: boolean): void {
  const btn = document.querySelector(
    `#backend-selector button[data-backend="${name}"]`,
  ) as HTMLButtonElement | null;
  if (btn) btn.disabled = disabled;
}
