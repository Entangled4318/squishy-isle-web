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
import { isIOS, showInstallHint } from './shell/install-hint';
import { standalone } from './scenes/taptest';
import { encodeSave } from './rules/save-data';
import { TouchKind } from './engine/input';

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
const closeup = new Closeup(game, () => meadow);
const open = new Open(game, () => meadow.open, () => closeup.show(meadow.open.friend, true), () => meadow);
meadow.openScene = () => open;
const title = (): Title => new Title(game, () => meadow, () => meadow.reset());
/* ?title is the game (M4). The tap test stays the default page until the
 * owner has done device checklist 1 and agrees to the switch. */
const first = params.has('gallery')
  ? () => new Gallery(game)
  : params.has('sound')
    ? () => new SoundTest(game)
    : params.has('title')
      ? title
      : () => new TapTest(game);

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
    stage: () => ({ popT: open.popT, landed: closeup.landedT, squishes: closeup.squishes, leave: closeup.leaveT }),
  };
});
