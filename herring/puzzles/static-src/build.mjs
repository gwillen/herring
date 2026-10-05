// Builds the frontend into ../static: app.js -> bundle.js (esbuild) and
// style.less -> style.css (less). Both outputs are committed.
//
//   node build.mjs           one-off build
//   node build.mjs --watch   rebuild on changes
import * as esbuild from 'esbuild';
import less from 'less';
import { readFile, writeFile } from 'node:fs/promises';
import { watch } from 'node:fs';

const OUT_DIR = '../static';
const LESS_SOURCE = 'style.less';

const jsOptions = {
  entryPoints: ['app.js'],
  outfile: `${OUT_DIR}/bundle.js`,
  bundle: true,
  minify: true,
  target: 'es2022',
  loader: { '.js': 'jsx' },
  jsx: 'automatic',
  define: { 'process.env.NODE_ENV': '"production"' },
  logLevel: 'info',
};

async function buildCss() {
  const source = await readFile(LESS_SOURCE, 'utf8');
  // math: 'always' keeps LESS 2's handling of unparenthesized division (e.g. @stdpadding/2).
  const { css } = await less.render(source, { filename: LESS_SOURCE, math: 'always' });
  await writeFile(`${OUT_DIR}/style.css`, css);
  console.log(`${new Date().toISOString()} built ${OUT_DIR}/style.css`);
}

async function rebuildCssLoudly() {
  try {
    await buildCss();
  } catch (err) {
    console.error(`${new Date().toISOString()} style.less build failed:`, err.message);
  }
}

async function watchAll() {
  await rebuildCssLoudly();
  watch(LESS_SOURCE, rebuildCssLoudly);
  const context = await esbuild.context(jsOptions);
  await context.watch();
}

if (process.argv.includes('--watch')) {
  await watchAll();
} else {
  await buildCss();
  await esbuild.build(jsOptions);
}
