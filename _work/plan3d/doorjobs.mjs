// close up jobs for every door of an apartment: node doorjobs.mjs <apt> [polar] [zoom] [cut]
import fs from 'fs';
const [, , apt, polar = '0.62', zoom = '0.2', cut = 'false'] = process.argv;
const A = JSON.parse(fs.readFileSync('qa/apts.json', 'utf8'))[apt];
const jobs = [];
A.levels.forEach((lv, li) => (lv.doors || []).forEach((d, i) => {
  const o = d.o;
  const horiz = o[2] - o[0] >= o[3] - o[1];
  const c = [(o[0] + o[2]) / 2, (o[1] + o[3]) / 2, 1.0];
  const sides = horiz ? [['s', 0.18], ['n', Math.PI - 0.18]] : [['e', Math.PI / 2 - 0.18], ['w', -Math.PI / 2 + 0.18]];
  for (const [nm, az] of sides) jobs.push({ name: `${apt}-${lv.id}-d${i}-${nm}`, orbit: { level: li, az, polar: +polar, zoom: +zoom, target: c }, cut: cut === 'true' });
}));
console.log(JSON.stringify(jobs));
