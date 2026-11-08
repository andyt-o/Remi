const fs = require('node:fs');
const path = require('node:path');

let electronPath;
try {
  electronPath = require('electron');
} catch {
  electronPath = null;
}
if (typeof electronPath !== 'string' || !fs.existsSync(electronPath)) {
  console.error('Electron runtime is missing. From apps/desktop, run: npm install-scripts approve electron && npm rebuild electron');
  process.exit(1);
}
