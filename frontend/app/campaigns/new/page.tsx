"use client";

import Link from "next/link";
import { ChangeEvent, DragEvent, FormEvent, useCallback, useEffect, useRef, useState } from "react";
import { useRouter } from "next/navigation";
import { ParticipationCard } from "@/app/components/ParticipationCard";
import { UserErrorAlert } from "@/components/user-error-alert";
import { useAuth } from "@/components/providers/auth-provider";
import { createCampaign, fetchContributionProgress, uploadCampaignCover } from "@/lib/api";
import { toUserError, type UserError } from "@/lib/user-errors";
import type { CampaignCategory, ContributionProgress } from "@/lib/types";
import {
  CAMPAIGN_DESCRIPTION_MAX_LENGTH,
  CAMPAIGN_DESCRIPTION_MIN_LENGTH,
  CAMPAIGN_TITLE_MAX_LENGTH,
  CAMPAIGN_TITLE_MIN_LENGTH,
} from "@/lib/validation";

type CoverImagePreview = {
  id: string;
  name: string;
  url: string;
  file: File;
};

type SupportingDocument = {
  id: string;
  name: string;
  size: number;
};

const maxCoverImages = 3;
const acceptedDocumentTypes = ["application/pdf", "image/jpeg", "image/png"];
const descriptionPlaceholder = `Расскажите:
- зачем вам нужна помощь
- почему это важно
- как изменится ваша ситуация после достижения цели

Людям проще поддержать цель, когда они понимают ее историю.`;

const categories: Array<{ value: CampaignCategory; label: string }> = [
  { value: "medical", label: "Лечение" },
  { value: "education", label: "Образование" },
  { value: "emergency", label: "Срочно" },
  { value: "pets", label: "Животные" },
  { value: "community", label: "Сообщество" },
  { value: "personal", label: "Личное" },
  { value: "other", label: "Другое" },
];

