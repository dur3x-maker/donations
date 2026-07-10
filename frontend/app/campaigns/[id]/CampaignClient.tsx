"use client";

import { FormEvent, useCallback, useEffect, useRef, useState } from "react";
import Link from "next/link";
import { useRouter } from "next/navigation";
import { ProgressBar } from "@/app/components/ProgressBar";
import { CampaignDonationsList } from "./CampaignDonationsList";
import { PhotoUploader, type PendingPhoto } from "./PhotoUploader";
import { createCampaignUpdate, createCompletionReport, donate, fetchAuthorReputation, fetchCampaign, fetchCampaignSubscription, fetchCampaignUpdates, fetchCompletionReport, fetchRecentDonations, fetchWithdrawalInfo, reportCampaign, subscribeToCampaign, unsubscribeFromCampaign, uploadStoryPhoto } from "@/lib/api";
import { amountLeft, formatDate, formatMoney } from "@/lib/format";
import { useLiveRefresh } from "@/lib/use-live-refresh";
import { subscribeCampaignUpdates, type RealtimeStatus } from "@/lib/ws";
import { useAuth } from "@/components/providers/auth-provider";
import type { AuthorReputation, CampaignCompletionReport, CampaignDetail, CampaignUpdateItem, RecentDonation, WithdrawalInfo } from "@/lib/types";

const quickAmounts = [100, 500, 1000];
const MIN_DONATION_AMOUNT = 100;
const categoryLabels: Record<string, string> = {
  medical: "лечение",
  education: "образование",
  emergency: "срочно",
  pets: "животные",
  community: "сообщество",
  personal: "личное",
  other: "другое",
};

