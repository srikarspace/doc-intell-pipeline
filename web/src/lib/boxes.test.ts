import assert from "node:assert/strict";
import { test } from "node:test";
import type { Highlight } from "./api.ts";
import { toBoxes } from "./boxes.ts";

// The real box of "Kubient, Inc. ("Kubient")" on page 1 of the Kubient sample (an A4 page: 595 x 842 points).
const parties: Highlight = { quote_index: 0, page: 1, page_size: [595, 842], rects: [[318.9, 772.5, 398.5, 780.1]] };

test("at 595 px wide, 1 point is 1 px, and y is flipped to count from the top", () => {
  assert.deepEqual(toBoxes(parties, 595), [{ left: 316.9, top: 59.9, width: 83.6, height: 11.6 }]);
});

test("a page drawn twice as wide doubles the box, but the 2 px of room stays 2 px", () => {
  // width: 79.6 points x 2 = 159.2 px, plus 2 px on each side = 163.2
  assert.deepEqual(toBoxes(parties, 1190), [{ left: 635.8, top: 121.8, width: 163.2, height: 19.2 }]);
});
