import assert from "node:assert/strict";
import test from "node:test";

import {
  coverTargetSourceRect,
  selectCenteredBarcode,
  type PositionedBarcode,
} from "../app/scanTarget.ts";

function barcode(x: number, y: number, size = 40): PositionedBarcode {
  return {
    isValid: true,
    bytes: new Uint8Array([1]),
    position: {
      topLeft: { x: x - size / 2, y: y - size / 2 },
      topRight: { x: x + size / 2, y: y - size / 2 },
      bottomLeft: { x: x - size / 2, y: y + size / 2 },
      bottomRight: { x: x + size / 2, y: y + size / 2 },
    },
  };
}

test("object-fit cover görüntüsünde görünen kareyi kaynak kameraya eşler", () => {
  const region = coverTargetSourceRect(
    3840,
    2160,
    360,
    300,
    { x: 90, y: 60, width: 180, height: 180 },
    0,
  );

  assert.equal(Math.round(region.width), Math.round(region.height));
  assert.equal(Math.round(region.x + region.width / 2), 1920);
  assert.equal(Math.round(region.y + region.height / 2), 1080);
});

test("varsayılan tarama alanı görünür karenin kenarlarını ayrıca kesmez", () => {
  const region = coverTargetSourceRect(
    1000,
    1000,
    500,
    500,
    { x: 100, y: 100, width: 300, height: 300 },
  );

  assert.equal(region.x, 200);
  assert.equal(region.y, 200);
  assert.equal(region.width, 600);
  assert.equal(region.height, 600);
});

test("iki barkod varsa merkeze yakın olanı seçer", () => {
  const middle = barcode(500, 500);
  const side = barcode(850, 500);
  assert.equal(
    selectCenteredBarcode([side, middle], 1000, 1000),
    middle,
  );
});

test("yalnız kenardaki barkod okunursa sonuç kabul etmez", () => {
  const outside = barcode(900, 500);
  assert.equal(
    selectCenteredBarcode([outside], 1000, 1000),
    undefined,
  );
});
