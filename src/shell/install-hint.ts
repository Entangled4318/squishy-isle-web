/* A one-time hint for parents in a Safari tab: Share, then Add to Home
 * Screen. The home screen app is the full-screen mode on iPhone, keeps its
 * own storage, and is exempt from Safari's 7-day storage cap. The game still
 * works in the tab. Pictures carry the steps; the words are for the parent. */
import { prefs } from './storage';

export function isIOS(): boolean {
  const ua = navigator.userAgent;
  return /iPad|iPhone|iPod/.test(ua) || (navigator.platform === 'MacIntel' && navigator.maxTouchPoints > 1);
}

const SHARE_ICON =
  '<svg viewBox="0 0 24 24" width="28" height="28" aria-hidden="true"><path d="M12 3v12M7 8l5-5 5 5" fill="none" stroke="#2f7cf6" stroke-width="2" stroke-linecap="round" stroke-linejoin="round"/><path d="M6 11v9h12v-9" fill="none" stroke="#2f7cf6" stroke-width="2" stroke-linejoin="round"/></svg>';
const ADD_ICON =
  '<svg viewBox="0 0 24 24" width="28" height="28" aria-hidden="true"><rect x="3" y="3" width="18" height="18" rx="4" fill="none" stroke="#333" stroke-width="2"/><path d="M12 8v8M8 12h8" stroke="#333" stroke-width="2" stroke-linecap="round"/></svg>';

export function showInstallHint(force = false): void {
  if (!force && prefs.get('install-hint') === 'seen') return;
  const box = document.createElement('div');
  box.id = 'install-hint';
  box.innerHTML = `
    <div class="card" role="dialog" aria-label="Add Squishy Isle to the Home Screen">
      <p class="title">For grown-ups: play from the Home Screen</p>
      <ol>
        <li><span class="icon">${SHARE_ICON}</span><span>Tap <b>Share</b> in Safari</span></li>
        <li><span class="icon">${ADD_ICON}</span><span>Tap <b>Add to Home Screen</b></span></li>
        <li><span class="icon">🐰</span><span>Open <b>Squishy Isle</b> from the Home Screen</span></li>
      </ol>
      <p class="small">The Home Screen app fills the screen and keeps the save safest. Install it before your child plays: a save made in this tab does not move to the app by itself.</p>
      <button type="button">OK</button>
    </div>`;
  document.body.appendChild(box);
  const close = (e: Event) => {
    e.stopPropagation();
    prefs.set('install-hint', 'seen');
    box.remove();
  };
  box.querySelector('button')!.addEventListener('click', close);
}
