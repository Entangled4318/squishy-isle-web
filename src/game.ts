/* The game object: screen, touch, sound, scenes, the save, and the fixed
 * step. Boot loads the save the way the GBA game's collection_init() does. */
import { Collection } from './rules/collection';
import { SaveStatus, SaveStore } from './rules/save-store';
import { Input, TouchEvt } from './engine/input';
import { Loop } from './engine/loop';
import { dbg, setLogFrame } from './engine/log';
import { Scene, Scenes } from './engine/scenes';
import { Screen } from './engine/screen';
import { Sound } from './engine/audio';
import { Sparkles } from './engine/sparkles';
import { BrowserChip } from './shell/storage';
import { Art } from './engine/art';
import type { SongData } from './audio/engine';

export const BUILD = __BUILD__;

/** The 8 songs from tools/music.py, in their index order. */
async function loadSongs(): Promise<SongData[]> {
  const r = await fetch('./gen/music.json');
  const all = (await r.json()) as Record<string, SongData>;
  return Object.values(all).sort((a, b) => a.index - b.index);
}

export class Game {
  frame = 0;
  readonly input = new Input();
  readonly sound = new Sound();
  readonly scenes = new Scenes();
  readonly sparkles = new Sparkles();
  readonly art = new Art();
  readonly collection = new Collection(() => this.writeSave());
  store!: SaveStore;
  chip!: BrowserChip;
  loadStatus: SaveStatus = SaveStatus.New;
  readonly loop: Loop;
  /** called on every touch, before the step that handles it */
  onTouch: (e: TouchEvt) => void = () => {};

  constructor(
    readonly screen: Screen,
    readonly testMode: boolean,
  ) {
    this.loop = new Loop(
      () => this.step(),
      () => this.draw(),
    );
    this.loop.auto = !testMode;
  }

  async boot(first: () => Scene): Promise<void> {
    const [chip, songs] = await Promise.all([BrowserChip.open(), loadSongs(), this.art.load()]);
    this.chip = chip;
    this.sound.setSongs(songs);
    this.store = new SaveStore(this.chip);
    const c = this.collection;
    const { status, data } = this.store.load();
    this.loadStatus = status;
    c.s = data;
    c.sanitize();
    c.s.boots = (c.s.boots + 1) & 0xffff;
    if (c.s.mailNew && !c.s.letters[0] && c.s.mail) c.s.letters[0] = c.s.mail; /* before GBA 8.2: one unread letter */
    c.linesMerge();
    dbg(`save: ${status} v2 boots=${c.s.boots} found=${c.foundTotal()} opens=${c.s.opens}`);
    c.save();
    this.input.attach(this.screen.canvas, (x, y) => this.screen.toArt(x, y), () => this.sound.unlock());
    document.addEventListener('visibilitychange', () => {
      if (document.hidden) {
        this.sound.suspend();
        this.loop.pause();
        dbg('app hidden');
      } else {
        this.sound.resume();
        dbg('app shown');
      }
    });
    window.addEventListener('pagehide', () => dbg('page hide'));
    this.scenes.start(first());
    this.loop.start();
  }

  private writeSave(): boolean {
    const ok = this.store.store(this.collection.s);
    if (!ok) dbg('save: write FAILED');
    return ok;
  }

  step(): void {
    this.frame++;
    setLogFrame(this.frame);
    const touches = this.input.take();
    for (const t of touches) {
      this.sparkles.add(t);
      if (t.kind === 'down' || t.kind === 'extra') this.sound.tick();
      this.onTouch(t);
    }
    this.scenes.step(touches.filter((t) => t.kind !== 'extra'));
    this.sparkles.step();
  }

  draw(): void {
    const ctx = this.screen.ctx;
    const v = this.screen.view;
    ctx.setTransform(1, 0, 0, 1, 0, 0);
    ctx.fillStyle = '#fbe9f2';
    ctx.fillRect(0, 0, v.devW, v.devH);
    this.screen.artTransform();
    this.scenes.draw(ctx, v.w, v.h);
    this.sparkles.draw(ctx);
  }
}
