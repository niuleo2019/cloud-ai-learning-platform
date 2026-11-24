import { Capacitor } from '@capacitor/core';
import { Camera } from '@capacitor/camera';

/** True inside the Android/iOS app, where the native camera plugin is available. */
export const canUseNativeCamera = Capacitor.isNativePlatform();

export class CameraCancelledError extends Error {}

/**
 * Open the phone's camera, let the user take one photo and return it as a File,
 * ready for the existing OCR upload. Throws CameraCancelledError if the user backs out.
 */
export async function takePhotoForOcr(): Promise<File> {
  let photo;
  try {
    photo = await Camera.takePhoto({
      quality: 85, // keeps phone photos well under the 8MB upload limit
      correctOrientation: true,
      saveToGallery: false
    });
  } catch (error) {
    const code = (error as { code?: string }).code;
    if (code === 'OS-PLUG-CAMR-0006') {
      throw new CameraCancelledError('Camera cancelled');
    }
    throw error;
  }

  if (!photo.webPath) {
    throw new Error('Camera returned no image');
  }

  // webPath is a local URL the WebView can read; turn it into a File for multipart upload.
  const blob = await (await fetch(photo.webPath)).blob();
  const file = new File([blob], `camera-${Date.now()}.jpg`, { type: blob.type || 'image/jpeg' });
  return shrinkImageForOcr(file);
}

const OCR_MAX_SIDE = 2000;

/**
 * Phone photos are often 8-12MB (50MP sensors). Uploading that over Wi-Fi is slow and
 * OCR does not need it, so scale the longest side down to 2000px and re-encode as JPEG.
 * Small images, and anything the browser cannot decode, are returned unchanged.
 */
export async function shrinkImageForOcr(file: File): Promise<File> {
  try {
    const bitmap = await createImageBitmap(file);
    const scale = Math.min(1, OCR_MAX_SIDE / Math.max(bitmap.width, bitmap.height));
    if (scale === 1 && file.size <= 1.5 * 1024 * 1024) {
      bitmap.close();
      return file;
    }

    const canvas = document.createElement('canvas');
    canvas.width = Math.round(bitmap.width * scale);
    canvas.height = Math.round(bitmap.height * scale);
    canvas.getContext('2d')?.drawImage(bitmap, 0, 0, canvas.width, canvas.height);
    bitmap.close();

    const blob = await new Promise<Blob | null>((resolve) => canvas.toBlob(resolve, 'image/jpeg', 0.85));
    if (!blob) return file;
    const name = file.name.replace(/\.[^.]+$/, '') + '.jpg';
    return new File([blob], name, { type: 'image/jpeg' });
  } catch {
    return file;
  }
}
