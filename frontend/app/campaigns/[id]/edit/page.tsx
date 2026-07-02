"use client";

import Link from "next/link";
import { FormEvent, useEffect, useState } from "react";
import { useRouter } from "next/navigation";
import { fetchCampaign, updateCampaign } from "@/lib/api";
import type { CampaignDetail } from "@/lib/types";
import { CAMPAIGN_DESCRIPTION_MAX_LENGTH, CAMPAIGN_DESCRIPTION_MIN_LENGTH } from "@/lib/validation";

export default function EditCampaignPage({ params }: { params: { id: string } }) {
  const router = useRouter();
  const [campaign, setCampaign] = useState<CampaignDetail | null>(null);
  const [description, setDescription] = useState("");
  const [targetAmount, setTargetAmount] = useState("");
  const [coverImageUrl, setCoverImageUrl] = useState("");
  const [message, setMessage] = useState<string | null>(null);
  const [isSaving, setIsSaving] = useState(false);

  useEffect(() => {
    fetchCampaign(params.id)
      .then((item) => {
        setCampaign(item);
        setDescription(item.description);
        setTargetAmount(item.target_amount);
        setCoverImageUrl(item.cover_image_url ?? "");
      })
      .catch((error) => setMessage(error instanceof Error ? error.message : "Не удалось загрузить сбор."));
  }, [params.id]);

  async function handleSubmit(event: FormEvent<HTMLFormElement>) {
    event.preventDefault();
    setIsSaving(true);
    setMessage(null);
    try {
      await updateCampaign(params.id, {
        description,
        target_amount: Number(targetAmount),
        cover_image_url: coverImageUrl || null,
      });
      router.push("/dashboard");
    } catch (error) {
      setMessage(error instanceof Error ? error.message : "Не удалось сохранить изменения.");
    } finally {
      setIsSaving(false);
    }
  }

  if (!campaign) return <div className="mx-auto max-w-3xl rounded-[28px] border border-stone-200 bg-white p-6 text-sm text-stone-600 shadow-sm">{message ?? "Загружаем сбор..."}</div>;

  if (campaign.status !== "ACTIVE") {
    return (
      <section className="mx-auto max-w-3xl rounded-[30px] border border-stone-200 bg-white p-6 shadow-[0_22px_70px_rgba(28,25,23,0.09)] md:p-8">
        <p className="text-xs font-semibold uppercase tracking-[0.18em] text-amber-700">редактирование недоступно</p>
        <h1 className="mt-3 text-3xl font-semibold tracking-tight text-stone-950">{campaign.title}</h1>
        <p className="mt-3 text-sm leading-6 text-stone-600">
          Этот сбор уже перешёл в следующий этап. Редактировать можно только активные сборы.
        </p>
        <div className="mt-6 flex flex-wrap gap-3">
          <Link href={`/campaigns/${campaign.id}`} className="rounded-full bg-stone-950 px-5 py-3 text-sm font-semibold text-white transition hover:bg-emerald-700">Открыть страницу сбора</Link>
          <Link href="/dashboard" className="rounded-full bg-stone-100 px-5 py-3 text-sm font-semibold text-stone-700 transition hover:bg-stone-200">Вернуться в кабинет</Link>
        </div>
      </section>
    );
  }

  return (
    <section className="mx-auto max-w-3xl">
      <Link href="/dashboard" className="text-sm font-semibold text-emerald-800 hover:text-emerald-950">← Вернуться в кабинет</Link>
      <form onSubmit={handleSubmit} className="mt-4 space-y-6 rounded-[30px] border border-stone-200 bg-white p-6 shadow-[0_22px_70px_rgba(28,25,23,0.09)] md:p-8">
        <div>
          <p className="text-xs font-semibold uppercase tracking-[0.18em] text-emerald-700">управление сбором</p>
          <h1 className="mt-3 text-3xl font-semibold tracking-tight text-stone-950">{campaign.title}</h1>
          <p className="mt-2 text-sm leading-6 text-stone-600">Обновите ключевую информацию. Изменения сразу появятся на странице сбора.</p>
        </div>

        <label id="description" className="block scroll-mt-24 text-sm font-semibold text-stone-700">
          Описание
          <textarea className="mt-2 min-h-48 w-full rounded-2xl border border-stone-200 bg-stone-50 px-4 py-3 font-normal leading-6 outline-none transition focus:border-emerald-500 focus:bg-white focus:ring-4 focus:ring-emerald-100" minLength={CAMPAIGN_DESCRIPTION_MIN_LENGTH} maxLength={CAMPAIGN_DESCRIPTION_MAX_LENGTH} value={description} onChange={(event) => setDescription(event.target.value)} />
          <span className="mt-2 flex justify-between gap-3 text-xs font-normal text-stone-500">
            <span>{CAMPAIGN_DESCRIPTION_MIN_LENGTH}–{CAMPAIGN_DESCRIPTION_MAX_LENGTH} символов</span>
            <span>{description.length}/{CAMPAIGN_DESCRIPTION_MAX_LENGTH}</span>
          </span>
        </label>

        <label id="target" className="block scroll-mt-24 text-sm font-semibold text-stone-700">
          Цель, ₽
          <input className="mt-2 w-full rounded-2xl border border-stone-200 bg-stone-50 px-4 py-3.5 text-lg font-semibold outline-none transition focus:border-emerald-500 focus:bg-white focus:ring-4 focus:ring-emerald-100" min="1" step="0.01" type="number" value={targetAmount} onChange={(event) => setTargetAmount(event.target.value)} />
        </label>

        <label id="cover" className="block scroll-mt-24 text-sm font-semibold text-stone-700">
          Ссылка на фотографию
          <input className="mt-2 w-full rounded-2xl border border-stone-200 bg-stone-50 px-4 py-3.5 font-normal outline-none transition focus:border-emerald-500 focus:bg-white focus:ring-4 focus:ring-emerald-100" placeholder="https://..." type="url" value={coverImageUrl} onChange={(event) => setCoverImageUrl(event.target.value)} />
        </label>

        {message ? <p className="rounded-2xl bg-rose-50 px-4 py-3 text-sm text-rose-800">{message}</p> : null}
        <div className="flex flex-wrap gap-3">
          <button className="rounded-full bg-stone-950 px-5 py-3 text-sm font-semibold text-white transition hover:bg-emerald-700 disabled:opacity-60" disabled={isSaving} type="submit">{isSaving ? "Сохраняем..." : "Сохранить изменения"}</button>
          <Link href={`/campaigns/${campaign.id}`} className="rounded-full bg-stone-100 px-5 py-3 text-sm font-semibold text-stone-700 transition hover:bg-stone-200">Открыть страницу сбора</Link>
        </div>
      </form>
    </section>
  );
}