export function CampaignClient({ initialCampaign }: { initialCampaign: CampaignDetail }) {
  const router = useRouter();
  const { user } = useAuth();
  const [campaign, setCampaign] = useState(initialCampaign);
  const [donations, setDonations] = useState<RecentDonation[]>([]);
  const donationsCountRef = useRef(3);
  const [hasMoreDonations, setHasMoreDonations] = useState(false);
  const [isLoadingMoreDonations, setIsLoadingMoreDonations] = useState(false);
  const [updates, setUpdates] = useState<CampaignUpdateItem[]>([]);
  const [completionReport, setCompletionReport] = useState<CampaignCompletionReport | null>(null);
  const [authorReputation, setAuthorReputation] = useState<AuthorReputation | null>(null);
  const [newDonationId, setNewDonationId] = useState<string | null>(null);
  const [amount, setAmount] = useState(String(MIN_DONATION_AMOUNT));
  const [paymentState, setPaymentState] = useState<"idle" | "processing" | "success" | "failed">("idle");
  const [message, setMessage] = useState<string | null>(null);
  const [wsMessage, setWsMessage] = useState<string | null>(null);
  const [wsStatus, setWsStatus] = useState<RealtimeStatus>("disconnected");
  const [shareMessage, setShareMessage] = useState<string | null>(null);
  const [reportMessage, setReportMessage] = useState<string | null>(null);
  const [isReportOpen, setIsReportOpen] = useState(false);
  const [reportReason, setReportReason] = useState("scam");
  const [reportDetails, setReportDetails] = useState("");
  const [isReporting, setIsReporting] = useState(false);
  const [updateTitle, setUpdateTitle] = useState("");
  const [updateContent, setUpdateContent] = useState("");
  const [updatePhotos, setUpdatePhotos] = useState<PendingPhoto[]>([]);
  const [isPublishingUpdate, setIsPublishingUpdate] = useState(false);
  const [updateMessage, setUpdateMessage] = useState<string | null>(null);
  const [gratitudeText, setGratitudeText] = useState("");
  const [completionPhotos, setCompletionPhotos] = useState<PendingPhoto[]>([]);
  const [isPublishingCompletion, setIsPublishingCompletion] = useState(false);
  const [completionMessage, setCompletionMessage] = useState<string | null>(null);
  const [isSubscribed, setIsSubscribed] = useState(false);
  const [isSubscriptionLoading, setIsSubscriptionLoading] = useState(false);
  const [subscriptionMessage, setSubscriptionMessage] = useState<string | null>(null);
  const [withdrawalInfo, setWithdrawalInfo] = useState<WithdrawalInfo | null>(null);
  const [isWithdrawalOpen, setIsWithdrawalOpen] = useState(false);
  const isOwner = user?.id === campaign.owner_id;
  const isCompleted = campaign.status === "COMPLETED";
  const canDonate = campaign.status === "ACTIVE" && Number(campaign.current_amount) < Number(campaign.target_amount);
  const donationHint = isCompleted
    ? "История завершена. Спасибо всем участникам."
    : "Сбор достиг цели. Сейчас автор готовит итоговый отчет.";
  const amountNumber = Number(amount);
  const remainingAmount = amountLeft(campaign.current_amount, campaign.target_amount);

  const refresh = useCallback(async () => {
    const [freshCampaign, freshDonations, freshUpdates, freshReport] = await Promise.all([
      fetchCampaign(initialCampaign.id),
      fetchRecentDonations(initialCampaign.id, { limit: Math.max(3, donationsCountRef.current) }),
      fetchCampaignUpdates(initialCampaign.id),
      fetchCompletionReport(initialCampaign.id).catch(() => null),
    ]);
    setCampaign(freshCampaign);
    setDonations(freshDonations.items);
    setHasMoreDonations(freshDonations.has_more);
    setUpdates(freshUpdates);
    setCompletionReport(freshReport);
  }, [initialCampaign.id]);

  useEffect(() => {
    donationsCountRef.current = donations.length;
  }, [donations.length]);

  useEffect(() => {
    Promise.all([fetchRecentDonations(campaign.id, { limit: 3 }), fetchCampaignUpdates(campaign.id), fetchCompletionReport(campaign.id).catch(() => null)])
      .then(([freshDonations, freshUpdates, freshReport]) => {
        setDonations(freshDonations.items);
        setHasMoreDonations(freshDonations.has_more);
        setUpdates(freshUpdates);
        setCompletionReport(freshReport);
      })
      .catch(() => {
        setDonations([]);
        setHasMoreDonations(false);
        setUpdates([]);
        setCompletionReport(null);
      });
  }, [campaign.id]);

  useEffect(() => {
    fetchAuthorReputation(campaign.owner_id).then(setAuthorReputation).catch(() => setAuthorReputation(null));
  }, [campaign.owner_id]);

  useEffect(() => {
    if (!user) {
      setIsSubscribed(false);
      return;
    }
    fetchCampaignSubscription(campaign.id)
      .then((subscription) => setIsSubscribed(subscription.is_subscribed))
      .catch(() => setIsSubscribed(false));
  }, [campaign.id, user]);

  useEffect(() => {
    if (!isOwner) {
      setWithdrawalInfo(null);
      return;
    }
    fetchWithdrawalInfo(campaign.id)
      .then(setWithdrawalInfo)
      .catch(() => setWithdrawalInfo(null));
  }, [campaign.id, campaign.status, campaign.current_amount, isOwner]);

  useLiveRefresh(refresh, wsStatus === "connected");

  useEffect(() => {
    return subscribeCampaignUpdates(
      campaign.id,
      (event) => {
        if (event.type === "campaign_lifecycle_changed") {
          refresh().catch(() => undefined);
          router.refresh();
          return;
        }
        setCampaign((value) => ({
          ...value,
          current_amount: event.current_amount,
          target_amount: event.goal_amount,
          progress_percentage: event.progress_percentage,
          contributors_count: event.contributors_count,
        }));
        setDonations((current) => [event.donation, ...current.filter((item) => item.id !== event.donation.id)]);
        setNewDonationId(event.donation.id);
        window.setTimeout(() => setNewDonationId((current) => (current === event.donation.id ? null : current)), 1400);
      },
      (status) => {
        setWsStatus(status);
        setWsMessage(status === "connected" ? null : "Живые обновления переподключаются. Поддержка все равно работает.");
      },
    );
  }, [campaign.id, refresh, router]);

  async function loadMoreDonations() {
    if (isLoadingMoreDonations || !hasMoreDonations) return;
    setIsLoadingMoreDonations(true);
    try {
      const page = await fetchRecentDonations(campaign.id, { offset: donations.length, limit: 10 });
      setDonations((current) => {
        const existingIds = new Set(current.map((item) => item.id));
        return [...current, ...page.items.filter((item) => !existingIds.has(item.id))];
      });
      setHasMoreDonations(page.has_more);
    } finally {
      setIsLoadingMoreDonations(false);
    }
  }

  async function handleSubmit(event: FormEvent<HTMLFormElement>) {
    event.preventDefault();
    if (!Number.isFinite(amountNumber) || amountNumber < MIN_DONATION_AMOUNT) {
      setPaymentState("failed");
      setMessage("Минимальная сумма поддержки — 100 ₽.");
      return;
    }
    if (!canDonate) {
      setPaymentState("failed");
      setMessage(donationHint);
      return;
    }
    setMessage(null);
    setPaymentState("processing");

    try {
      const anonymousToken = localStorage.getItem("anonymous_token") ?? undefined;
      const result = await donate(campaign.id, {
        amount: Number(amount),
        anonymous_token: anonymousToken,
      });

      if (result.anonymous_token) {
        localStorage.setItem("anonymous_token", result.anonymous_token);
      }

      setPaymentState(result.status === "succeeded" ? "success" : "processing");
      setMessage(result.status === "succeeded" ? "Спасибо, вклад подтвержден и уже учтен." : "Платеж создан и ожидает подтверждения.");
      if (user && result.status === "succeeded") {
        setIsSubscribed(true);
        if (result.subscription_created) {
          setSubscriptionMessage("Вы автоматически подписались на обновления этой истории.");
        }
      }
    } catch (error) {
      setPaymentState("failed");
      setMessage(error instanceof Error ? error.message : "Не получилось отправить вклад. Попробуйте еще раз.");
    }
  }

  async function handleShare() {
    const url = window.location.href;
    const text = `Поддержите этот сбор на TipForTea: ${campaign.title}`;

    try {
      if (navigator.share) {
        await navigator.share({ title: campaign.title, text, url });
        return;
      }
      await navigator.clipboard.writeText(`${text}\n${url}`);
      setShareMessage("Ссылка скопирована.");
    } catch {
      setShareMessage("Сейчас не получилось поделиться.");
    }
  }

  async function handleSubscriptionChange() {
    if (!user) {
      router.push(`/login?next=/campaigns/${campaign.id}`);
      return;
    }
    setIsSubscriptionLoading(true);
    setSubscriptionMessage(null);
    try {
      const subscription = isSubscribed
        ? await unsubscribeFromCampaign(campaign.id)
        : await subscribeToCampaign(campaign.id);
      setIsSubscribed(subscription.is_subscribed);
      setSubscriptionMessage(subscription.is_subscribed ? "Вы следите за этой историей." : "Вы отписались от обновлений истории.");
    } catch (error) {
      setSubscriptionMessage(error instanceof Error ? error.message : "Не удалось изменить подписку.");
    } finally {
      setIsSubscriptionLoading(false);
    }
  }

  async function handleReportSubmit(event: FormEvent<HTMLFormElement>) {
    event.preventDefault();
    setIsReporting(true);
    setReportMessage(null);
    try {
      await reportCampaign(campaign.id, { reason: reportReason, details: reportDetails || undefined });
      setReportMessage("Спасибо. Жалоба отправлена на проверку.");
      setIsReportOpen(false);
      setReportDetails("");
    } catch (error) {
      setReportMessage(error instanceof Error ? error.message : "Не получилось отправить жалобу.");
    } finally {
      setIsReporting(false);
    }
  }

  async function handleUpdateSubmit(event: FormEvent<HTMLFormElement>) {
    event.preventDefault();
    setIsPublishingUpdate(true);
    setUpdateMessage(null);
    try {
      const photoUrls = await uploadPhotos(updatePhotos);
      const created = await createCampaignUpdate(campaign.id, {
        title: updateTitle,
        content: updateContent,
        photos: photoUrls,
      });
      setUpdates((current) => [created, ...current]);
      setUpdateTitle("");
      setUpdateContent("");
      clearPendingPhotos(updatePhotos);
      setUpdatePhotos([]);
      setUpdateMessage("Обновление опубликовано.");
    } catch (error) {
      setUpdateMessage(error instanceof Error ? error.message : "Не получилось опубликовать обновление.");
    } finally {
      setIsPublishingUpdate(false);
    }
  }

  async function handleCompletionSubmit(event: FormEvent<HTMLFormElement>) {
    event.preventDefault();
    setIsPublishingCompletion(true);
    setCompletionMessage(null);
    try {
      const photoUrls = await uploadPhotos(completionPhotos);
      const created = await createCompletionReport(campaign.id, {
        gratitude_text: gratitudeText,
        photos: photoUrls,
      });
      setCompletionReport(created);
      setCampaign((current) => ({
        ...current,
        status: "COMPLETED",
        has_completion_report: true,
        report_completed_at: created.created_at,
      }));
      setGratitudeText("");
      clearPendingPhotos(completionPhotos);
      setCompletionPhotos([]);
      setCompletionMessage("Итоговый отчет опубликован.");
      fetchAuthorReputation(campaign.owner_id).then(setAuthorReputation).catch(() => setAuthorReputation(null));
      router.refresh();
    } catch (error) {
      setCompletionMessage(error instanceof Error ? error.message : "Не удалось опубликовать итоговый отчет.");
    } finally {
      setIsPublishingCompletion(false);
    }
  }

  if (!campaign.is_active) {
    return (
      <section className="mx-auto max-w-3xl rounded-[32px] bg-stone-950 p-6 text-white shadow-[0_24px_80px_rgba(28,25,23,0.20)] md:p-10">
        <p className="text-sm font-medium uppercase tracking-[0.18em] text-emerald-300">на проверке</p>
        <h1 className="mt-3 text-3xl font-semibold tracking-tight md:text-5xl">Этот сбор временно недоступен.</h1>
        <p className="mt-4 max-w-2xl leading-7 text-stone-300">Команда модерации внимательно смотрит ситуацию. Спасибо, что помогаете сохранять площадку безопасной.</p>
      </section>
    );
  }

  return (
    <div className="grid gap-8 lg:grid-cols-[minmax(0,1fr)_400px] lg:items-start">
      <section className="overflow-hidden rounded-[34px] border border-stone-200 bg-white shadow-[0_24px_90px_rgba(28,25,23,0.10)]">
        <div className="relative min-h-[390px] overflow-hidden bg-stone-100 md:aspect-[16/8.6] md:min-h-0">
          {campaign.cover_image_url ? <img src={campaign.cover_image_url} alt="" className="absolute inset-0 h-full w-full object-cover" /> : null}
          <div className="absolute inset-0 bg-[linear-gradient(90deg,rgba(28,25,23,0.82),rgba(28,25,23,0.42)_52%,rgba(28,25,23,0.16)),linear-gradient(0deg,rgba(28,25,23,0.92),rgba(28,25,23,0.38)_58%,rgba(28,25,23,0.10))]" />
          <div className="absolute inset-x-0 bottom-0 h-2/3 bg-[linear-gradient(0deg,rgba(28,25,23,0.92),rgba(28,25,23,0))]" />
          <div className="absolute inset-x-0 bottom-0 p-5 md:p-9">
            <div className="mb-5 flex flex-wrap items-center gap-x-3 gap-y-2 text-xs font-semibold uppercase tracking-[0.14em] text-stone-200/80">
              <span>{categoryLabels[campaign.category] ?? campaign.category}</span>
              {campaign.is_verified ? <span className="text-emerald-200">проверено</span> : null}
              <span>{formatDate(campaign.created_at)}</span>
            </div>
            <h1 className="max-w-4xl text-4xl font-semibold leading-[1.02] tracking-[-0.035em] text-white drop-shadow-[0_4px_22px_rgba(0,0,0,0.55)] md:text-7xl">
              {campaign.title}
            </h1>
            <p className="mt-5 text-sm text-stone-200/85">
              История от{" "}
              {campaign.owner?.username ? (
                <Link href={`/u/${campaign.owner.username}`} className="font-semibold text-white underline decoration-white/30 underline-offset-4 hover:decoration-white">
                  {campaign.owner.username}
                </Link>
              ) : (
                "сообщество"
              )}
            </p>
          </div>
        </div>

        <div className="space-y-10 p-5 md:p-8">
          {campaign.status !== "ACTIVE" && Number(campaign.current_amount) >= Number(campaign.target_amount) ? (
            <section className="rounded-[28px] border border-amber-200 bg-amber-50 p-5 shadow-[0_18px_55px_rgba(146,64,14,0.10)] md:p-6">
              <p className="text-xs font-semibold uppercase tracking-[0.18em] text-amber-800">следующий шаг</p>
              <h2 className="mt-2 text-2xl font-semibold text-stone-950">История достигла цели.</h2>
              <p className="mt-2 max-w-2xl leading-7 text-stone-700">
                Средства будут доступны для вывода через банк-партнёр.
              </p>
              {isOwner ? (
                <div className="mt-4 flex flex-wrap gap-3">
                  {campaign.status === "AWAITING_REPORT" ? <a href="#completion-report" className="inline-flex rounded-full bg-stone-950 px-5 py-3 font-semibold text-white hover:bg-emerald-800">Перейти к итоговому отчёту</a> : null}
                  {withdrawalInfo?.available ? (
                    <button className="rounded-full bg-emerald-700 px-5 py-3 font-semibold text-white transition hover:bg-emerald-800" onClick={() => setIsWithdrawalOpen(true)} type="button">
                      Вывести средства
                    </button>
                  ) : null}
                </div>
              ) : null}
            </section>
          ) : null}
          <section className="rounded-[30px] border border-stone-200 bg-stone-50/80 p-5 md:p-7">
            <div className="mb-6 grid gap-5 md:grid-cols-[1.15fr_0.85fr] md:items-end">
              <div>
                <p className="text-xs font-semibold uppercase tracking-[0.18em] text-emerald-700">осталось собрать</p>
                <p className="mt-2 text-4xl font-semibold tracking-[-0.03em] text-stone-950 md:text-5xl">{formatMoney(remainingAmount)}</p>
                <p className="mt-3 text-sm leading-6 text-stone-500">Уже собрано {formatMoney(campaign.current_amount)} из {formatMoney(campaign.target_amount)}.</p>
              </div>
              <div className="text-left md:text-right">
                <p className="text-sm text-stone-500">цель {formatMoney(campaign.target_amount)}</p>
                <p className="mt-1 font-semibold text-emerald-700">{campaign.progress_percentage}% цели</p>
                <p className="mt-1 text-sm text-stone-500">{campaign.contributors_count} участников</p>
              </div>
            </div>
            <ProgressBar value={campaign.progress_percentage} className="h-4" />
          </section>

          <article className="mx-auto max-w-[68ch] whitespace-pre-wrap text-[17px] leading-9 text-stone-700 md:text-lg md:leading-9">{campaign.description}</article>

          <FutureUseOfFundsSection items={[]} />

          <StoryTrustPause />

          <CompletionReportSection
            campaign={campaign}
            report={completionReport}
            isOwner={isOwner}
            gratitudeText={gratitudeText}
            photos={completionPhotos}
            isPublishing={isPublishingCompletion}
            message={completionMessage}
            onGratitudeChange={setGratitudeText}
            onPhotosChange={setCompletionPhotos}
            onSubmit={handleCompletionSubmit}
          />

          <CampaignUpdatesSection
            campaignStatus={campaign.status}
            updates={updates}
            isOwner={isOwner}
            title={updateTitle}
            content={updateContent}
            photos={updatePhotos}
            isPublishing={isPublishingUpdate}
            message={updateMessage}
            onTitleChange={setUpdateTitle}
            onContentChange={setUpdateContent}
            onPhotosChange={setUpdatePhotos}
            onSubmit={handleUpdateSubmit}
          />

          {wsMessage ? <p className="rounded-2xl bg-amber-50 px-4 py-3 text-sm text-amber-900">{wsMessage}</p> : null}
          <CampaignDonationsList
            donations={donations}
            hasMore={hasMoreDonations}
            isLoadingMore={isLoadingMoreDonations}
            newDonationId={newDonationId}
            onLoadMore={loadMoreDonations}
          />

          <ShareSection
            shareMessage={shareMessage}
            reportMessage={reportMessage}
            onShare={handleShare}
            onReport={() => setIsReportOpen(true)}
          />
        </div>
      </section>

      <aside className="space-y-4 lg:sticky lg:top-24">
        {canDonate ? (
          <form onSubmit={handleSubmit} className="space-y-5 rounded-[30px] border border-emerald-100 bg-white p-5 shadow-[0_28px_100px_rgba(28,25,23,0.16)]">
            <div>
              <p className="text-xs font-semibold uppercase tracking-[0.18em] text-emerald-700">поддержка</p>
              <h2 className="mt-2 text-2xl font-semibold leading-tight tracking-[-0.02em] text-stone-950">Поддержать сбор</h2>
            </div>
            <div className="grid grid-cols-3 gap-2">
              {quickAmounts.map((value) => (
                <button
                  key={value}
                  type="button"
                  onClick={() => setAmount(String(value))}
                  className={`min-h-11 rounded-full px-3 py-2 text-sm font-semibold transition ${amount === String(value) ? "bg-stone-950 text-white" : "bg-stone-100 text-stone-700 hover:bg-stone-200"}`}
                >
                  {value}
                </button>
              ))}
            </div>
            <label className="block text-sm font-semibold text-stone-700">
              Сумма
              <input
                className="mt-2 w-full rounded-2xl border border-stone-200 bg-stone-50 px-4 py-3.5 text-lg font-semibold outline-none transition focus:border-emerald-500 focus:bg-white focus:ring-4 focus:ring-emerald-100"
                min={MIN_DONATION_AMOUNT}
                step="0.01"
                type="number"
                value={amount}
                onChange={(event) => setAmount(event.target.value)}
              />
            </label>
            {amount !== "" && Number.isFinite(amountNumber) && amountNumber < MIN_DONATION_AMOUNT ? (
              <p className="text-sm text-rose-700">Минимальная сумма поддержки — 100 ₽.</p>
            ) : null}
            <button className="min-h-12 w-full rounded-full bg-emerald-700 px-5 py-3 font-semibold text-white shadow-lg shadow-emerald-800/15 transition hover:bg-emerald-800 disabled:cursor-not-allowed disabled:opacity-70" disabled={paymentState === "processing"} type="submit">
              {paymentState === "processing" ? "Отправляем..." : "Поддержать"}
            </button>
            {message ? <p className="break-words text-sm text-stone-600">{message}</p> : null}
          </form>
        ) : (
          <section className="rounded-[30px] border border-stone-200 bg-white p-5 shadow-[0_24px_90px_rgba(28,25,23,0.12)]">
            <p className="text-xs font-semibold uppercase tracking-[0.18em] text-emerald-700">поддержка</p>
            <h2 className="mt-2 text-2xl font-semibold leading-tight tracking-[-0.02em] text-stone-950">
              {isCompleted ? "История завершена" : "Сбор достиг цели"}
            </h2>
            <p className="mt-2 text-sm leading-6 text-stone-500">{donationHint}</p>
          </section>
        )}

        {!isOwner ? (
          <section className="rounded-[24px] border border-emerald-100 bg-emerald-50/70 p-4">
            <p className="text-sm font-semibold text-stone-950">
              {isSubscribed ? "Вы следите за этой историей" : "Получайте новости этой истории"}
            </p>
            <p className="mt-1 text-sm leading-6 text-stone-600">
              {isSubscribed ? "Мы сообщим об обновлениях, новых фотографиях и завершении истории." : "Подпишитесь, чтобы не пропустить обновления автора."}
            </p>
            <button
              className={`mt-3 rounded-full px-4 py-2 text-sm font-semibold transition disabled:opacity-60 ${isSubscribed ? "bg-white text-stone-700 ring-1 ring-stone-200 hover:bg-stone-50" : "bg-emerald-700 text-white hover:bg-emerald-800"}`}
              disabled={isSubscriptionLoading}
              onClick={handleSubscriptionChange}
              type="button"
            >
              {isSubscriptionLoading ? "Сохраняем..." : isSubscribed ? "Не следить" : "Следить за историей"}
            </button>
            {subscriptionMessage ? <p className="mt-2 text-xs leading-5 text-stone-600">{subscriptionMessage}</p> : null}
          </section>
        ) : null}

        <AuthorReputationCard campaign={campaign} reputation={authorReputation} />
      </aside>

      {isReportOpen ? (
        <div className="fixed inset-0 z-50 flex items-center justify-center bg-stone-950/40 p-4 backdrop-blur-sm">
          <form onSubmit={handleReportSubmit} className="w-full max-w-md space-y-4 rounded-[28px] bg-white p-5 shadow-[0_24px_90px_rgba(28,25,23,0.25)]">
            <div>
              <h2 className="text-2xl font-semibold tracking-[-0.02em] text-stone-950">Пожаловаться на сбор</h2>
              <p className="mt-2 text-sm leading-6 text-stone-600">Расскажите, что выглядит сомнительно. Это посмотрит человек.</p>
            </div>
            <label className="block text-sm font-semibold text-stone-700">
              Причина
              <select className="mt-2 w-full rounded-2xl border border-stone-200 bg-stone-50 px-4 py-3 outline-none transition focus:border-emerald-500 focus:bg-white" value={reportReason} onChange={(event) => setReportReason(event.target.value)}>
                <option value="scam">Похоже на обман</option>
                <option value="unsafe">Небезопасный контент</option>
                <option value="duplicate">Повторяющийся сбор</option>
                <option value="other">Другое</option>
              </select>
            </label>
            <label className="block text-sm font-semibold text-stone-700">
              Детали
              <textarea className="mt-2 min-h-28 w-full rounded-2xl border border-stone-200 bg-stone-50 px-4 py-3 outline-none transition focus:border-emerald-500 focus:bg-white" value={reportDetails} onChange={(event) => setReportDetails(event.target.value)} />
            </label>
            <div className="flex flex-wrap gap-3">
              <button className="rounded-full bg-stone-950 px-5 py-3 font-semibold text-white transition hover:bg-emerald-700 disabled:opacity-70" disabled={isReporting} type="submit">
                {isReporting ? "Отправляем..." : "Отправить"}
              </button>
              <button className="rounded-full bg-stone-100 px-5 py-3 font-semibold text-stone-700 transition hover:bg-stone-200" type="button" onClick={() => setIsReportOpen(false)}>
                Отмена
              </button>
            </div>
          </form>
        </div>
      ) : null}

      {isWithdrawalOpen ? (
        <div className="fixed inset-0 z-50 flex items-center justify-center bg-stone-950/40 p-4 backdrop-blur-sm">
          <section
            aria-labelledby="withdrawal-demo-title"
            aria-modal="true"
            className="w-full max-w-lg rounded-[28px] bg-white p-6 shadow-[0_24px_90px_rgba(28,25,23,0.25)] md:p-7"
            role="dialog"
          >
            <p className="text-xs font-semibold uppercase tracking-[0.18em] text-emerald-700">демонстрационный режим</p>
            <h2 id="withdrawal-demo-title" className="mt-2 text-2xl font-semibold text-stone-950">Вывод средств</h2>
            <p className="mt-4 leading-7 text-stone-700">
              В будущем здесь будет открытие счёта через банк-партнёр.
            </p>
            <p className="mt-2 leading-7 text-stone-700">
              Сейчас функция работает в демонстрационном режиме.
            </p>
            <p className="mt-4 rounded-2xl bg-stone-50 px-4 py-3 text-sm leading-6 text-stone-600">
              После подключения банка здесь появится процесс открытия счёта и вывода собранных средств.
            </p>
            <div className="mt-6 flex flex-wrap gap-3">
              <button className="rounded-full bg-emerald-700 px-5 py-3 font-semibold text-white hover:bg-emerald-800" onClick={() => setIsWithdrawalOpen(false)} type="button">
                Понятно
              </button>
              <button className="rounded-full bg-stone-100 px-5 py-3 font-semibold text-stone-700 hover:bg-stone-200" onClick={() => setIsWithdrawalOpen(false)} type="button">
                Закрыть
              </button>
            </div>
          </section>
        </div>
      ) : null}
    </div>
  );
}

