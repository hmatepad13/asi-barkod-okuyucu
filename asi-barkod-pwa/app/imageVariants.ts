export function normalizeBlueChannel(
  rgba: Uint8ClampedArray<ArrayBufferLike>,
): Uint8ClampedArray<ArrayBuffer> {
  const histogram = new Uint32Array(256);
  const pixelCount = Math.floor(rgba.length / 4);
  for (let index = 0; index < pixelCount; index += 1) {
    histogram[rgba[index * 4 + 2]] += 1;
  }

  const lowTarget = Math.max(1, Math.floor(pixelCount * 0.01));
  const highTarget = Math.max(1, Math.ceil(pixelCount * 0.99));
  let cumulative = 0;
  let low = 0;
  let high = 255;
  for (let value = 0; value < 256; value += 1) {
    cumulative += histogram[value];
    if (cumulative >= lowTarget) {
      low = value;
      break;
    }
  }
  cumulative = 0;
  for (let value = 0; value < 256; value += 1) {
    cumulative += histogram[value];
    if (cumulative >= highTarget) {
      high = value;
      break;
    }
  }

  const range = Math.max(1, high - low);
  const output = new Uint8ClampedArray(new ArrayBuffer(rgba.length));
  for (let index = 0; index < pixelCount; index += 1) {
    const sourceOffset = index * 4;
    const blue = rgba[sourceOffset + 2];
    const normalized = Math.max(
      0,
      Math.min(255, Math.round(((blue - low) * 255) / range)),
    );
    output[sourceOffset] = normalized;
    output[sourceOffset + 1] = normalized;
    output[sourceOffset + 2] = normalized;
    output[sourceOffset + 3] = 255;
  }
  return output;
}

export function edgeSharpnessScore(
  rgba: Uint8ClampedArray<ArrayBufferLike>,
  width: number,
  height: number,
): number {
  if (width < 3 || height < 3) return 0;
  const startX = Math.max(1, Math.floor(width * 0.1));
  const endX = Math.min(width - 1, Math.ceil(width * 0.9));
  const startY = Math.max(1, Math.floor(height * 0.1));
  const endY = Math.min(height - 1, Math.ceil(height * 0.9));
  const step = Math.max(1, Math.floor(Math.min(width, height) / 300));
  const gray = (offset: number) =>
    (rgba[offset] * 77 + rgba[offset + 1] * 150 + rgba[offset + 2] * 29) >>
    8;
  let score = 0;
  let samples = 0;

  for (let y = startY; y < endY; y += step) {
    for (let x = startX; x < endX; x += step) {
      const offset = (y * width + x) * 4;
      const current = gray(offset);
      const horizontal = current - gray(offset - step * 4);
      const vertical = current - gray(offset - step * width * 4);
      score += horizontal * horizontal + vertical * vertical;
      samples += 1;
    }
  }
  return samples ? score / samples : 0;
}
