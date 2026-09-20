import { cpSync, copyFileSync, existsSync } from 'fs';
import { join, dirname } from 'path';
import { fileURLToPath } from 'url';
const __dirname = dirname(fileURLToPath(import.meta.url));
const root = join(__dirname, '..', '..');
const web = join(root, 'web');
const dist = join(root, 'frontend', 'dist');
try {
  if (existsSync(join(dist, 'index.html'))) {
    copyFileSync(join(dist, 'index.html'), join(dist, 'app.html'));
    console.log('copied index.html -> app.html');
  }
  copyFileSync(join(web, 'index.html'), join(dist, 'index.html'));
  console.log('copied web/index.html -> dist/index.html');
  for (const f of ['quantive-logo.png', 'logo.png', 'landing-page-1.jpg', 'landing-page-1.png', 'banking.html', 'qubo.html', 'terms.html', 'chat.html']) {
    const src = join(web, f);
    const dest = join(dist, f);
    if (existsSync(src)) {
      copyFileSync(src, dest);
      console.log(`copied ${f}`);
    }
  }
  const personalSrc = join(web, 'personal');
  const personalDest = join(dist, 'personal');
  if (existsSync(personalSrc)) {
    cpSync(personalSrc, personalDest, { recursive: true });
    console.log('copied personal');
  }
  // also copy new glass logo assets if in public
  for (const f of ['quantive-logo.png', 'logo.png']) {
    const src = join(root, 'frontend', 'public', f);
    if (existsSync(src)) copyFileSync(src, join(dist, f));
  }
  console.log('web copy done');
} catch (e) {
  console.error('copy-web failed', e);
  process.exit(0);
}