function CompletionReportSection({
  campaign,
  report,
  isOwner,
  gratitudeText,
  photos,
  isPublishing,
  message,
  onGratitudeChange,
  onPhotosChange,
  onSubmit,
}: {
  campaign: CampaignDetail;
  report: CampaignCompletionReport | null;
  isOwner: boolean;
  gratitudeText: string;
  photos: PendingPhoto[];
  isPublishing: boolean;
  message: string | null;
  onGratitudeChange: (value: string) => void;
  onPhotosChange: (value: PendingPhoto[]) => void;
  onSubmit: (event: FormEvent<HTMLFormElement>) => void;
}) {
  if (report) {
    return (
      <section className="rounded-[28px] border border-emerald-200 bg-[linear-gradient(145deg,#ecfdf5,#ffffff)] p-5 shadow-[0_18px_55px_rgba(6,78,59,0.10)] md:p-6">
        <p className="text-xs font-semibold uppercase tracking-[0.18em] text-emerald-700">итог</p>
        <h2 className="mt-2 text-2xl font-semibold tracking-[-0.02em] text-stone-950">История завершена</h2>
        <div className="mt-4 grid gap-3 sm:grid-cols-3">
          <ResultMetric label="Собрано" value={formatMoney(report.raised_amount)} />
          <ResultMetric label="Участников" value={String(report.supporters_count)} />
          <ResultMetric label="Завершена" value={formatDate(report.created_at)} />
        </div>
        <p className="mt-5 whitespace-pre-wrap text-sm leading-7 text-stone-700">{report.gratitude_text}</p>
        {report.photos.length ? (
          <div className="mt-5 grid gap-3 sm:grid-cols-2">
            {report.photos.map((photo) => (
              <img key={photo.id} src={photo.image_url} alt="" className="h-52 w-full rounded-[22px] object-cover" />
            ))}
          </div>
        ) : null}
        <div className="mt-6 rounded-[22px] bg-white/80 p-4 ring-1 ring-emerald-100">
          <h3 className="text-lg font-semibold text-stone-950">Стена благодарности</h3>
          <p className="mt-1 text-sm leading-6 text-stone-600">Спасибо людям, которые помогли этой истории состояться.</p>
          <div className="mt-4 flex flex-wrap gap-2">
            {report.supporters.map((supporter, index) => (
              <span key={`${supporter.name}-${index}`} className="rounded-full bg-emerald-50 px-3 py-2 text-sm font-semibold text-emerald-900 ring-1 ring-emerald-100">
                {supporter.name}
              </span>
            ))}
          </div>
        </div>
      </section>
    );
  }

  if (!isOwner || campaign.status !== "AWAITING_REPORT") {
    return null;
  }

  return (
    <section id="completion-report" className="scroll-mt-24 rounded-[28px] border-2 border-amber-300 bg-amber-50/80 p-5 shadow-[0_20px_60px_rgba(146,64,14,0.14)] md:p-6">
      <p className="text-xs font-semibold uppercase tracking-[0.18em] text-amber-800">ожидается отчет</p>
      <h2 className="mt-2 text-2xl font-semibold tracking-[-0.02em] text-stone-950">Опубликовать итоговый отчет</h2>
      <form onSubmit={onSubmit} className="mt-5 space-y-3">
        <textarea
          className="min-h-32 w-full rounded-2xl border border-amber-200 bg-white px-4 py-3 outline-none transition focus:border-emerald-500"
          maxLength={5000}
          minLength={10}
          onChange={(event) => onGratitudeChange(event.target.value)}
          placeholder="Благодарность участникам и результат истории"
          required
          value={gratitudeText}
        />
        <PhotoUploader photos={photos} onChange={onPhotosChange} required />
        <button className="rounded-full bg-stone-950 px-5 py-3 font-semibold text-white transition hover:bg-emerald-700 disabled:opacity-70" disabled={isPublishing} type="submit">
          {isPublishing ? "Публикуем..." : "Опубликовать итоговый отчет"}
        </button>
        {message ? <p className="text-sm text-stone-700">{message}</p> : null}
      </form>
    </section>
  );
}

