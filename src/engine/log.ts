/* The game log, the same idea as the GBA game's dbg(): short lines that the
 * tests read. Each line starts with the frame number. */

let frame = 0;
const lines: string[] = [];
const MAX_LINES = 20000;
let echo = false;

export function setLogFrame(f: number): void {
  frame = f;
}

/** Test mode also prints each line to the console. */
export function setLogEcho(on: boolean): void {
  echo = on;
}

export function dbg(msg: string): void {
  const line = `f${frame} ${msg}`;
  lines.push(line);
  if (lines.length > MAX_LINES) lines.splice(0, lines.length - MAX_LINES);
  if (echo) console.log(line);
}

export function logLines(): readonly string[] {
  return lines;
}
