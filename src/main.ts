/* Entry point. ?test=1 is test mode: steps run only from the test driver
 * (window.__squishy), the log prints to the console, no install hint.
 * ?sw=1 registers the service worker in test mode too (offline test). */
import './style.css';
import { Game } from './game';
import { Screen } from './engine/screen';
import { logLines, setLogEcho } from './engine/log';
import { TapTest } from './scenes/taptest';
import { Gallery } from './scenes/gallery';
import { SoundTest } from './scenes/soundtest';
import { Title } from './scenes/title';
import { Meadow } from './scenes/meadow';
import { Open } from './scenes/open';
import { Closeup } from './scenes/closeup';
import { Shelf } from './scenes/shelf';
import { isIOS, showInstallHint } from './shell/install-hint';
import { standalone } from './scenes/taptest';
import { encodeSave } from './rules/save-data';
import { TouchKind } from './engine/input';
import { fixedLayout } from './engine/screen';
import { BUTTON_ROOM, buttonAt, BUTTON_D } from './scenes/button';

const params = new URLSearchParams(location.search);
const testMode = params.has('test');
setLogEcho(testMode);

const canvas = document.getElementById('game') as HTMLCanvasElement;
const screen = new Screen(canvas);
const game = new Game(screen, testMode);

if ('serviceWorker' in navigator && import.meta.env.PROD && (!testMode || params.has('sw')))
  navigator.serviceWorker.register('./sw.js', { scope: './' }).catch(() => {});

if ((!testMode && isIOS() && !standalone()) || params.has('hint')) showInstallHint(params.has('hint'));

declare global {
  interface Window {
    __squishy?: unknown;
  }
}

const meadow = new Meadow(game);
const reveal = new Closeup(game, () => meadow);
const shelf: Shelf = new Shelf(game, () => meadow, (id) => closeup.show(id, false));
const closeup = new Closeup(game, () => meadow, () => shelf);
meadow.shelfScene = () => {
  shelf.pick = false;
  return shelf;
};
meadow.pickScene = () => {
  shelf.pick = true;
  return shelf;
};
const open = new Open(game, () => meadow.open, () => reveal.show(meadow.open.friend, true), () => meadow);
meadow.openScene = () => open;
const title = (): Title => new Title(game, () => meadow, () => meadow.reset());
/* The game starts at the title (owner's choice after M4). The test pages:
 * ?taptest (device checklist 1), ?gallery, ?sound. */
const first = params.has('gallery')
  ? () => new Gallery(game)
  : params.has('sound')
    ? () => new SoundTest(game)
    : params.has('taptest')
      ? () => new TapTest(game)
      : title;

void game.boot(first).then(() => {
  if (!testMode) return;
  window.__squishy = {
    ready: true,
    run: (n: number) => game.loop.run(n),
    touch: (kind: TouchKind, x: number, y: number) => game.input.push({ kind, x, y }),
    log: () => [...logLines()],
    save: () => ({ ...game.collection.s, bytes: Array.from(encodeSave(game.collection.s)) }),
    view: () => ({ ...screen.view }),
    scene: () => game.scenes.current?.name,
    page: () => (game.scenes.current as Gallery | null)?.page,
    pages: () => (game.scenes.current as Gallery | null)?.pages?.map((p) => p.title),
    artLoaded: (path: string) => game.art.cached(path) !== undefined,
    fading: () => game.scenes.fading(),
    sparkles: () => game.sparkles.count(),
    storage: () => ({ ...game.chip.report }),
    flush: () => game.chip.flush(),
    sound: () => game.sound.state(),
    unlock: () => game.sound.unlock(),
    addFriend: (id: number) => game.collection.add(id),
    meadow: () => ({ pip: [meadow.pipX, meadow.pipY], cam: [meadow.camX, meadow.camY], area: meadow.A?.index }),
    placePip: (x: number, y: number) => meadow.place(x, y),
    goMeadow: () => game.scenes.go(meadow),
    walk: () => ({ path: meadow.path.length, dir: meadow.dir, walking: meadow.walkT > 0 }),
    blocked: (x: number, y: number) => meadow.blocked(x, y),
    boxes: () => meadow.boxes.map((b) => (b.spot < 0 ? null : meadow.A.spots[b.spot])),
    arrow: () => meadow.arrowBox,
    friends: () => ({
      pen: meadow.pen.map((r) => [r.x, r.y, r.id]),
      follow: meadow.followIds.map((id, k) => [meadow.followerPos(k).x, meadow.followerPos(k).y, id]),
    }),
    stage: () => ({ popT: open.popT, landed: reveal.landedT, squishes: reveal.squishes, leave: reveal.leaveT }),
    shelfPage: () => shelf.page,
    followers: () => [0, 1, 2].map((i) => game.collection.followerGet(i)),
    /** a backdrop pixel as view art pixels (room: the screen keeps room for the home button) */
    fixedToView: (x: number, y: number, room: boolean) => {
      const v = screen.view;
      const f = fixedLayout(v, 240, 160, room ? BUTTON_ROOM : 0);
      return [(x * f.k + f.ox - v.ox) / v.k, (y * f.k + f.oy - v.oy) / v.k];
    },
    button: () => {
      const b = buttonAt(game);
      return [b.x + BUTTON_D / 2, b.y + BUTTON_D / 2];
    },
  };
});