function ResultMetric({ label, value }: { label: string; value: string }) {
  return <div className="rounded-[18px] bg-white p-4 ring-1 ring-emerald-100"><p className="text-xs font-semibold uppercase tracking-[0.12em] text-emerald-700">{label}</p><p className="mt-2 text-lg font-semibold text-stone-950">{value}</p></div>;
}

function FutureUseOfFundsSection({ items }: { items: Array<{ label: string; value: string }> }) {
  if (!items.length) return null;

  return (
    <section className="rounded-[30px] bg-stone-950 p-5 text-white shadow-[0_22px_70px_rgba(28,25,23,0.18)] md:p-7">
      <div className="grid gap-5 md:grid-cols-[0.8fr_1.2fr] md:items-end">
        <div>
          <p className="text-xs font-semibold uppercase tracking-[0.18em] text-emerald-300">на что собираются деньги</p>
          <h2 className="mt-2 text-2xl font-semibold leading-tight md:text-3xl">Здесь появится разбивка цели</h2>
        </div>
        <div className="divide-y divide-white/10 border-y border-white/10">
          {items.map((item) => (
            <div key={item.label} className="flex items-center justify-between gap-4 py-3 text-sm">
              <span className="text-stone-300">{item.label}</span>
              <strong className="text-right text-white">{item.value}</strong>
            </div>
          ))}
        </div>
      </div>
    </section>
  );
}

