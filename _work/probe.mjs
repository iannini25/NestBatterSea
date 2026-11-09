import puppeteer from 'puppeteer-core';
const b = await puppeteer.launch({ executablePath: 'C:/Program Files/Google/Chrome/Application/chrome.exe', headless: 'new', args: ['--no-sandbox'] });
const p = await b.newPage(); await p.setViewport({ width: 1600, height: 900 });
p.on('console', m => console.log('console', m.type(), m.text()));
p.on('pageerror', e => console.log('pageerror', e.message));
await p.goto(process.argv[2] || 'http://localhost:8080/', { waitUntil: 'networkidle2' });
await new Promise(r => setTimeout(r, 4000));
console.log(await p.evaluate(() => ({ app: typeof App, state: typeof App !== 'undefined' ? App.state() : null, body: document.body.dataset.state })));
await b.close();
