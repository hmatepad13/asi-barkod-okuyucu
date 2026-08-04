export type Rectangle = {
  x: number;
  y: number;
  width: number;
  height: number;
};

export type BarcodePoint = {
  x: number;
  y: number;
};

export type PositionedBarcode = {
  isValid: boolean;
  bytes: Uint8Array;
  position: {
    topLeft: BarcodePoint;
    topRight: BarcodePoint;
    bottomLeft: BarcodePoint;
    bottomRight: BarcodePoint;
  };
};

export function coverTargetSourceRect(
  videoWidth: number,
  videoHeight: number,
  displayWidth: number,
  displayHeight: number,
  target: Rectangle,
  insetRatio = 0,
): Rectangle {
  const scale = Math.max(displayWidth / videoWidth, displayHeight / videoHeight);
  const renderedWidth = videoWidth * scale;
  const renderedHeight = videoHeight * scale;
  const hiddenX = (renderedWidth - displayWidth) / 2;
  const hiddenY = (renderedHeight - displayHeight) / 2;
  const inset = Math.min(target.width, target.height) * insetRatio;

  const x = Math.max(0, (target.x + inset + hiddenX) / scale);
  const y = Math.max(0, (target.y + inset + hiddenY) / scale);
  const right = Math.min(
    videoWidth,
    (target.x + target.width - inset + hiddenX) / scale,
  );
  const bottom = Math.min(
    videoHeight,
    (target.y + target.height - inset + hiddenY) / scale,
  );
  const size = Math.max(1, Math.min(right - x, bottom - y));

  return { x, y, width: size, height: size };
}

function barcodeCenter(barcode: PositionedBarcode) {
  const points = Object.values(barcode.position);
  return {
    x: points.reduce((sum, point) => sum + point.x, 0) / points.length,
    y: points.reduce((sum, point) => sum + point.y, 0) / points.length,
  };
}

export function selectCenteredBarcode<T extends PositionedBarcode>(
  results: T[],
  imageWidth: number,
  imageHeight: number,
  maximumCenterOffset = 0.3,
) {
  const centerX = imageWidth / 2;
  const centerY = imageHeight / 2;
  return results
    .filter((result) => result.isValid && result.bytes.length)
    .map((result) => {
      const center = barcodeCenter(result);
      const offsetX = Math.abs(center.x - centerX) / imageWidth;
      const offsetY = Math.abs(center.y - centerY) / imageHeight;
      return {
        result,
        accepted:
          offsetX <= maximumCenterOffset && offsetY <= maximumCenterOffset,
        distance: offsetX * offsetX + offsetY * offsetY,
      };
    })
    .filter((candidate) => candidate.accepted)
    .sort((left, right) => left.distance - right.distance)[0]?.result;
}
