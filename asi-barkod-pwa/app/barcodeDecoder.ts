import {
  readBarcodes,
  type ReadResult,
  type ReaderOptions,
} from "zxing-wasm/reader";
import { selectCenteredBarcode } from "./scanTarget.ts";

export type SupportedBarcodeFormat = "DataMatrix" | "QRCode";

const READER_DEFAULTS = {
  maxNumberOfSymbols: 4,
  tryHarder: true,
  tryRotate: true,
  tryInvert: true,
  tryDownscale: true,
  tryDenoise: true,
  textMode: "Plain",
} satisfies Omit<ReaderOptions, "formats">;

async function read(
  imageData: ImageData,
  formats: SupportedBarcodeFormat[],
) {
  return readBarcodes(imageData, {
    ...READER_DEFAULTS,
    formats,
  });
}

export async function decodeCenteredBarcode(
  imageData: ImageData,
  formats: SupportedBarcodeFormat[],
): Promise<ReadResult | undefined> {
  const results = await read(imageData, formats);
  return selectCenteredBarcode(results, imageData.width, imageData.height);
}

export async function decodeFirstBarcode(
  imageData: ImageData,
  formats: SupportedBarcodeFormat[],
): Promise<ReadResult | undefined> {
  const results = await read(imageData, formats);
  return results.find((result) => result.isValid && result.bytes.length);
}