export default function NewCampaignPage() {
  const router = useRouter();
  const { isAuthenticated, isLoading } = useAuth();
  const [contributionProgress, setContributionProgress] = useState<ContributionProgress | null>(null);
  const [isProgressLoading, setIsProgressLoading] = useState(true);
  const [title, setTitle] = useState("");
  const [description, setDescription] = useState("");
  const [targetAmount, setTargetAmount] = useState("10000");
  const [category, setCategory] = useState<CampaignCategory>("other");
  const [coverImages, setCoverImages] = useState<CoverImagePreview[]>([]);
  const [supportingDocuments, setSupportingDocuments] = useState<SupportingDocument[]>([]);
  const [isSubmitting, setIsSubmitting] = useState(false);
  const [error, setError] = useState<UserError | null>(null);
  const coverImagesRef = useRef<CoverImagePreview[]>([]);
  const isLargeTargetAmount = Number(targetAmount) > 1_000_000;

  const loadContributionProgress = useCallback(async () => {
    if (!isAuthenticated) return;
    if (!contributionProgress) setIsProgressLoading(true);
    try {
      setContributionProgress(await fetchContributionProgress());
    } catch (err) {
      setError(toUserError(err, { title: "Не удалось загрузить прогресс" }));
    } finally {
      setIsProgressLoading(false);
    }
  }, [contributionProgress, isAuthenticated]);

  useEffect(() => {
    if (!isLoading && !isAuthenticated) {
      router.replace("/login?next=/campaigns/new");
    }
  }, [isAuthenticated, isLoading, router]);

  useEffect(() => {
    loadContributionProgress();
  }, [loadContributionProgress]);

  useEffect(() => {
    window.addEventListener("focus", loadContributionProgress);
    return () => window.removeEventListener("focus", loadContributionProgress);
  }, [loadContributionProgress]);

  useEffect(() => {
    coverImagesRef.current = coverImages;
  }, [coverImages]);

  useEffect(() => {
    return () => {
      coverImagesRef.current.forEach((image) => URL.revokeObjectURL(image.url));
    };
  }, []);

  function addCoverImages(files: FileList | File[]) {
    const imageFiles = Array.from(files).filter((file) => file.type.startsWith("image/"));
    if (!imageFiles.length) return;

    setCoverImages((currentImages) => {
      const availableSlots = maxCoverImages - currentImages.length;
      if (availableSlots <= 0) return currentImages;

      const nextImages = imageFiles.slice(0, availableSlots).map((file) => ({
        id: `${file.name}-${file.lastModified}-${crypto.randomUUID()}`,
        name: file.name,
        url: URL.createObjectURL(file),
        file,
      }));

      return [...currentImages, ...nextImages];
    });
  }

  function handleCoverInputChange(event: ChangeEvent<HTMLInputElement>) {
    if (!event.target.files) return;
    addCoverImages(event.target.files);
    event.target.value = "";
  }

  function handleCoverDrop(event: DragEvent<HTMLLabelElement>) {
    event.preventDefault();
    addCoverImages(event.dataTransfer.files);
  }

  function removeCoverImage(imageId: string) {
    setCoverImages((currentImages) => {
      const imageToRemove = currentImages.find((image) => image.id === imageId);
      if (imageToRemove) URL.revokeObjectURL(imageToRemove.url);
      return currentImages.filter((image) => image.id !== imageId);
    });
  }

  function handleDocumentsChange(event: ChangeEvent<HTMLInputElement>) {
    if (!event.target.files) return;

    const documents = Array.from(event.target.files)
      .filter((file) => acceptedDocumentTypes.includes(file.type))
      .map((file) => ({
        id: `${file.name}-${file.lastModified}-${crypto.randomUUID()}`,
        name: file.name,
        size: file.size,
      }));

    setSupportingDocuments((currentDocuments) => [...currentDocuments, ...documents]);
    event.target.value = "";
  }

  function removeSupportingDocument(documentId: string) {
    setSupportingDocuments((currentDocuments) => currentDocuments.filter((document) => document.id !== documentId));
  }

  async function handleSubmit(event: FormEvent<HTMLFormElement>) {
    event.preventDefault();
    setError(null);
    setIsSubmitting(true);

    try {
      const coverImageUrl = coverImages[0] ? (await uploadCampaignCover(coverImages[0].file)).url : null;
      const campaign = await createCampaign({
        title,
        description,
        target_amount: Number(targetAmount),
        category,
        cover_image_url: coverImageUrl,
      });
      router.push(`/campaigns/${campaign.id}`);
    } catch (err) {
      setError(toUserError(err, { title: "Не удалось создать сбор" }));
      await loadContributionProgress();
    } finally {
      setIsSubmitting(false);
    }
  }

  if (isLoading || !isAuthenticated || isProgressLoading) {
    return <div className="border-y border-stone-200 py-6 text-stone-600">Загружаем...</div>;
  }

  if (!contributionProgress?.can_create_campaign) {
    const hasUnfinishedCampaign = contributionProgress?.has_unfinished_campaign;

    return (
      <section className="mx-auto max-w-3xl space-y-6">
        <header className="border-b border-stone-200 pb-8">
          <p className="text-xs font-semibold uppercase tracking-[0.18em] text-emerald-700">сбор пока закрыт</p>
          <h1 className="mt-3 text-4xl font-semibold tracking-[-0.035em] text-stone-950 md:text-5xl">
            {hasUnfinishedCampaign ? "Сначала завершите текущую историю." : "Поддержите 5 других сборов, чтобы открыть свой."}
          </h1>
          <p className="mt-4 max-w-2xl leading-7 text-stone-600">
            {hasUnfinishedCampaign
              ? "Новый сбор станет доступен после завершения активной истории и публикации итогового отчета."
              : "Подтвержденные вклады от 100 ₽ засчитываются автоматически, включая анонимные, если вы привяжете их после регистрации."}
          </p>
        </header>

        <div className="space-y-4">
          {contributionProgress ? <ParticipationCard progress={contributionProgress} /> : null}
          <Link href="/campaigns" className="mt-5 inline-flex rounded-full bg-stone-950 px-5 py-3 font-medium text-white transition hover:bg-emerald-700">
            Смотреть сборы
          </Link>
        </div>

        {error ? <UserErrorAlert error={error} /> : null}
      </section>
    );
  }

  return (
    <section className="mx-auto max-w-3xl space-y-6">
      <header className="border-b border-stone-200 pb-8">
        <p className="text-xs font-semibold uppercase tracking-[0.18em] text-emerald-700">новая история</p>
        <h1 className="mt-3 text-4xl font-semibold tracking-[-0.035em] text-stone-950 md:text-5xl">Открыть сбор</h1>
        <p className="mt-4 text-sm font-medium text-emerald-800">Создание сборов доступно</p>
      </header>

      <form onSubmit={handleSubmit} className="space-y-8">
        <div className="space-y-4">
          <div>
            <p className="text-sm font-semibold uppercase tracking-[0.16em] text-stone-400">история</p>
            <p className="mt-2 text-sm leading-6 text-stone-600">Название и рассказ помогают людям быстро понять, кого и зачем они поддерживают.</p>
          </div>

          <label className="block text-sm font-medium text-stone-700">
            Название
            <input
              className="mt-2 w-full rounded-xl border border-stone-300 bg-white px-4 py-3 outline-none transition placeholder:text-stone-400 focus:border-emerald-500 focus:ring-4 focus:ring-emerald-100"
              minLength={CAMPAIGN_TITLE_MIN_LENGTH}
              maxLength={CAMPAIGN_TITLE_MAX_LENGTH}
              value={title}
              onChange={(event) => setTitle(event.target.value)}
              required
            />
            <span className="mt-2 flex justify-between gap-3 text-xs font-normal text-stone-500">
              <span>{CAMPAIGN_TITLE_MIN_LENGTH}–{CAMPAIGN_TITLE_MAX_LENGTH} символов</span>
              <span>{title.length}/{CAMPAIGN_TITLE_MAX_LENGTH}</span>
            </span>
          </label>

          <label className="block text-sm font-medium text-stone-700">
            Описание
            <textarea
              className="mt-2 min-h-56 w-full rounded-xl border border-stone-300 bg-white px-4 py-4 leading-7 outline-none transition placeholder:whitespace-pre-line placeholder:text-stone-400 focus:border-emerald-500 focus:ring-4 focus:ring-emerald-100"
              minLength={CAMPAIGN_DESCRIPTION_MIN_LENGTH}
              maxLength={CAMPAIGN_DESCRIPTION_MAX_LENGTH}
              placeholder={descriptionPlaceholder}
              value={description}
              onChange={(event) => setDescription(event.target.value)}
              required
            />
            <span className="mt-2 flex justify-between gap-3 text-xs font-normal text-stone-500">
              <span>{CAMPAIGN_DESCRIPTION_MIN_LENGTH}–{CAMPAIGN_DESCRIPTION_MAX_LENGTH} символов</span>
              <span>{description.length}/{CAMPAIGN_DESCRIPTION_MAX_LENGTH}</span>
            </span>
          </label>
        </div>

        <div className="grid gap-4 md:grid-cols-2">
          <label className="block text-sm font-medium text-stone-700">
            Цель
            <input className="mt-2 w-full rounded-xl border border-stone-300 bg-white px-4 py-3 outline-none transition focus:border-emerald-500 focus:ring-4 focus:ring-emerald-100" min="1" step="0.01" type="number" value={targetAmount} onChange={(event) => setTargetAmount(event.target.value)} required />
            {isLargeTargetAmount ? (
              <span className="mt-2 block rounded-2xl border border-amber-100 bg-amber-50 px-4 py-3 text-xs font-normal leading-5 text-amber-800">
                Крупные сборы проходят ручную проверку перед публикацией.
              </span>
            ) : null}
          </label>

          <label className="block text-sm font-medium text-stone-700">
            Категория
            <select className="mt-2 w-full rounded-xl border border-stone-300 bg-white px-4 py-3 outline-none transition focus:border-emerald-500 focus:ring-4 focus:ring-emerald-100" value={category} onChange={(event) => setCategory(event.target.value as CampaignCategory)}>
              {categories.map((item) => (
                <option key={item.value} value={item.value}>
                  {item.label}
                </option>
              ))}
            </select>
          </label>
        </div>

        <div className="space-y-3">
          <div>
            <p className="text-sm font-semibold text-stone-800">Загрузите главное фото вашей цели</p>
            <p className="mt-1 text-sm leading-6 text-stone-500">Можно добавить до 3 изображений. Первое фото станет главным после подключения загрузки на сервер.</p>
          </div>

          <label
            className="flex cursor-pointer flex-col items-center justify-center rounded-xl border border-dashed border-stone-300 bg-white px-5 py-8 text-center transition hover:border-emerald-500"
            onDragOver={(event) => event.preventDefault()}
            onDrop={handleCoverDrop}
          >
            <span className="text-sm font-semibold text-stone-800">Выберите фото или перетащите сюда</span>
            <span className="mt-2 text-xs leading-5 text-stone-500">JPG или PNG, максимум {maxCoverImages} изображения</span>
            <input className="sr-only" type="file" accept="image/jpeg,image/png" multiple onChange={handleCoverInputChange} disabled={coverImages.length >= maxCoverImages} />
          </label>

          {coverImages.length ? (
            <div className="grid gap-3 sm:grid-cols-3">
              {coverImages.map((image, index) => (
                <div key={image.id} className="overflow-hidden rounded-2xl border border-stone-200 bg-white">
                  <img src={image.url} alt="" className="aspect-[4/3] w-full object-cover" />
                  <div className="flex items-center justify-between gap-2 px-3 py-2">
                    <span className="truncate text-xs text-stone-600">{index === 0 ? "Главное фото" : image.name}</span>
                    <button className="shrink-0 rounded-full px-2 py-1 text-xs font-medium text-stone-500 transition hover:bg-stone-100 hover:text-stone-900" type="button" onClick={() => removeCoverImage(image.id)}>
                      Убрать
                    </button>
                  </div>
                </div>
              ))}
            </div>
          ) : null}
        </div>

        <div className="space-y-3 border-y border-stone-200 py-6">
          <div>
            <p className="text-sm font-semibold text-stone-800">Подтверждающие материалы (необязательно)</p>
            <p className="mt-1 text-sm leading-6 text-stone-500">Документы помогают вызвать больше доверия к сбору.</p>
          </div>

          <label className="inline-flex cursor-pointer items-center gap-2 rounded-full bg-white px-4 py-2 text-sm font-medium text-stone-700 shadow-sm ring-1 ring-stone-200 transition hover:text-emerald-800 hover:ring-emerald-200">
            <PaperclipIcon />
            Прикрепить файл
            <input className="sr-only" type="file" accept="application/pdf,image/jpeg,image/png" multiple onChange={handleDocumentsChange} />
          </label>

          {supportingDocuments.length ? (
            <div className="space-y-2">
              {supportingDocuments.map((document) => (
                <div key={document.id} className="flex items-center justify-between gap-3 rounded-2xl bg-white px-4 py-3 text-sm ring-1 ring-stone-200">
                  <div className="min-w-0">
                    <p className="truncate font-medium text-stone-800">{document.name}</p>
                    <p className="mt-1 text-xs text-stone-500">{formatFileSize(document.size)}</p>
                  </div>
                  <button className="shrink-0 rounded-full px-3 py-1 text-xs font-medium text-stone-500 transition hover:bg-stone-100 hover:text-stone-900" type="button" onClick={() => removeSupportingDocument(document.id)}>
                    Убрать
                  </button>
                </div>
              ))}
            </div>
          ) : null}
        </div>

        <button className="rounded-full bg-stone-950 px-5 py-3 font-medium text-white transition hover:bg-emerald-700 disabled:cursor-not-allowed disabled:opacity-70" disabled={isSubmitting} type="submit">
          {isSubmitting ? "Создаем..." : "Открыть сбор"}
        </button>
      </form>

      {error ? <UserErrorAlert error={error} /> : null}
    </section>
  );
}

function formatFileSize(size: number) {
  if (size < 1024 * 1024) {
    return `${Math.max(1, Math.round(size / 1024))} КБ`;
  }

  return `${(size / 1024 / 1024).toFixed(1)} МБ`;
}

function PaperclipIcon() {
  return (
    <svg aria-hidden="true" className="h-4 w-4" fill="none" viewBox="0 0 24 24" stroke="currentColor" strokeWidth="1.8">
      <path strokeLinecap="round" strokeLinejoin="round" d="m21.4 11.1-8.5 8.5a6 6 0 0 1-8.5-8.5l9.2-9.2a4 4 0 0 1 5.7 5.7l-9.2 9.2a2 2 0 0 1-2.8-2.8l8.5-8.5" />
    </svg>
  );
}
