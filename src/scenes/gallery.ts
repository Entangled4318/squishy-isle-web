/* The art gallery (?gallery): every sprite, screen and map from
 * tools/export_web.py, for review on a real device. Page 1 is the squishy
 * size choice for the map. Tap the right side for the next page, the left
 * side for the one before. A grown-up tool: words are fine here. */
import { Game } from '../game';
import { Scene } from '../engine/scenes';
import { TouchEvt } from '../engine/input';
import { View } from '../engine/screen';
import { dbg } from '../engine/log';

interface Page {
  title: string;
  /** images it needs loaded first */
  needs?: string[];
  draw(ctx: CanvasRenderingContext2D, v: View): void;
}

const INK = '#5a2a44';

export class Gallery implements Scene {
  readonly name = 'gallery';
  page = 0;
  pages: Page[] = [];
  private t = 0;

  constructor(private game: Game) {}

  enter(): void {
    const art = this.game.art;
    const ix = art.index;
    const pages: Page[] = [];
    pages.push(this.sizePage());
    for (const area of ix.names.areas) pages.push(this.areaPage(area.key, area.name, area.species));
    pages.push(this.closeupPage());
    pages.push(this.containersPage());
    const shown = /^(sq\/|gift\/|cont64\/|cont16\/|logo\/)/;
    pages.push(this.gridPage('Pip, Momo and the UI', Object.keys(ix.sprites).filter((n) => !shown.test(n)).sort()));
    pages.push(this.gridPage('Logo letters', ix.logo.map((l) => l.sprite)));
    for (const [key, path] of Object.entries(ix.screens)) pages.push(this.screenPage(key, path));
    for (const m of ix.maps) pages.push(this.mapPage(m.name, [m.ground, m.overlay]));
    this.pages = pages;
    for (const p of pages) for (const f of p.needs ?? []) void art.image(f);
  }

  update(touches: TouchEvt[]): void {
    this.t++;
    for (const e of touches) {
      if (e.kind !== 'down') continue;
      const v = this.game.screen.view;
      const n = this.pages.length;
      this.page = (this.page + (e.x < v.w / 3 ? n - 1 : 1)) % n;
      dbg(`gallery page ${this.page} ${this.pages[this.page].title}`);
    }
  }

  draw(ctx: CanvasRenderingContext2D): void {
    const v = this.game.screen.view;
    ctx.fillStyle = '#fdf3f8';
    ctx.fillRect(0, 0, v.w, v.h);
    const p = this.pages[this.page];
    if (p.needs?.some((f) => !this.game.art.cached(f))) {
      this.label(ctx, v, 'loading...');
      return;
    }
    p.draw(ctx, v);
    this.label(ctx, v, `${this.page + 1}/${this.pages.length} ${p.title}`);
  }

  private label(ctx: CanvasRenderingContext2D, v: View, s: string): void {
    const art = this.game.art;
    const w = art.textWidth(s);
    const x = v.safe.left + 4;
    const y = v.safe.top + 3;
    ctx.fillStyle = 'rgba(255,255,255,0.85)';
    ctx.fillRect(x - 2, y - 2, w + 4, 11);
    art.text(ctx, s, x, y, INK);
  }

  /* Page 1: the squishy size on the map. The GBA draws friends at 16 px;
   * 32 px doubles them. The ring is Apple's 44-point touch target. */
  private sizePage(): Page {
    const meadow = this.game.art.index.maps[0];
    return {
      title: 'Squishy size on the map: left 16 px (GBA), right 32 px',
      needs: [meadow.ground, meadow.overlay],
      draw: (ctx, v) => {
        const art = this.game.art;
        const g = art.cached(meadow.ground)!;
        const ox = Math.round(-meadow.spawn[0] + v.w / 2), oy = Math.round(-meadow.spawn[1] + v.h / 2 + 20);
        ctx.drawImage(g, ox, oy);
        const flavors = art.index.names.flavors;
        const species = art.index.names.areas[0].species;
        const cy = Math.round(v.h / 2 + 20);
        const hop = (i: number) => Math.round(Math.abs(Math.sin((this.t + i * 9) / 10)) * 2);
        art.draw(ctx, 'pip/down0', v.w / 2 - 16, cy - 30);
        for (let i = 0; i < 4; i++) {
          const fl = flavors[i];
          art.draw(ctx, `sq/${species[i]}/${fl}/16/idle`, v.w / 2 - 40 - (i % 2) * 22, cy - 14 + Math.floor(i / 2) * 22 - hop(i));
          art.draw(ctx, `sq/${species[i]}/${fl}/32/idle`, v.w / 2 + 22 + (i % 2) * 38, cy - 34 + Math.floor(i / 2) * 36 - hop(i));
        }
        const r = (22 * v.dpr) / v.k;
        ctx.strokeStyle = 'rgba(90,42,68,0.6)';
        ctx.lineWidth = 1;
        for (const x of [v.w / 2 - 40 + 8, v.w / 2 + 22 + 16]) {
          ctx.beginPath();
          ctx.arc(x, cy + (x < v.w / 2 ? -6 : -18), r, 0, Math.PI * 2);
          ctx.stroke();
        }
      },
    };
  }