function StoryTrustPause() {
  return (
    <section className="rounded-[30px] bg-stone-950 p-5 text-white shadow-[0_22px_70px_rgba(28,25,23,0.18)] md:p-7">
      <p className="text-xs font-semibold uppercase tracking-[0.18em] text-emerald-300">пауза доверия</p>
      <h2 className="mt-3 max-w-2xl text-2xl font-semibold leading-tight md:text-3xl">
        Каждый вклад сразу отражается в прогрессе этой истории.
      </h2>
      <p className="mt-4 max-w-2xl text-sm leading-7 text-stone-300">
        Здесь важны не только сумма и процент. Важен момент, когда история получает еще одного участника.
      </p>
    </section>
  );
}

function ShareSection({
  shareMessage,
  reportMessage,
  onShare,
  onReport,
}: {
  shareMessage: string | null;
  reportMessage: string | null;
  onShare: () => void;
  onReport: () => void;
}) {
  return (
    <section className="rounded-[28px] border border-stone-200 bg-white p-5 shadow-sm md:p-6">
      <div className="grid gap-4 md:grid-cols-[1fr_auto] md:items-center">
        <div>
          <h2 className="text-2xl font-semibold tracking-[-0.02em] text-stone-950">Поделиться сбором</h2>
          <p className="mt-2 text-sm leading-6 text-stone-600">Иногда один репост приводит человека, который сможет помочь.</p>
        </div>
        <div className="flex flex-wrap gap-3">
          <button onClick={onShare} className="rounded-full bg-stone-950 px-5 py-3 font-semibold text-white transition hover:bg-emerald-700" type="button">
            Поделиться
          </button>
          <button
            onClick={onReport}
            className="rounded-full bg-stone-100 px-5 py-3 font-semibold text-stone-700 transition hover:bg-stone-200"
            type="button"
          >
            Пожаловаться
          </button>
        </div>
      </div>
      {shareMessage ? <p className="mt-3 text-sm text-emerald-700">{shareMessage}</p> : null}
      {reportMessage ? <p className="mt-3 text-sm text-stone-600">{reportMessage}</p> : null}
    </section>
  );
}

