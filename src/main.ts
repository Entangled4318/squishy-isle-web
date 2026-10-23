/* Entry point. ?test=1 is test mode: steps run only from the test driver
 * (window.__squishy), the log prints to the console, no install hint.
 * ?sw=1 registers the service worker in test mode too (offline test). */
import './style.css';
import { Game } from './game';
import { Screen } from './engine/screen';
import { logLines, setLogEcho } from './engine/log';
import { TapTest } from './scenes/taptest';
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

void game.boot(() => new TapTest(game)).then(() => {
  if (!testMode) return;
  window.__squishy = {
    ready: true,
    run: (n: number) => game.loop.run(n),
    touch: (kind: TouchKind, x: number, y: number) => game.input.push({ kind, x, y }),
    log: () => [...logLines()],
    save: () => ({ ...game.collection.s, bytes: Array.from(encodeSave(game.collection.s)) }),
    view: () => ({ ...screen.view }),
    scene: () => game.scenes.current?.name,
    fading: () => game.scenes.fading(),
    sparkles: () => game.sparkles.count(),
    storage: () => ({ ...game.chip.report }),
    flush: () => game.chip.flush(),
    sound: () => game.sound.state(),
  };
});
