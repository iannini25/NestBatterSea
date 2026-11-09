// jobs for 8 azimuths at two elevations: node orbits.mjs <level> <prefix> [zoom]
const [, , level = '0', prefix = 'o', zoom = '0.62'] = process.argv;
const jobs = [];
for (const polar of [0.5, 0.95]) for (let i = 0; i < 8; i++) {
  const az = -Math.PI + (i * Math.PI) / 4;
  jobs.push({ name: `${prefix}-p${polar}-a${i}`, orbit: { level: +level, az, polar, zoom: +zoom } });
}
console.log(JSON.stringify(jobs));