function AuthorReputationCard({ campaign, reputation }: { campaign: CampaignDetail; reputation: AuthorReputation | null }) {
  return (
    <section className="rounded-[24px] border border-stone-200 bg-white/80 p-4 shadow-sm">
      <p className="text-xs font-semibold uppercase tracking-[0.18em] text-stone-400">автор</p>
      <h2 className="mt-2 text-xl font-semibold tracking-[-0.02em] text-stone-950">{campaign.owner?.username ?? "Автор истории"}</h2>
      <div className="mt-4 space-y-2 text-sm">
        <AuthorReputationRow label="Историй создано" value={reputation ? String(reputation.campaigns_created) : "—"} />
        <AuthorReputationRow label="Успешно завершено" value={reputation ? String(reputation.campaigns_completed) : "—"} />
        <AuthorReputationRow label="Всего собрано" value={reputation ? formatMoney(reputation.total_raised_amount) : "—"} />
      </div>
      {campaign.owner?.username ? (
        <Link href={`/u/${campaign.owner.username}`} className="mt-4 inline-flex rounded-full bg-stone-100 px-4 py-2 text-sm font-semibold text-stone-700 transition hover:bg-emerald-50 hover:text-emerald-800">
          Посмотреть профиль автора
        </Link>
      ) : null}
    </section>
  );
}

