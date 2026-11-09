// Bundle the dollhouse viewer and the parts of three.js it uses into one minified ES module.
const path = require('path');
const esbuild = require(path.join(__dirname, '../tools/npm3/node_modules/esbuild-wasm'));
esbuild.build({
  entryPoints: [path.join(__dirname, 'src/viewer.js')],
  bundle: true,
  format: 'esm',
  minify: true,
  target: ['es2020'],
  nodePaths: [path.join(__dirname, '../tools/npm3/node_modules')],
  // an optional output path lets a new build be tested before it replaces the live bundle
  outfile: process.argv[2] ? path.resolve(process.argv[2]) : path.join(__dirname, '../../assets/js/plan3d.js'),
  legalComments: 'none',
  metafile: true,
  logLevel: 'warning',
}).then((r) => {
  const out = Object.entries(r.metafile.outputs)[0];
  console.log('bundle', out[0], (out[1].bytes / 1024).toFixed(0) + ' KB');
}).catch((e) => { console.error(e); process.exit(1); });