  /* One area's friends: 4 species x 5 flavors at 32 px, the silhouettes,
   * the 16 px map sprites and the gifts. */
  private areaPage(key: string, name: string, species: string[]): Page {
    return {
      title: `${name}: friends, 16 px, silhouettes, gifts`,
      draw: (ctx, v) => {
        const art = this.game.art;
        const flavors = art.index.names.flavors;
        const x0 = Math.max(4, Math.round(v.w / 2 - 146)), y0 = v.safe.top + 16;
        species.forEach((sp, r) => {
          const y = y0 + r * 34;
          flavors.forEach((fl, c) => {
            art.draw(ctx, `sq/${sp}/${fl}/32/idle`, x0 + c * 34, y);
            art.draw(ctx, `sq/${sp}/${fl}/16/idle`, x0 + 208 + c * 17, y);
            art.draw(ctx, `gift/${sp}/${fl}`, x0 + 208 + c * 17, y + 17);
          });
          art.draw(ctx, `sq/${sp}/sil/32`, x0 + 172, y);
        });
        void key;
      },
    };
  }

  /* A close-up friend at 64 px: idle, blink, open mouth, squish. */
  private closeupPage(): Page {
    return {
      title: '64 px frames: idle, blink, open, squish (Strawberry)',
      draw: (ctx, v) => {
        const art = this.game.art;
        const all = art.index.names.areas.flatMap((a) => a.species);
        const sp = all[Math.floor(this.t / 90) % all.length];
        ['idle', 'blink', 'open', 'squish'].forEach((fr, i) => art.draw(ctx, `sq/${sp}/strawberry/64/${fr}`, v.w / 2 - 136 + i * 68, v.h / 2 - 32));
      },
    };
  }

  private containersPage(): Page {
    return {
      title: 'Containers: 64 px (body, open, lid) and 16 px, 5 colors each',
      draw: (ctx, v) => {
        const art = this.game.art;
        const areas = art.index.names.areas;
        const x0 = Math.max(2, Math.round(v.w / 2 - 170));
        areas.forEach((a, r) => {
          for (let c = 0; c < 5; c++) {
            const x = x0 + c * 68, y = v.safe.top + 14 + r * 36;
            ctx.save();
            ctx.translate(x, y);
            ctx.scale(0.5, 0.5);
            art.draw(ctx, `cont64/${a.key}/${c}/body`, 0, 0);
            art.draw(ctx, `cont64/${a.key}/${c}/lid`, 0, 0);
            ctx.restore();
            art.draw(ctx, `cont16/${a.key}/${c}`, x + 34, y + 8);
            ctx.save();
            ctx.translate(x + 34, y + 24);
            ctx.scale(0.25, 0.25);
            art.draw(ctx, `cont64/${a.key}/${c}/open`, 0, 0);
            ctx.restore();
          }
        });
      },
    };
  }

  private gridPage(title: string, names: string[]): Page {
    return {
      title,
      draw: (ctx, v) => {
        const art = this.game.art;
        let x = v.safe.left + 4, y = v.safe.top + 14, rowH = 0;
        for (const n of names) {
          const { w, h } = art.size(n);
          if (x + w > v.w - v.safe.right - 4) {
            x = v.safe.left + 4;
            y += rowH + 3;
            rowH = 0;
          }
          art.draw(ctx, n, x, y);
          x += w + 3;
          rowH = Math.max(rowH, h);
        }
      },
    };
  }

  private screenPage(key: string, path: string): Page {
    return {
      title: `Screen: ${key}`,
      needs: [path],
      draw: (ctx, v) => {
        const img = this.game.art.cached(path)!;
        ctx.drawImage(img, Math.round((v.w - img.width) / 2), Math.round((v.h - img.height) / 2));
      },
    };
  }

  private mapPage(name: string, paths: string[]): Page {
    return {
      title: `Map: ${name} (ground and overlay, scaled to fit)`,
      needs: paths,
      draw: (ctx, v) => {
        const [g, o] = paths.map((p) => this.game.art.cached(p)!);
        const s = Math.min((v.w - 8) / g.width, (v.h - 18) / g.height);
        const x = (v.w - g.width * s) / 2, y = 14 + (v.h - 14 - g.height * s) / 2;
        ctx.drawImage(g, x, y, g.width * s, g.height * s);
        ctx.drawImage(o, x, y, o.width * s, o.height * s);
      },
    };
  }
}