function AuthorReputationRow({ label, value }: { label: string; value: string }) {
  return (
    <div className="flex items-center justify-between gap-4 border-b border-stone-100 pb-3 last:border-0 last:pb-0">
      <span className="text-stone-500">{label}</span>
      <strong className="text-right text-stone-950">{value}</strong>
    </div>
  );
}

async function uploadPhotos(photos: PendingPhoto[]) {
  return Promise.all(photos.map(async (photo) => (await uploadStoryPhoto(photo.file)).url));
}

function clearPendingPhotos(photos: PendingPhoto[]) {
  photos.forEach((photo) => URL.revokeObjectURL(photo.previewUrl));
}

function CampaignUpdatesSection({
  campaignStatus,
  updates,
  isOwner,
  title,
  content,
  photos,
  isPublishing,
  message,
  onTitleChange,
  onContentChange,
  onPhotosChange,
  onSubmit,
}: {
  campaignStatus: CampaignDetail["status"];
  updates: CampaignUpdateItem[];
  isOwner: boolean;
  title: string;
  content: string;
  photos: PendingPhoto[];
  isPublishing: boolean;
  message: string | null;
  onTitleChange: (value: string) => void;
  onContentChange: (value: string) => void;
  onPhotosChange: (value: PendingPhoto[]) => void;
  onSubmit: (event: FormEvent<HTMLFormElement>) => void;
}) {
  const canPublishRegularUpdate = isOwner && campaignStatus === "ACTIVE";
  return (
    <section className="rounded-[28px] border border-stone-200 bg-white p-5 shadow-sm md:p-6">
      <div className="flex flex-wrap items-start justify-between gap-3">
        <div>
          <p className="text-xs font-semibold uppercase tracking-[0.18em] text-emerald-700">обновления</p>
          <h2 className="mt-2 text-2xl font-semibold tracking-[-0.02em] text-stone-950">Обновления</h2>
          <p className="mt-1 text-sm text-stone-500">{updates.length ? `${updates.length} обновлений` : "Первое обновление появится позже."}</p>
        </div>
      </div>

      {canPublishRegularUpdate ? (
        <form onSubmit={onSubmit} className="mt-5 space-y-3 rounded-[22px] bg-stone-50 p-4">
          <h3 className="text-lg font-semibold text-stone-950">Опубликовать обновление</h3>
          <input
            className="w-full rounded-2xl border border-stone-200 bg-white px-4 py-3 outline-none transition focus:border-emerald-500"
            minLength={3}
            maxLength={160}
            onChange={(event) => onTitleChange(event.target.value)}
            placeholder="Заголовок"
            required
            value={title}
          />
          <textarea
            className="min-h-32 w-full rounded-2xl border border-stone-200 bg-white px-4 py-3 outline-none transition focus:border-emerald-500"
            maxLength={5000}
            minLength={10}
            onChange={(event) => onContentChange(event.target.value)}
            placeholder="Что произошло в истории"
            required
            value={content}
          />
          <PhotoUploader photos={photos} onChange={onPhotosChange} />
          <button className="rounded-full bg-stone-950 px-5 py-3 font-semibold text-white transition hover:bg-emerald-700 disabled:opacity-70" disabled={isPublishing} type="submit">
            {isPublishing ? "Публикуем..." : "Опубликовать обновление"}
          </button>
          {message ? <p className="text-sm text-stone-600">{message}</p> : null}
        </form>
      ) : null}

      <div className="mt-5 space-y-4">
        {updates.length ? (
          updates.map((update) => (
            <article key={update.id} className="rounded-[22px] border border-stone-100 bg-stone-50/80 p-4">
              <p className="text-xs font-semibold uppercase tracking-[0.14em] text-stone-400">{formatDate(update.created_at)}</p>
              <h3 className="mt-2 text-xl font-semibold text-stone-950">{update.title}</h3>
              <p className="mt-2 whitespace-pre-wrap text-sm leading-6 text-stone-700">{update.content}</p>
              {update.photos.length ? (
                <div className="mt-4 grid gap-3 sm:grid-cols-2">
                  {update.photos.map((photo) => (
                    <img key={photo.id} src={photo.image_url} alt="" className="h-44 w-full rounded-2xl object-cover" />
                  ))}
                </div>
              ) : null}
            </article>
          ))
        ) : (
          <div className="flex gap-4 rounded-[22px] border border-stone-200 bg-white px-4 py-5">
            <span className="relative mt-0.5 flex h-10 w-10 shrink-0 items-center justify-center rounded-full border border-stone-200 bg-stone-50">
              <span className="absolute h-3.5 w-px -translate-y-1 bg-stone-400" />
              <span className="absolute h-px w-3 translate-x-1 bg-stone-400" />
            </span>
            <div>
              <h3 className="font-semibold text-stone-950">Первое обновление еще впереди</h3>
              <p className="mt-1 text-sm leading-6 text-stone-600">
                Оно появится после того, как автор расскажет о ходе сбора.
              </p>
            </div>
          </div>
        )}
      </div>
    </section>
  );
}
