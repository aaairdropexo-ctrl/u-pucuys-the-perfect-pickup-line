// One pickup line (150 chars) written to /output/entry.txt.
// The guard keeps the entry inside the kit's 1-200 character gate.
import { mkdirSync, writeFileSync } from "node:fs";

const LINE =
  "I ran a million simulations of saying hello to you. In every one, you smiled — so I stopped simulating and came over. Mind if this one counts as real?";

const length = [...LINE].length;
if (length < 1 || length > 200) {
  throw new Error(`entry must be 1-200 characters, got ${length}`);
}
if (LINE.trim().length === 0) {
  throw new Error("entry must not be only whitespace");
}

mkdirSync("/output", { recursive: true });
writeFileSync("/output/entry.txt", LINE, "utf8");
