// Auto-add missing lucide-react icon imports for TS2304 errors.
// Usage: node scripts/fix-lucide-imports.mjs
import { readFileSync, writeFileSync } from 'node:fs';
import { execSync } from 'node:child_process';

const dts = readFileSync('node_modules/lucide-react/dist/lucide-react.d.ts', 'utf8');
const exports = new Set([...dts.matchAll(/declare const (\w+):/g)].map((m) => m[1]));

// Deprecated lucide names still used across components -> canonical export.
const ALIASES = {
  AlertTriangle: 'TriangleAlert',
  CheckCircle: 'CircleCheck',
  CheckCircle2: 'CircleCheckBig',
  XCircle: 'CircleX',
  BarChart3: 'ChartColumn',
  BarChart2: 'ChartColumnBig',
  BarChart: 'ChartNoAxesColumn',
};

let tscOut = '';
try {
  tscOut = execSync('npx tsc -b --force --pretty false', { encoding: 'utf8', maxBuffer: 64 * 1024 * 1024 });
} catch (err) {
  // tsc exits non-zero when errors exist — output is still on stdout
  tscOut = err.stdout || '';
}
const missing = new Map(); // file -> Set<name>
for (const line of tscOut.split('\n')) {
  const m = line.match(/^(src[^(]+\.tsx?)\(\d+,\d+\): error TS2304: Cannot find name '(\w+)'/);
  if (!m) continue;
  const [, file, rawName] = m;
  let name = rawName;
  let importAs = null;
  if (!exports.has(name)) {
    if (ALIASES[name] && exports.has(ALIASES[name])) {
      importAs = `${ALIASES[name]} as ${name}`;
    } else {
      continue;
    }
  }
  if (!missing.has(file)) missing.set(file, new Map());
  if (!missing.get(file).has(name)) missing.get(file).set(name, importAs || name);
}

let touched = 0;
for (const [file, nameMap] of missing) {
  let src = readFileSync(file, 'utf8');
  const lucideRe = /import\s*\{([^}]*)\}\s*from\s*['"]lucide-react['"]/;
  const lm = src.match(lucideRe);
  const have = new Set(
    lm ? lm[1].split(',').map((s) => s.trim()).filter(Boolean) : [],
  );
  // Also treat `X as Y` entries as providing Y
  for (const h of [...have]) {
    const am = h.match(/as\s+(\w+)\s*$/);
    if (am) have.add(am[1]);
  }
  const needed = [...nameMap.entries()]
    .filter(([n]) => !have.has(n))
    .map(([, imp]) => imp);
  if (needed.length === 0) continue;
  if (lm) {
    const merged = [...lm[1].split(',').map((s) => s.trim()).filter(Boolean), ...needed];
    merged.sort();
    src = src.replace(lucideRe, `import { ${merged.join(', ')} } from 'lucide-react'`);
  } else {
    const lines = src.split('\n');
    // Find the end of the last complete import statement (handles multiline).
    let idx = 0;
    let inImport = false;
    for (let i = 0; i < lines.length; i++) {
      if (/^import /.test(lines[i])) inImport = true;
      if (inImport && /from\s+['"][^'"]+['"];?\s*$/.test(lines[i])) {
        idx = i + 1;
        inImport = false;
      }
      if (!inImport && lines[i].trim() !== '' && !/^import /.test(lines[i]) && idx > 0) break;
    }
    needed.sort();
    lines.splice(idx, 0, `import { ${needed.join(', ')} } from 'lucide-react';`);
    src = lines.join('\n');
  }
  writeFileSync(file, src);
  touched++;
  console.log(`fixed ${file}: +${needed.join(', ')}`);
}
console.log(`touched ${touched} files`);
