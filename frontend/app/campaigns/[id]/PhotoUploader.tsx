"use client";

import { ChangeEvent, DragEvent, useEffect, useRef, useState } from "react";

export type PendingPhoto = {
  id: string;
  file: File;
  previewUrl: string;
};

const MAX_PHOTOS = 12;
const MAX_SIZE = 5 * 1024 * 1024;
const ACCEPTED_TYPES = new Set(["image/jpeg", "image/png", "image/webp"]);

export function PhotoUploader({
  photos,
  onChange,
  required = false,
}: {
  photos: PendingPhoto[];
  onChange: (photos: PendingPhoto[]) => void;
  required?: boolean;
}) {
  const [error, setError] = useState<string | null>(null);
  const photosRef = useRef(photos);

  useEffect(() => {
    photosRef.current = photos;
  }, [photos]);

  useEffect(() => () => {
    photosRef.current.forEach((photo) => URL.revokeObjectURL(photo.previewUrl));
  }, []);

  function addFiles(files: FileList | File[]) {
    setError(null);
    const incoming = Array.from(files);
    const invalid = incoming.find((file) => !ACCEPTED_TYPES.has(file.type) || file.size > MAX_SIZE);
    if (invalid) {
      setError("Допустимы JPG, PNG и WebP до 5 МБ.");
    }

    const accepted = incoming
      .filter((file) => ACCEPTED_TYPES.has(file.type) && file.size <= MAX_SIZE)
      .slice(0, Math.max(0, MAX_PHOTOS - photos.length))
      .map((file) => ({
        id: `${file.name}-${file.lastModified}-${crypto.randomUUID()}`,
        file,
        previewUrl: URL.createObjectURL(file),
      }));
    if (accepted.length) onChange([...photos, ...accepted]);
  }

  function handleInput(event: ChangeEvent<HTMLInputElement>) {
    if (event.target.files) addFiles(event.target.files);
    event.target.value = "";
  }

  function handleDrop(event: DragEvent<HTMLLabelElement>) {
    event.preventDefault();
    addFiles(event.dataTransfer.files);
  }

  function removePhoto(id: string) {
    const photo = photos.find((item) => item.id === id);
    if (photo) URL.revokeObjectURL(photo.previewUrl);
    onChange(photos.filter((item) => item.id !== id));
  }

  return (
    <div className="space-y-3">
      <label
        className="flex cursor-pointer flex-col items-center justify-center rounded-[22px] border border-dashed border-stone-300 bg-white px-5 py-7 text-center transition hover:border-emerald-400 hover:bg-emerald-50/40"
        onDragOver={(event) => event.preventDefault()}
        onDrop={handleDrop}
      >
        <span className="rounded-full bg-stone-950 px-4 py-2 text-sm font-semibold text-white">Выбрать фото</span>
        <span className="mt-2 text-xs leading-5 text-stone-500">или перетащите сюда · JPG, PNG, WebP · до 5 МБ</span>
        <input
          className="sr-only"
          type="file"
          accept="image/jpeg,image/png,image/webp"
          multiple
          required={required && !photos.length}
          onChange={handleInput}
          disabled={photos.length >= MAX_PHOTOS}
        />
      </label>
      {error ? <p className="text-sm text-rose-700">{error}</p> : null}
      {photos.length ? (
        <div className="grid grid-cols-2 gap-3 sm:grid-cols-3">
          {photos.map((photo) => (
            <div key={photo.id} className="overflow-hidden rounded-2xl border border-stone-200 bg-white">
              <img src={photo.previewUrl} alt="" className="aspect-[4/3] w-full object-cover" />
              <div className="flex items-center justify-between gap-2 px-3 py-2">
                <span className="truncate text-xs text-stone-500">{photo.file.name}</span>
                <button type="button" onClick={() => removePhoto(photo.id)} className="text-xs font-semibold text-stone-600 hover:text-rose-700">
                  Удалить
                </button>
              </div>
            </div>
          ))}
        </div>
      ) : null}
    </div>
  );
}
