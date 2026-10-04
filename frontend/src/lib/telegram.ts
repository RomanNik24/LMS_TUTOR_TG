/** Работа с Telegram WebApp: initData, тема, кнопки. */

let initialInitData: string | null = null;

function readInitDataFromHash(): string | null {
  try {
    const params = new URLSearchParams(window.location.hash.slice(1));
    return params.get("tgWebAppData");
  } catch {
    return null;
  }
}

// Capture initData immediately on module load
if (typeof window !== "undefined") {
  initialInitData = readInitDataFromHash();
}

export function getInitData(): string | null {
  return initialInitData;
}

export function isTelegramMiniApp(): boolean {
  return initialInitData !== null && initialInitData.length > 0;
}

// Telegram theme colors (CSS variables will be applied by SDK)
export function applyTelegramTheme(): void {
  if (typeof window === "undefined") return;
  // SDK applies theme automatically via CSS variables
  // We just ensure our root element has the right class
  const tg = (window as any).Telegram?.WebApp;
  if (tg?.colorScheme) {
    document.documentElement.classList.toggle("dark", tg.colorScheme === "dark");
  }
}

export function setupTelegramBackButton(onBack: () => void): void {
  const tg = (window as any).Telegram?.WebApp;
  if (tg?.BackButton) {
    tg.BackButton.show();
    tg.BackButton.onClick(onBack);
  }
}

export function hideTelegramBackButton(): void {
  const tg = (window as any).Telegram?.WebApp;
  if (tg?.BackButton) {
    tg.BackButton.hide();
  }
}

export function setupTelegramMainButton(text: string, onClick: () => void): void {
  const tg = (window as any).Telegram?.WebApp;
  if (tg?.MainButton) {
    tg.MainButton.setText(text);
    tg.MainButton.show();
    tg.MainButton.onClick(onClick);
  }
}

export function hideTelegramMainButton(): void {
  const tg = (window as any).Telegram?.WebApp;
  if (tg?.MainButton) {
    tg.MainButton.hide();
  }
}

export function readyTelegram(): void {
  const tg = (window as any).Telegram?.WebApp;
  if (tg?.ready) {
    tg.ready();
  }
}

export function expandTelegram(): void {
  const tg = (window as any).Telegram?.WebApp;
  if (tg?.expand) {
    tg.expand();
  }
}