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

/**
 * İnce dikey yazıcı boşluklarını kapatmak için yalnız yatay eksende
 * morfolojik kapatma uygular. Önce koyu pikselleri yatayda genişletir,
 * sonra aynı miktarda geri toplar. Böylece kısa beyaz dikey kopukluklar
 * kapanır; üst-alt yönde yayılma olmaz.
 */
export function repairVerticalPrintGaps(
  rgba: Uint8ClampedArray<ArrayBufferLike>,
  width: number,
  height: number,
  kernelWidth: number,
): Uint8ClampedArray<ArrayBuffer> {
  if (width < 1 || height < 1 || rgba.length < width * height * 4) {
    throw new Error("Geçersiz barkod görüntüsü.");
  }
  if (kernelWidth < 3 || kernelWidth % 2 === 0) {
    throw new Error("Onarım genişliği 3 veya daha büyük tek sayı olmalı.");
  }

  const histogram = new Uint32Array(256);
  const pixelCount = width * height;
  const luminance = new Uint8Array(pixelCount);
  for (let index = 0; index < pixelCount; index += 1) {
    const offset = index * 4;
    const value =
      (rgba[offset] * 77 + rgba[offset + 1] * 150 + rgba[offset + 2] * 29) >>
      8;
    luminance[index] = value;
    histogram[value] += 1;
  }

  let total = 0;
  for (let value = 0; value < 256; value += 1) total += value * histogram[value];
  let backgroundWeight = 0;
  let backgroundTotal = 0;
  let bestScore = -1;
  let threshold = 127;
  for (let value = 0; value < 256; value += 1) {
    backgroundWeight += histogram[value];
    if (!backgroundWeight) continue;
    const foregroundWeight = pixelCount - backgroundWeight;
    if (!foregroundWeight) break;
    backgroundTotal += value * histogram[value];
    const backgroundMean = backgroundTotal / backgroundWeight;
    const foregroundMean = (total - backgroundTotal) / foregroundWeight;
    const score =
      backgroundWeight * foregroundWeight *
      (backgroundMean - foregroundMean) * (backgroundMean - foregroundMean);
    if (score > bestScore) {
      bestScore = score;
      threshold = value;
    }
  }

  const ink = new Uint8Array(pixelCount);
  for (let index = 0; index < pixelCount; index += 1) {
    ink[index] = luminance[index] <= threshold ? 1 : 0;
  }

  const radius = Math.floor(kernelWidth / 2);
  const dilated = new Uint8Array(pixelCount);
  for (let y = 0; y < height; y += 1) {
    for (let x = 0; x < width; x += 1) {
      const start = Math.max(0, x - radius);
      const end = Math.min(width - 1, x + radius);
      for (let sourceX = start; sourceX <= end; sourceX += 1) {
        if (ink[y * width + sourceX]) {
          dilated[y * width + x] = 1;
          break;
        }
      }
    }
  }

  const output = new Uint8ClampedArray(new ArrayBuffer(rgba.length));
  for (let y = 0; y < height; y += 1) {
    for (let x = 0; x < width; x += 1) {
      const start = Math.max(0, x - radius);
      const end = Math.min(width - 1, x + radius);
      let closed = 1;
      for (let sourceX = start; sourceX <= end; sourceX += 1) {
        if (!dilated[y * width + sourceX]) {
          closed = 0;
          break;
        }
      }
      const offset = (y * width + x) * 4;
      const value = closed ? 0 : 255;
      output[offset] = value;
      output[offset + 1] = value;
      output[offset + 2] = value;
      output[offset + 3] = 255;
    }
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
