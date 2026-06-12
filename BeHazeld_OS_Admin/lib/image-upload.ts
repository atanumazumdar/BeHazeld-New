'use client';

const MAX_UPLOAD_BYTES = 3_500_000;
const MAX_IMAGE_EDGE = 1800;
const QUALITY_STEPS = [0.82, 0.72, 0.62, 0.54];

function loadBrowserImage(file: File): Promise<HTMLImageElement> {
  return new Promise((resolve, reject) => {
    const url = URL.createObjectURL(file);
    const image = new Image();

    image.onload = () => {
      URL.revokeObjectURL(url);
      resolve(image);
    };
    image.onerror = () => {
      URL.revokeObjectURL(url);
      reject(new Error('Could not read the selected image.'));
    };
    image.src = url;
  });
}

function canvasToBlob(
  canvas: HTMLCanvasElement,
  type: string,
  quality: number,
): Promise<Blob> {
  return new Promise((resolve, reject) => {
    canvas.toBlob(
      (blob) => {
        if (!blob) {
          reject(new Error('Could not prepare the selected image.'));
          return;
        }
        resolve(blob);
      },
      type,
      quality,
    );
  });
}

function jpgName(filename: string): string {
  return filename.replace(/\.[^.]+$/, '') + '.jpg';
}

export async function prepareProductImageForUpload(file: File): Promise<File> {
  if (!file.type.startsWith('image/')) {
    throw new Error('Please choose a JPG, PNG, or WebP image.');
  }

  if (file.size <= MAX_UPLOAD_BYTES) {
    return file;
  }

  const image = await loadBrowserImage(file);
  const scale = Math.min(1, MAX_IMAGE_EDGE / Math.max(image.naturalWidth, image.naturalHeight));
  const width = Math.max(1, Math.round(image.naturalWidth * scale));
  const height = Math.max(1, Math.round(image.naturalHeight * scale));
  const canvas = document.createElement('canvas');
  const context = canvas.getContext('2d');

  if (!context) {
    throw new Error('Could not prepare the selected image.');
  }

  canvas.width = width;
  canvas.height = height;
  context.fillStyle = '#ffffff';
  context.fillRect(0, 0, width, height);
  context.drawImage(image, 0, 0, width, height);

  let bestBlob: Blob | null = null;
  for (const quality of QUALITY_STEPS) {
    const blob = await canvasToBlob(canvas, 'image/jpeg', quality);
    bestBlob = blob;
    if (blob.size <= MAX_UPLOAD_BYTES) break;
  }

  if (!bestBlob || bestBlob.size > MAX_UPLOAD_BYTES) {
    throw new Error('Please upload a smaller image. The selected photo is too large after optimization.');
  }

  return new File([bestBlob], jpgName(file.name), {
    type: 'image/jpeg',
    lastModified: Date.now(),
  });
}

