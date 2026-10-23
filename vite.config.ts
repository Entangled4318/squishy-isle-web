import { createHash } from 'node:crypto';
import { execSync } from 'node:child_process';
import { readFileSync, readdirSync, statSync } from 'node:fs';
import { join, relative } from 'node:path';
import { defineConfig, Plugin } from 'vite';

const pkg = JSON.parse(readFileSync('package.json', 'utf8')) as { version: string };

function commit(): string {
  if (process.env.GITHUB_SHA) return process.env.GITHUB_SHA.slice(0, 7);
  try {
    return execSync('git rev-parse --short HEAD', { stdio: ['ignore', 'pipe', 'ignore'] }).toString().trim();
  } catch {
    return 'local';
  }
}

const BUILD = `${pkg.version} ${commit()} ${new Date().toISOString().slice(0, 10)}`;

function walk(dir: string): string[] {
  return readdirSync(dir).flatMap((f) => {
    const p = join(dir, f);
    return statSync(p).isDirectory() ? walk(p) : [p];
  });
}

/* Writes sw.js with the list of every built file and a version that
 * changes when any file changes (src/shell/sw-template.js). */
function serviceWorker(): Plugin {
  return {
    name: 'squishy-service-worker',
    apply: 'build',
    enforce: 'post',
    generateBundle(_options, bundle) {
      const hash = createHash('sha256');
      const files = ['./', 'index.html'];
      for (const [name, item] of Object.entries(bundle).sort(([a], [b]) => a.localeCompare(b))) {
        files.push(name);
        hash.update(name);
        hash.update(item.type === 'chunk' ? item.code : typeof item.source === 'string' ? item.source : Buffer.from(item.source));
      }
      for (const p of walk('public').sort()) {
        const name = relative('public', p).split('\\').join('/');
        files.push(name);
        hash.update(name);
        hash.update(readFileSync(p));
      }
      const version = hash.digest('hex').slice(0, 12);
      const code = readFileSync('src/shell/sw-template.js', 'utf8')
        .replace('__VERSION__', version)
        .replace('__FILES__', JSON.stringify([...new Set(files)]));
      this.emitFile({ type: 'asset', fileName: 'sw.js', source: code });
    },
  };
}

export default defineConfig({
  base: '/squishy-isle-web/',
  define: { __BUILD__: JSON.stringify(BUILD) },
  build: { target: ['safari15', 'es2020'], assetsInlineLimit: 0 },
  plugins: [serviceWorker()],
});
