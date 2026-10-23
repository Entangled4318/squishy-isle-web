/* Loads the art that tools/export_web.py writes (public/gen): atlas pages,
 * screens, maps and art.json, and draws sprites by name. */

export interface AreaData {
  index: number;
  name: string;
  w: number;
  h: number;
  ground: string;
  overlay: string;
  glint: string;
  glintCycle: string[];
  cell: number;
  cols: number;
  rows: number;
  solid: string;
  spawn: [number, number];
  spots: [number, number][];
  firstSpot: number;
  pen: [number, number, number, number] | null;
  sign: [number, number] | null;
  signs: [number, number, number, number][];
  doors: [number, number, number, number][];
  exits: [number, number, number, number, number, number, number][];
  gates: [number, number, number, number, number][];
  mailbox: [number, number] | null;
  basket: [number, number] | null;
  momo: [number, number] | null;
}

export interface ArtIndex {
  atlases: string[];
  sprites: Record<string, [number, number, number, number, number]>;
  screens: Record<string, string>;
  maps: AreaData[];
  logo: { sprite: string; x: number; y: number }[];
  font: { height: number; descent: number; spacing: number; glyphs: Record<string, string[]> };
  names: {
    areas: { key: string; name: string; container: string; species: string[] }[];
    species: Record<string, string>;
    flavors: string[];
    flavorNames: string[];
    snacks: string[];
    containerColors: Record<string, string[]>;
  };
  layout: Record<string, unknown>;
}

function loadImage(url: string): Promise<HTMLImageElement> {
  return new Promise((resolve, reject) => {
    const img = new Image();
    img.onload = () => resolve(img);
    img.onerror = () => reject(new Error(`art: cannot load ${url}`));
    img.src = url;
  });
}

export class Art {
  index!: ArtIndex;
  private atlases: HTMLImageElement[] = [];
  private images = new Map<string, HTMLImageElement>();

  constructor(private base = './gen/') {}

  async load(extra: string[] = []): Promise<void> {
    const r = await fetch(`${this.base}art.json`);
    if (!r.ok) throw new Error(`art: art.json ${r.status}`);
    this.index = (await r.json()) as ArtIndex;
    this.atlases = await Promise.all(this.index.atlases.map((f) => loadImage(this.base + f)));
    await Promise.all(extra.map((f) => this.image(f)));
  }

  /** A screen or map image by its path in art.json (loaded once). */
  async image(path: string): Promise<HTMLImageElement> {
    let img = this.images.get(path);
    if (!img) {
      img = await loadImage(this.base + path);
      this.images.set(path, img);
    }
    return img;
  }

  cached(path: string): HTMLImageElement | undefined {
    return this.images.get(path);
  }

  has(name: string): boolean {
    return name in this.index.sprites;
  }

  size(name: string): { w: number; h: number } {
    const s = this.index.sprites[name];
    if (!s) throw new Error(`art: no sprite ${name}`);
    return { w: s[3], h: s[4] };
  }

  /** Draws a sprite with its top-left at (x, y), optionally flipped and scaled. */
  draw(ctx: CanvasRenderingContext2D, name: string, x: number, y: number, opts: { flipX?: boolean; sx?: number; sy?: number } = {}): void {
    const s = this.index.sprites[name];
    if (!s) throw new Error(`art: no sprite ${name}`);
    const [page, ax, ay, w, h] = s;
    const sx = opts.sx ?? 1, sy = opts.sy ?? 1;
    if (!opts.flipX && sx === 1 && sy === 1) {
      ctx.drawImage(this.atlases[page], ax, ay, w, h, Math.round(x), Math.round(y), w, h);
      return;
    }
    ctx.save();
    ctx.translate(Math.round(x) + (opts.flipX ? w * sx : 0), Math.round(y));
    ctx.scale(opts.flipX ? -sx : sx, sy);
    ctx.drawImage(this.atlases[page], ax, ay, w, h, 0, 0, w, h);
    ctx.restore();
  }

  /** Width of a string in the 5x7 font (1 px between letters). */
  textWidth(s: string): number {
    const g = this.index.font.glyphs;
    let w = 0;
    for (const ch of s) w += (g[ch] ?? g['?'])[0].length + 1;
    return Math.max(0, w - 1);
  }

  /** Text with a 1 px outline all round, as the GBA's strip_print draws it. */
  textOutlined(ctx: CanvasRenderingContext2D, s: string, x: number, y: number, color: string, outline: string): void {
    for (let dy = -1; dy <= 1; dy++) for (let dx = -1; dx <= 1; dx++) if (dx || dy) this.text(ctx, s, x + dx, y + dy, outline);
    this.text(ctx, s, x, y, color);
  }

  /** Draws text in the 5x7 font; y is the top of the capitals. */
  text(ctx: CanvasRenderingContext2D, s: string, x: number, y: number, color: string): void {
    const g = this.index.font.glyphs;
    ctx.fillStyle = color;
    let cx = Math.round(x);
    for (const ch of s) {
      const rows = g[ch] ?? g['?'];
      rows.forEach((row, ry) => {
        for (let rx = 0; rx < row.length; rx++) if (row[rx] === '#') ctx.fillRect(cx + rx, Math.round(y) + ry, 1, 1);
      });
      cx += rows[0].length + 1;
    }
  }
}
