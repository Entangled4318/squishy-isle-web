/* The screen in "art pixels", the GBA game's pixel size. The canvas has one
 * pixel per device pixel, and each art pixel is a whole number of device
 * pixels (k), so the pixel art stays sharp. The view always shows at least
 * 240 x 160 art pixels (the GBA screen) in landscape, or 160 x 240 in
 * portrait; the map shows more of the island in the long direction. */

export const MIN_LONG = 240;
export const MIN_SHORT = 160;

export interface Insets {
  top: number;
  right: number;
  bottom: number;
  left: number;
}

export interface View {
  /** device pixels per art pixel */
  k: number;
  /** view size in art pixels */
  w: number;
  h: number;
  /** device-pixel offset of art pixel (0, 0): the leftover is split evenly */
  ox: number;
  oy: number;
  /** canvas size in device pixels */
  devW: number;
  devH: number;
  dpr: number;
  portrait: boolean;
  /** safe-area insets in art pixels (notch, Dynamic Island, home bar) */
  safe: Insets;
}

/** The largest whole-number scale that fits a w x h box in the view. */
export function fitScale(devW: number, devH: number, w: number, h: number): number {
  return Math.max(1, Math.min(Math.floor(devW / w), Math.floor(devH / h)));
}

export function computeView(cssW: number, cssH: number, dpr: number, safeCss: Insets): View {
  const devW = Math.max(1, Math.round(cssW * dpr));
  const devH = Math.max(1, Math.round(cssH * dpr));
  const portrait = devH > devW;
  const k = portrait ? fitScale(devW, devH, MIN_SHORT, MIN_LONG) : fitScale(devW, devH, MIN_LONG, MIN_SHORT);
  const w = Math.floor(devW / k);
  const h = Math.floor(devH / k);
  const toArt = (css: number) => Math.ceil((css * dpr) / k);
  return {
    k,
    w,
    h,
    ox: Math.floor((devW - w * k) / 2),
    oy: Math.floor((devH - h * k) / 2),
    devW,
    devH,
    dpr,
    portrait,
    safe: { top: toArt(safeCss.top), right: toArt(safeCss.right), bottom: toArt(safeCss.bottom), left: toArt(safeCss.left) },
  };
}

/** Reads env(safe-area-inset-*) through a hidden element. */
function readSafeArea(probe: HTMLElement): Insets {
  const cs = getComputedStyle(probe);
  const px = (v: string) => parseFloat(v) || 0;
  return { top: px(cs.paddingTop), right: px(cs.paddingRight), bottom: px(cs.paddingBottom), left: px(cs.paddingLeft) };
}

export class Screen {
  view!: View;
  readonly ctx: CanvasRenderingContext2D;
  private probe: HTMLElement;
  private listeners: Array<(v: View) => void> = [];

  constructor(public canvas: HTMLCanvasElement) {
    const ctx = canvas.getContext('2d', { alpha: false });
    if (!ctx) throw new Error('no 2D canvas');
    this.ctx = ctx;
    this.probe = document.createElement('div');
    this.probe.style.cssText =
      'position:fixed;inset:0;visibility:hidden;pointer-events:none;' +
      'padding:env(safe-area-inset-top) env(safe-area-inset-right) env(safe-area-inset-bottom) env(safe-area-inset-left)';
    document.body.appendChild(this.probe);
    this.resize();
    const again = () => this.resize();
    window.addEventListener('resize', again);
    window.addEventListener('orientationchange', () => setTimeout(again, 50));
    window.visualViewport?.addEventListener('resize', again);
  }

  onResize(f: (v: View) => void): void {
    this.listeners.push(f);
  }

  resize(): void {
    const cssW = window.innerWidth;
    const cssH = window.innerHeight;
    const v = computeView(cssW, cssH, window.devicePixelRatio || 1, readSafeArea(this.probe));
    const changed = !this.view || v.devW !== this.view.devW || v.devH !== this.view.devH || v.k !== this.view.k;
    this.view = v;
    if (this.canvas.width !== v.devW) this.canvas.width = v.devW;
    if (this.canvas.height !== v.devH) this.canvas.height = v.devH;
    this.canvas.style.width = `${cssW}px`;
    this.canvas.style.height = `${cssH}px`;
    this.ctx.imageSmoothingEnabled = false;
    if (changed) this.listeners.forEach((f) => f(v));
  }

  /** Client (CSS) coordinates to art pixels. */
  toArt(clientX: number, clientY: number): { x: number; y: number } {
    const r = this.canvas.getBoundingClientRect();
    const v = this.view;
    return {
      x: (((clientX - r.left) * v.devW) / r.width - v.ox) / v.k,
      y: (((clientY - r.top) * v.devH) / r.height - v.oy) / v.k,
    };
  }

  /** Sets the canvas transform so drawing is in art pixels. */
  artTransform(): void {
    const v = this.view;
    this.ctx.setTransform(v.k, 0, 0, v.k, v.ox, v.oy);
    this.ctx.imageSmoothingEnabled = false;
  }
}
