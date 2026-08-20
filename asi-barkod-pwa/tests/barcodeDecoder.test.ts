import assert from "node:assert/strict";
import { readFileSync } from "node:fs";
import test from "node:test";
import {
  prepareZXingModule as prepareReader,
} from "zxing-wasm/reader";
import {
  prepareZXingModule as prepareWriter,
  writeBarcode,
} from "zxing-wasm/writer";
import { decodeCenteredBarcode } from "../app/barcodeDecoder.ts";

const TEST_VALUE =
  "010868364221008621TEST123456\u001d1728123110LOT123\u001d99001\u001d97001";

function localWasm(relativePath: string) {
  const file = readFileSync(new URL(relativePath, import.meta.url));
  return file.buffer.slice(
    file.byteOffset,
    file.byteOffset + file.byteLength,
  ) as ArrayBuffer;
}

prepareReader({
  overrides: {
    wasmBinary: localWasm(
      "../node_modules/zxing-wasm/dist/reader/zxing_reader.wasm",
    ),
  },
});
prepareWriter({
  overrides: {
    wasmBinary: localWasm(
      "../node_modules/zxing-wasm/dist/writer/zxing_writer.wasm",
    ),
  },
});

type BarcodeSymbol = Awaited<ReturnType<typeof writeBarcode>>["symbol"];

function renderSymbol(
  symbol: BarcodeSymbol,
  moduleSize = 10,
  quietModules = 4,
) {
  const width = (symbol.width + quietModules * 2) * moduleSize;
  const height = (symbol.height + quietModules * 2) * moduleSize;
  const data = new Uint8ClampedArray(width * height * 4).fill(255);

  for (let symbolY = 0; symbolY < symbol.height; symbolY += 1) {
    for (let symbolX = 0; symbolX < symbol.width; symbolX += 1) {
      const value = symbol.data[symbolY * symbol.width + symbolX];
      for (let pixelY = 0; pixelY < moduleSize; pixelY += 1) {
        for (let pixelX = 0; pixelX < moduleSize; pixelX += 1) {
          const x = (symbolX + quietModules) * moduleSize + pixelX;
          const y = (symbolY + quietModules) * moduleSize + pixelY;
          const offset = (y * width + x) * 4;
          data[offset] = value;
          data[offset + 1] = value;
          data[offset + 2] = value;
        }
      }
    }
  }

  return { data, width, height } as ImageData;
}

function addVerticalPrintGaps(image: ImageData, every = 10, gapWidth = 2) {
  const copy = new Uint8ClampedArray(image.data);
  for (let x = every - 1; x < image.width; x += every) {
    for (let gap = 0; gap < gapWidth; gap += 1) {
      for (let y = 0; y < image.height; y += 1) {
        const offset = (y * image.width + Math.min(image.width - 1, x + gap)) * 4;
        copy[offset] = 255;
        copy[offset + 1] = 255;
        copy[offset + 2] = 255;
      }
    }
  }
  return { data: copy, width: image.width, height: image.height } as ImageData;
}

function halfScaleNearest(image: ImageData) {
  const width = Math.floor(image.width / 2);
  const height = Math.floor(image.height / 2);
  const data = new Uint8ClampedArray(width * height * 4);
  for (let y = 0; y < height; y += 1) {
    for (let x = 0; x < width; x += 1) {
      const source = ((y * 2) * image.width + x * 2) * 4;
      const target = (y * width + x) * 4;
      data[target] = image.data[source];
      data[target + 1] = image.data[source + 1];
      data[target + 2] = image.data[source + 2];
      data[target + 3] = 255;
    }
  }
  return { data, width, height } as ImageData;
}

function rawBytes(result: NonNullable<Awaited<ReturnType<typeof decodeCenteredBarcode>>>) {
  return Array.from(result.bytes, (byte) => String.fromCharCode(byte)).join("");
}

test("gerçek ZXing motoru GS1 DataMatrix verisini eksiksiz çözer", async () => {
  const written = await writeBarcode(TEST_VALUE, {
    format: "DataMatrix",
    addQuietZones: true,
  });
  const image = renderSymbol(written.symbol);

  const result = await decodeCenteredBarcode(image, ["DataMatrix"]);

  assert.ok(result);
  assert.equal(rawBytes(result), TEST_VALUE);
});

test("dikey baskı boşluklu DataMatrix yarı ölçek kurtarmasıyla çözülür", async () => {
  const written = await writeBarcode(TEST_VALUE, {
    format: "DataMatrix",
    addQuietZones: true,
  });
  const damaged = addVerticalPrintGaps(renderSymbol(written.symbol), 10, 4);
  const direct = await decodeCenteredBarcode(damaged, ["DataMatrix"]);
  const rescued = halfScaleNearest(damaged);

  assert.equal(direct, undefined);
  const result = await decodeCenteredBarcode(rescued, ["DataMatrix"]);

  assert.ok(result);
  assert.equal(rawBytes(result), TEST_VALUE);
});
