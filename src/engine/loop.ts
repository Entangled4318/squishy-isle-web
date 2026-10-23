/* The game runs on a fixed 60 Hz step, whatever the screen's refresh rate
 * (60 Hz, 120 Hz ProMotion, or a slow frame). Drawing happens once per
 * browser frame. In test mode the driver runs steps itself, as fast as it
 * can, and the browser frame only draws. */

export const STEP_HZ = 60;
export const STEP_MS = 1000 / STEP_HZ;
/** At most this many steps per browser frame, like the GBA's 8 sound ticks:
 * after a long stall the game does not race to catch up. */
export const MAX_STEPS = 8;

export class Loop {
  private acc = 0;
  private last = -1;
  private raf = 0;
  /** false in test mode: only the driver runs steps. */
  auto = true;

  constructor(
    private step: () => void,
    private draw: () => void,
  ) {}

  start(): void {
    const tick = (t: number) => {
      this.raf = requestAnimationFrame(tick);
      if (this.auto) {
        if (this.last < 0) this.last = t;
        this.acc += Math.min(t - this.last, 250);
        this.last = t;
        let n = 0;
        while (this.acc >= STEP_MS && n < MAX_STEPS) {
          this.step();
          this.acc -= STEP_MS;
          n++;
        }
        if (n === MAX_STEPS) this.acc = 0;
      }
      this.draw();
    };
    this.raf = requestAnimationFrame(tick);
  }

  /** The app went to the background: no catch-up when it comes back. */
  pause(): void {
    this.last = -1;
    this.acc = 0;
  }

  stop(): void {
    cancelAnimationFrame(this.raf);
  }

  /** Test driver: run n steps now. */
  run(n: number): void {
    for (let i = 0; i < n; i++) this.step();
  }
}
