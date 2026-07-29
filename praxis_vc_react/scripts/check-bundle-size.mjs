import { readFile, readdir, stat } from "node:fs/promises";
import { gzipSync } from "node:zlib";
import path from "node:path";
import { fileURLToPath } from "node:url";

const ROOT = path.resolve(path.dirname(fileURLToPath(import.meta.url)), "..");
const DIST = path.join(ROOT, "dist");
const ASSETS = path.join(DIST, "assets");

// C4 budgets deliberately sit above the measured lazy-build values while
// guarding the original 635 kB single-bundle regression.
const BUDGET = {
  initialRaw: 275_000,
  initialGzip: 85_000,
  chunkRaw: 450_000,
  chunkGzip: 130_000,
  fontsRaw: 250_000,
};

const indexHtml = await readFile(path.join(DIST, "index.html"), "utf8");
const initialChunks = new Set(
  [...indexHtml.matchAll(/(?:src|href)="(?:\.\/|\/)?assets\/([^"]+\.js)"/g)].map(
    (match) => match[1],
  ),
);
if (initialChunks.size === 0) {
  throw new Error("bundle budget: dist/index.html has no module entry script");
}

const files = (await readdir(ASSETS)).filter(
  (name) => !name.startsWith("._") && name.endsWith(".js"),
);
if (files.length === 0) {
  throw new Error("bundle budget: dist/assets has no JavaScript chunks");
}

const rows = [];
for (const name of files.sort()) {
  const filePath = path.join(ASSETS, name);
  const raw = (await stat(filePath)).size;
  const gzip = gzipSync(await readFile(filePath)).byteLength;
  const initial = initialChunks.has(name);
  rows.push({ name, initial, raw, gzip });

  if (raw > BUDGET.chunkRaw || gzip > BUDGET.chunkGzip) {
    throw new Error(
      `bundle budget exceeded: ${name} raw=${raw}/${BUDGET.chunkRaw}, gzip=${gzip}/${BUDGET.chunkGzip}`,
    );
  }
}

const initialRows = rows.filter((row) => row.initial);
const initialRaw = initialRows.reduce((total, row) => total + row.raw, 0);
const initialGzip = initialRows.reduce((total, row) => total + row.gzip, 0);
if (initialRaw > BUDGET.initialRaw || initialGzip > BUDGET.initialGzip) {
  throw new Error(
    `initial bundle budget exceeded: raw=${initialRaw}/${BUDGET.initialRaw}, ` +
      `gzip=${initialGzip}/${BUDGET.initialGzip}`,
  );
}

const resultsChunks = rows.filter((row) => /^ResultsStage-.*\.js$/.test(row.name));
if (resultsChunks.length !== 1 || resultsChunks[0].initial) {
  throw new Error("bundle budget: ResultsStage must remain one non-initial lazy chunk");
}

const fontFiles = (await readdir(ASSETS)).filter(
  (name) => !name.startsWith("._") && /\.woff2?$/.test(name),
);
const fontsRaw = (
  await Promise.all(fontFiles.map((name) => stat(path.join(ASSETS, name))))
).reduce((total, info) => total + info.size, 0);
if (fontsRaw > BUDGET.fontsRaw) {
  throw new Error(`font budget exceeded: raw=${fontsRaw}/${BUDGET.fontsRaw}`);
}

console.log("bundle budget passed");
console.log(`initial aggregate: raw=${initialRaw}, gzip=${initialGzip}`);
console.log(`font assets: files=${fontFiles.length}, raw=${fontsRaw}`);
console.table(rows);
