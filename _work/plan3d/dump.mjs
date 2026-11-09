// write the plan data of src/apartments.js as JSON for the python checks
import fs from 'fs';
const { APARTMENTS } = await import('./src/apartments.js');
fs.writeFileSync(process.argv[2] || 'qa/apts.json', JSON.stringify(APARTMENTS));
console.log('wrote', process.argv[2] || 'qa/apts.json');
