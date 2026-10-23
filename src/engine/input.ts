/* Touch for a toddler (docs/PLAN.md step 2):
 * - a touch acts when it goes down, not when it lifts;
 * - the first finger counts until it lifts; other fingers (a palm, a second
 *   hand) only get the sparkle, never an action;
 * - no browser zoom, scroll, text select or long-press menu.
 * Events wait in a queue and the next game step takes them, so input is
 * part of the fixed step (and the test driver can add its own). */

export type TouchKind = 'down' | 'move' | 'up' | 'extra';

export interface TouchEvt {
  kind: TouchKind;
  /** art pixels */
  x: number;
  y: number;
}

export class Input {
  private queue: TouchEvt[] = [];
  private primary: number | null = null;
  /** where the first finger is now, or null when no finger is down */
  held: { x: number; y: number } | null = null;

  /** Adds an event (from the browser or from the test driver). */
  push(e: TouchEvt): void {
    this.queue.push(e);
    if (e.kind === 'down' || e.kind === 'move') this.held = { x: e.x, y: e.y };
    if (e.kind === 'up') this.held = null;
  }

  /** The events since the last step. */
  take(): TouchEvt[] {
    const q = this.queue;
    this.queue = [];
    return q;
  }

  attach(el: HTMLElement, toArt: (cx: number, cy: number) => { x: number; y: number }, onAnyTouch: () => void): void {
    const at = (e: PointerEvent) => toArt(e.clientX, e.clientY);
    el.addEventListener('pointerdown', (e) => {
      e.preventDefault();
      onAnyTouch();
      const p = at(e);
      if (this.primary === null) {
        this.primary = e.pointerId;
        try {
          el.setPointerCapture(e.pointerId);
        } catch {
          /* a synthetic pointer cannot be captured */
        }
        this.push({ kind: 'down', ...p });
      } else this.push({ kind: 'extra', ...p });
    });
    el.addEventListener('pointermove', (e) => {
      if (e.pointerId === this.primary) this.push({ kind: 'move', ...at(e) });
    });
    const end = (e: PointerEvent) => {
      if (e.pointerId !== this.primary) return;
      this.primary = null;
      this.push({ kind: 'up', ...at(e) });
    };
    el.addEventListener('pointerup', end);
    el.addEventListener('pointercancel', end);
    el.addEventListener('lostpointercapture', end);
    /* iOS Safari: stop scroll, pinch and double-tap zoom, the long-press menu */
    const stop = (e: Event) => e.preventDefault();
    el.addEventListener('touchstart', stop, { passive: false });
    el.addEventListener('touchmove', stop, { passive: false });
    el.addEventListener('touchend', (e) => {
      onAnyTouch(); /* older iOS starts audio only from touchend */
      e.preventDefault();
    }, { passive: false });
    for (const name of ['gesturestart', 'gesturechange', 'dblclick', 'contextmenu', 'selectstart']) document.addEventListener(name, stop, { passive: false });
  }
}
