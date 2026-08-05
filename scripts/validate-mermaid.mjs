#!/usr/bin/env node
//
// REPOSITORY MAINTENANCE — not lab material. Learners can ignore this file.
//
// Parse every ```mermaid block in every markdown file and report syntax errors.
//
//   npm install mermaid jsdom
//   node scripts/validate-mermaid.mjs .
//
import fs from 'node:fs';
import path from 'node:path';
import { JSDOM } from 'jsdom';

const dom = new JSDOM('<!DOCTYPE html><body></body>', { pretendToBeVisual: true });
global.window = dom.window;
global.document = dom.window.document;
Object.defineProperty(global, 'navigator', { value: dom.window.navigator, configurable: true });
global.Element = dom.window.Element;
global.SVGElement = dom.window.SVGElement;

const mermaid = (await import('mermaid')).default;
mermaid.initialize({ startOnLoad: false, securityLevel: 'loose' });

const root = process.argv[2] ?? '.';
const files = [];
(function walk(dir) {
  for (const e of fs.readdirSync(dir, { withFileTypes: true })) {
    if (['.git', 'node_modules', '.remember'].includes(e.name)) continue;
    const p = path.join(dir, e.name);
    if (e.isDirectory()) walk(p);
    else if (e.name.endsWith('.md')) files.push(p);
  }
})(root);

let total = 0;
let failed = 0;

for (const file of files) {
  const lines = fs.readFileSync(file, 'utf8').split('\n');
  let start = -1;
  let buf = [];
  for (let i = 0; i < lines.length; i++) {
    if (start === -1 && /^\s*```mermaid\s*$/.test(lines[i])) {
      start = i;
      buf = [];
      continue;
    }
    if (start === -1) continue;
    if (/^\s*```\s*$/.test(lines[i])) {
      total++;
      try {
        await mermaid.parse(buf.join('\n'));
      } catch (err) {
        failed++;
        console.log(`\n     ${path.relative(root, file)}:${start + 1}`);
        console.log(
          String(err.message ?? err)
            .split('\n')
            .slice(0, 10)
            .map((l) => `       ${l}`)
            .join('\n'),
        );
      }
      start = -1;
    } else {
      buf.push(lines[i]);
    }
  }
}

console.log(`     ${total} diagrams checked, ${failed} failed`);
process.exit(failed ? 1 : 0);
