// Runs only the map page block of ../e2e.mjs (same checks, same helpers), for a quick re-check.
//   cd _work && node mapdata/e2e_map.mjs http://localhost:8080/ evidence
import fs from 'node:fs';
const src = fs.readFileSync(new URL('../e2e.mjs', import.meta.url), 'utf8');
const head = src.slice(0, src.indexOf('// geometry of the notches'));
const a = src.indexOf('// ======================================================= the neighbourhood map page');
const b = src.indexOf('// ======================================================= reduced motion');
const tail = `await browser.close();
const errs = logs.filter(l => /error|requestfailed|http [45]/.test(l));
check('No console errors or failed requests', errs.length === 0, errs.slice(0, 4).join(' | '));
console.log(\`\\n\${results.filter(r => r.ok).length}/\${results.length} passed\`);`;
const out = new URL('./_e2e_map_run.mjs', import.meta.url);
fs.writeFileSync(out, head.replace("from 'puppeteer-core'", "from 'puppeteer-core'") + '\n' + src.slice(a, b) + '\n' + tail);
await import(out.href);
