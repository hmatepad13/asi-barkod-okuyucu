import assert from "node:assert/strict";
import test from "node:test";
import {
  edgeSharpnessScore,
  normalizeBlueChannel,
  repairVerticalPrintGaps,
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

test("yatay kapatma ince dikey beyaz baskı boşluğunu köprüler", () => {
  const width = 7;
  const height = 3;
  const pixels = new Uint8ClampedArray(width * height * 4).fill(255);
  for (let y = 0; y < height; y += 1) {
    for (const x of [0, 1, 2, 4, 5, 6]) {
      const offset = (y * width + x) * 4;
      pixels[offset] = 0;
      pixels[offset + 1] = 0;
      pixels[offset + 2] = 0;
      pixels[offset + 3] = 255;
    }
  }

  const repaired = repairVerticalPrintGaps(pixels, width, height, 3);

  for (let y = 0; y < height; y += 1) {
    assert.equal(repaired[(y * width + 3) * 4], 0);
  }
});

test("yatay kapatma geniş beyaz modülü kapatmaz", () => {
  const width = 9;
  const pixels = new Uint8ClampedArray(width * 4).fill(255);
  for (const x of [0, 1, 2, 6, 7, 8]) {
    const offset = x * 4;
    pixels[offset] = 0;
    pixels[offset + 1] = 0;
    pixels[offset + 2] = 0;
    pixels[offset + 3] = 255;
  }

  const repaired = repairVerticalPrintGaps(pixels, width, 1, 3);

  assert.equal(repaired[4 * 4], 255);
});
