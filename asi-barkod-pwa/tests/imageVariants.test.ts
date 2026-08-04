import assert from "node:assert/strict";
import test from "node:test";
import {
  edgeSharpnessScore,
  normalizeBlueChannel,
} from "../app/imageVariants.ts";

test("mavi kalemi siyah DataMatrix hücresinden ayırır", () => {
  const pixels = new Uint8ClampedArray([
    20, 20, 20, 255,
    35, 70, 185, 255,
    240, 240, 240, 255,
  ]);

  const result = normalizeBlueChannel(pixels);

  assert.equal(result[0], 0);
  assert.ok(result[4] > 150);
  assert.equal(result[8], 255);
  assert.equal(result[4], result[5]);
  assert.equal(result[5], result[6]);
});

test("çıktıyı opak gri RGBA olarak üretir", () => {
  const result = normalizeBlueChannel(
    new Uint8ClampedArray([10, 20, 30, 40]),
  );

  assert.equal(result.length, 4);
  assert.equal(result[0], result[1]);
  assert.equal(result[1], result[2]);
  assert.equal(result[3], 255);
});

test("keskin kenarlı kareyi düz görüntüden daha yüksek puanlar", () => {
  const flat = new Uint8ClampedArray(8 * 8 * 4).fill(128);
  const sharp = new Uint8ClampedArray(8 * 8 * 4);
  for (let pixel = 0; pixel < 8 * 8; pixel += 1) {
    const value = (Math.floor(pixel / 8) + (pixel % 8)) % 2 ? 255 : 0;
    const offset = pixel * 4;
    sharp[offset] = value;
    sharp[offset + 1] = value;
    sharp[offset + 2] = value;
    sharp[offset + 3] = 255;
  }

  assert.ok(
    edgeSharpnessScore(sharp, 8, 8) >
      edgeSharpnessScore(flat, 8, 8),
  );
});
