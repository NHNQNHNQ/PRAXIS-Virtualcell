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
  entryRaw: 300_000,
  entryGzip: 90_000,
  chunkRaw: 500_000,
  chunkGzip: 140_000,
};

const indexHtml = await readFile(path.join(DIST, "index.html"), "utf8");
const entryMatch = indexHtml.match(
  /<script[^>]+src="(?:\.\/|\/)?assets\/([^"]+\.js)"/,
);
if (!entryMatch) {
  throw new Error("bundle budget: dist/index.html has no module entry script");
}

const files = (await readdir(ASSETS)).filter((name) => name.endsWith(".js"));
if (files.length === 0) {
  throw new Error("bundle budget: dist/assets has no JavaScript chunks");
}

const rows = [];
for (const name of files.sort()) {
  const filePath = path.join(ASSETS, name);
  const raw = (await stat(filePath)).size;
  const gzip = gzipSync(await readFile(filePath)).byteLength;
  const entry = name === entryMatch[1];
  rows.push({ name, entry, raw, gzip });

  const rawLimit = entry ? BUDGET.entryRaw : BUDGET.chunkRaw;
  const gzipLimit = entry ? BUDGET.entryGzip : BUDGET.chunkGzip;
  if (raw > rawLimit || gzip > gzipLimit) {
    throw new Error(
      `bundle budget exceeded: ${name} raw=${raw}/${rawLimit}, gzip=${gzip}/${gzipLimit}`,
    );
  }
}

console.log("bundle budget passed");
console.table(rows);
