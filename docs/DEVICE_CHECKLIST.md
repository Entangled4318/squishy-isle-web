# Device checklist

The play tests run in Chromium. Safari on iPhone and iPad has its own
rules for sound, storage and the home screen, so these checks need a real
device. Each milestone adds a section. Write "ok" or what you saw next to
each item, or tell Claude in chat.

Address: https://entangled4318.github.io/squishy-isle-web/

## Checklist 1 (milestone 1: the tap test)

Do every step on one iPhone and one iPad. The panel at the bottom left of
the tap test shows most of the answers.

### In a Safari tab

1. Open the address in Safari. The parents' hint "play from the Home
   Screen" shows once, with three picture steps. Tap OK. It closes.
2. Reload. The hint does not show again.
3. Tap the screen once. You hear a soft tick and a chime, a sparkle shows
   where you tapped, and the count in the circle goes up to 1.
4. Panel: note what it says after "sound" (expected: running) and
   "session" (expected on iOS 17 or later: playback).
5. Turn the iPhone's silent switch on (or use Control Center on iPad), then
   tap. Note if you still hear the chime.
6. Tap with two fingers at once. The count goes up by 1, not 2. Both
   fingers sparkle.
7. Pinch, double-tap and long-press on the screen. Nothing zooms, no menu
   opens, no text is selected, the page does not scroll.
8. Reload. The count is the same. "boots" in the panel went up by 1.

### On the Home Screen

9. In Safari: Share, then Add to Home Screen. The icon is a pink bunny on a
   sky-to-pink tile, named "Squishy Isle".
10. Open it from the Home Screen. It fills the screen with no Safari bars.
    The panel says "home screen app".
11. Note the count in the circle. Expected: it starts again at 0, because a
    home screen app keeps its storage apart from Safari. (If it shows the
    Safari tab's count, tell Claude: that changes the export plan.)
12. Tap 5 times. Close the app fully (swipe it away in the app switcher).
    Open it again. The count is the same, and "boots" went up.
13. Panel: note "persist" (granted, refused or no API) and "used".
14. Turn the device to portrait and back. The dashed frame and the three
    round button spots stay inside the screen, clear of the notch, the
    Dynamic Island and the home bar, in both orientations.
15. With the app open, lock the screen, wait 10 seconds, unlock. Tap. The
    sound comes back on that tap.
16. Turn on Airplane Mode. Close the app fully and open it again. It opens
    and works offline.

### A week later (storage)

17. Leave the home screen app unopened for 8 or more days, then open it.
    Note if the count is still there.

## Checklist 2 (milestone 2: the art gallery)

Address: https://entangled4318.github.io/squishy-isle-web/?gallery

1. Page 1 shows the meadow with Pip. On the left, four friends at 16 px
   (the GBA size). On the right, four at 32 px. The rings show Apple's
   smallest touch target (44 points). Pick the size for the map: 16, 32,
   or "between" (24 px, which needs new face art).
2. Tap the right side of the screen to go through all 26 pages. Note any
   art that looks wrong, blurry or cut off on the device.

## Checklists 3 and later

Added at the end of milestones 3 to 7.
