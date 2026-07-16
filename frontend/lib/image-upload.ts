export const MAX_IMAGE_SIZE_BYTES = 10 * 1024 * 1024;
export const MAX_IMAGE_SIZE_MB = 10;
export const IMAGE_INPUT_ACCEPT = "image/jpeg,image/png,image/webp";

const ALLOWED_IMAGE_TYPES = new Set(IMAGE_INPUT_ACCEPT.split(","));

export function getImageValidationError(file: File) {
  if (!ALLOWED_IMAGE_TYPES.has(file.type)) {
    return "Допустимы только JPG, PNG и WebP.";
  }
  if (file.size > MAX_IMAGE_SIZE_BYTES) {
    return `Фото слишком большое. Максимальный размер — ${MAX_IMAGE_SIZE_MB} МБ.`;
  }
  return null;
}

export function assertValidImage(file: File) {
  const error = getImageValidationError(file);
  if (error) throw new Error(error);
}
