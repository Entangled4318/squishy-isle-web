/* Small helpers that keep ported GBA code exact: the 64-step sine table
 * (tables.c) and C integer division, which truncates toward zero. */

const SIN64 = [
  0, 25, 50, 74, 98, 121, 142, 162, 181, 198, 213, 226, 237, 245, 251, 255, 256, 255, 251, 245, 237, 226, 213, 198, 181, 162, 142,
  121, 98, 74, 50, 25, 0, -25, -50, -74, -98, -121, -142, -162, -181, -198, -213, -226, -237, -245, -251, -255, -256, -255, -251,
  -245, -237, -226, -213, -198, -181, -162, -142, -121, -98, -74, -50, -25,
];

/** sin64[i & 63]: -256..256, one full turn in 64 steps. */
export const isin = (i: number): number => SIN64[i & 63];

/** a / b as C does it on ints. */
export const idiv = (a: number, b: number): number => Math.trunc(a / b);
