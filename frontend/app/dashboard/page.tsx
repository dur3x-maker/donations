"use client";

import Link from "next/link";
import { useCallback, useEffect, useRef, useState } from "react";
import { useRouter } from "next/navigation";
import { ParticipationCard } from "@/app/components/ParticipationCard";
import { ProgressBar } from "@/app/components/ProgressBar";
import { useAuth } from "@/components/providers/auth-provider";
import { fetchContributionProgress, fetchOwnerDashboard } from "@/lib/api";
import { amountLeft, formatMoney } from "@/lib/format";
import type { CampaignListItem, CampaignUpdatedEvent, ContributionProgress, OwnerDashboard, RecentDonation } from "@/lib/types";
import { useLiveRefresh } from "@/lib/use-live-refresh";
import { subscribeDashboardUpdates, type RealtimeStatus } from "@/lib/ws";

export default function DashboardPage() {
  const router = useRouter();
  const { user, isAuthenticated, isLoading } = useAuth();
  const [progress, setProgress] = useState<ContributionProgress | null>(null);
  const [dashboard, setDashboard] = useState<OwnerDashboard | null>(null);
  const [isDashboardLoading, setIsDashboardLoading] = useState(true);
  const [dashboardError, setDashboardError] = useState<string | null>(null);
  const [wsStatus, setWsStatus] = useState<RealtimeStatus>("disconnected");
  const refreshTimer = useRef<number | null>(null);

  useEffect(() => {
    if (!isLoading && !isAuthenticated) router.replace("/login?next=/dashboard");
  }, [isAuthenticated, isLoading, router]);

  useEffect(() => {
    if (!isAuthenticated) return;
    setIsDashboardLoading(true);
    setDashboardError(null);
    fetchContributionProgress().then(setProgress).catch(() => setProgress(null));
    fetchOwnerDashboard()
      .then(setDashboard)
      .catch((error) => setDashboardError(error instanceof Error ? error.message : "Не удалось загрузить кабинет."))
      .finally(() => setIsDashboardLoading(false));
  }, [isAuthenticated]);

  const refreshDashboard = useCallback(async () => {
    setDashboard(await fetchOwnerDashboard());
  }, []);

  useLiveRefresh(refreshDashboard, wsStatus === "connected");

  useEffect(() => {
    if (!isAuthenticated) return;
    return subscribeDashboardUpdates((event) => {
      if (event.type === "campaign_lifecycle_changed") {
        void refreshDashboard();
        return;
      }
      setDashboard((current) => patchDashboard(current, event));
      if (refreshTimer.current !== null) window.clearTimeout(refreshTimer.current);
      refreshTimer.current = window.setTimeout(() => void refreshDashboard(), 400);
    }, setWsStatus);
  }, [isAuthenticated, refreshDashboard]);

  useEffect(() => () => {
    if (refreshTimer.current !== null) window.clearTimeout(refreshTimer.current);
  }, []);

  if (isLoading || !isAuthenticated || !user) return <LoadingCard />;

  const campaign = dashboard?.campaign;

  return (
    <section className="mx-auto max-w-6xl space-y-5">
      <header className="overflow-hidden rounded-[32px] bg-stone-950 p-6 text-white shadow-[0_24px_80px_rgba(28,25,23,0.18)] md:p-8">
        <div className="flex flex-col gap-5 md:flex-row md:items-end md:justify-between">
          <div>
            <p className="text-xs font-semibold uppercase tracking-[0.2em] text-emerald-300">{campaign ? "центр управления сбором" : "личный кабинет"}</p>
            <h1 className="mt-3 text-3xl font-semibold tracking-tight md:text-5xl">
              {campaign ? "Ваш сбор в движении" : `С возвращением, ${user.username}`}
            </h1>
            <p className="mt-3 max-w-2xl text-sm leading-6 text-stone-300 md:text-base">
              {campaign ? "Следите за поступлениями, прогрессом и тем, что стоит обновить прямо сейчас." : "Поддерживайте важные истории и откройте возможность рассказать свою."}
            </p>
          </div>
          <Link href="/campaigns" className="inline-flex w-fit rounded-full bg-white/10 px-5 py-3 text-sm font-semibold text-white ring-1 ring-white/15 transition hover:bg-white/20">
            Найти сбор для поддержки
          </Link>
        </div>
      </header>

      {isDashboardLoading ? <DashboardSkeleton /> : dashboardError ? <DashboardError message={dashboardError} /> : campaign && dashboard?.stats ? <OwnerView dashboard={dashboard} campaign={campaign} progress={progress} /> : <MemberView progress={progress} />}
    </section>
  );
}

function OwnerView({ dashboard, campaign, progress }: { dashboard: OwnerDashboard; campaign: CampaignListItem; progress: ContributionProgress | null }) {
  const stats = dashboard.stats!;
  const canCreateAnotherCampaign = campaign.status === "COMPLETED" && progress?.can_create_campaign;
  return (
    <>
      <div className="grid grid-cols-2 gap-3 lg:grid-cols-4">
        <Metric label="Собрано" value={formatMoney(campaign.current_amount)} tone="green" />
        <Metric label="Поддержали" value={`${stats.unique_contributors_count} чел.`} />
        <Metric label="Сегодня" value={`+${formatMoney(stats.today_amount)}`} tone="lime" />
        <Metric label="Осталось" value={formatMoney(amountLeft(campaign.current_amount, campaign.target_amount))} />
      </div>

      <div className="grid gap-5 lg:grid-cols-[minmax(0,1.35fr)_minmax(280px,0.65fr)]">
        <CampaignCard campaign={campaign} canCreateAnotherCampaign={Boolean(canCreateAnotherCampaign)} />
        <ManagementCard campaignId={campaign.id} />
      </div>

      <div className="grid gap-5 lg:grid-cols-[minmax(0,0.75fr)_minmax(0,1.25fr)]">
        <StatsCard stats={stats} campaignsCount={dashboard.campaigns_count} />
        <RecentDonations donations={dashboard.recent_donations} />
      </div>
    </>
  );
}

function patchDashboard(dashboard: OwnerDashboard | null, event: CampaignUpdatedEvent) {
  if (!dashboard?.campaign || dashboard.campaign.id !== event.campaign_id || !dashboard.stats) return dashboard;
  const todayAmount = Number(dashboard.stats.today_amount) + Number(event.donation.amount);
  return {
    ...dashboard,
    campaign: {
      ...dashboard.campaign,
      current_amount: event.current_amount,
      target_amount: event.goal_amount,
      progress_percentage: event.progress_percentage,
      contributors_count: event.contributors_count,
    },
    stats: {
      ...dashboard.stats,
      contributions_count: event.contributors_count,
      today_amount: String(todayAmount),
    },
    recent_donations: [event.donation, ...dashboard.recent_donations.filter((donation) => donation.id !== event.donation.id)].slice(0, 5),
  };
}

function MemberView({ progress }: { progress: ContributionProgress | null }) {
  if (!progress) return <DashboardError message="Не удалось загрузить прогресс участия. Обновите страницу." />;

  const unlocked = progress.can_create_campaign;
  return (
    <div className="grid gap-5 lg:grid-cols-[minmax(0,1fr)_minmax(320px,0.82fr)]">
      <ParticipationCard progress={progress} />
      <section className="rounded-[28px] border border-emerald-100 bg-[linear-gradient(145deg,#ffffff,#ecfdf5)] p-6 shadow-[0_18px_55px_rgba(28,25,23,0.07)]">
        <p className="text-xs font-semibold uppercase tracking-[0.18em] text-emerald-700">следующий шаг</p>
        <h2 className="mt-3 text-2xl font-semibold text-stone-950">{unlocked ? "Расскажите свою историю" : "Найдите сбор для поддержки"}</h2>
        <p className="mt-3 text-sm leading-6 text-stone-600">
          {unlocked ? "Порог пройден. Создайте страницу сбора: добавьте цель, описание и материалы для проверки." : "Каждый подтвержденный вклад приближает открытие собственного сбора и помогает живой истории прямо сейчас."}
        </p>
        <div className="mt-6 flex flex-wrap gap-3">
          <Link href="/campaigns" className="inline-flex rounded-full bg-stone-950 px-5 py-3 text-sm font-semibold text-white transition hover:bg-emerald-700">Найти сбор для поддержки</Link>
          {unlocked ? <Link href="/campaigns/new" className="inline-flex rounded-full bg-white px-5 py-3 text-sm font-semibold text-emerald-800 ring-1 ring-emerald-200 transition hover:bg-emerald-50">Создать сбор</Link> : null}
        </div>
      </section>
    </div>
  );
}

function Metric({ label, value, tone }: { label: string; value: string; tone?: "green" | "lime" }) {
  return (
    <div className={`rounded-[22px] border p-4 shadow-sm ${tone === "green" ? "border-emerald-100 bg-emerald-50" : tone === "lime" ? "border-lime-100 bg-lime-50" : "border-stone-200 bg-white"}`}>
      <p className="text-xs font-semibold uppercase tracking-[0.14em] text-stone-500">{label}</p>
      <p className="mt-2 text-xl font-semibold tracking-tight text-stone-950 md:text-2xl">{value}</p>
    </div>
  );
}

function CampaignCard({ campaign, canCreateAnotherCampaign }: { campaign: CampaignListItem; canCreateAnotherCampaign: boolean }) {
  return (
    <section className="rounded-[28px] border border-stone-200 bg-white p-6 shadow-[0_18px_55px_rgba(28,25,23,0.07)]">
      <div className="flex flex-wrap items-start justify-between gap-3">
        <div>
          <p className="text-xs font-semibold uppercase tracking-[0.18em] text-emerald-700">мой сбор</p>
          <h2 className="mt-3 text-2xl font-semibold text-stone-950">{campaign.title}</h2>
        </div>
        <span className={`rounded-full px-3 py-1.5 text-xs font-semibold ${campaign.is_verified ? "bg-emerald-50 text-emerald-800" : "bg-amber-50 text-amber-800"}`}>{campaign.is_verified ? "проверен" : "на проверке"}</span>
      </div>
      <div className="mt-7 flex flex-wrap items-end justify-between gap-3">
        <div>
          <p className="text-3xl font-semibold tracking-tight text-stone-950">{formatMoney(campaign.current_amount)}</p>
          <p className="mt-1 text-sm text-stone-500">из {formatMoney(campaign.target_amount)}</p>
        </div>
        <p className="text-2xl font-semibold text-emerald-700">{campaign.progress_percentage}%</p>
      </div>
      <div className="mt-5"><ProgressBar value={campaign.progress_percentage} /></div>
      <div className="mt-6 flex flex-wrap gap-3">
        <Link href={`/campaigns/${campaign.id}`} className="inline-flex rounded-full bg-stone-950 px-5 py-3 text-sm font-semibold text-white transition hover:bg-emerald-700">Открыть страницу сбора</Link>
        <Link href={`/campaigns/${campaign.id}/edit`} className="inline-flex rounded-full bg-stone-100 px-5 py-3 text-sm font-semibold text-stone-700 transition hover:bg-stone-200">Редактировать</Link>
        {canCreateAnotherCampaign ? <Link href="/campaigns/new" className="inline-flex rounded-full bg-emerald-50 px-5 py-3 text-sm font-semibold text-emerald-800 ring-1 ring-emerald-200 transition hover:bg-emerald-100">Создать новый сбор</Link> : null}
      </div>
    </section>
  );
}

function ManagementCard({ campaignId }: { campaignId: string }) {
  const actions = [
    ["Редактировать описание", `/campaigns/${campaignId}/edit#description`],
    ["Добавить фотографии", `/campaigns/${campaignId}/edit#cover`],
    ["Изменить цель", `/campaigns/${campaignId}/edit#target`],
  ];
  return (
    <section className="rounded-[28px] border border-stone-200 bg-white p-6 shadow-[0_18px_55px_rgba(28,25,23,0.07)]">
      <p className="text-xs font-semibold uppercase tracking-[0.18em] text-stone-400">управление</p>
      <h2 className="mt-2 text-xl font-semibold text-stone-950">Быстрые действия</h2>
      <div className="mt-5 space-y-2">
        {actions.map(([action, href]) => (
          <Link key={action} href={href} className="flex items-center justify-between rounded-2xl bg-stone-50 px-4 py-3 text-sm font-semibold text-stone-700 transition hover:bg-emerald-50 hover:text-emerald-800">
            {action}<span aria-hidden="true">→</span>
          </Link>
        ))}
        <div className="flex items-center justify-between rounded-2xl bg-stone-50 px-4 py-3 text-sm font-semibold text-stone-400">
          Загрузить документы<span className="text-[10px] uppercase tracking-wide">скоро</span>
        </div>
      </div>
    </section>
  );
}

function StatsCard({ stats, campaignsCount }: { stats: NonNullable<OwnerDashboard["stats"]>; campaignsCount: number }) {
  return (
    <section className="rounded-[28px] border border-stone-200 bg-white p-6 shadow-[0_18px_55px_rgba(28,25,23,0.07)]">
      <p className="text-xs font-semibold uppercase tracking-[0.18em] text-stone-400">статистика</p>
      <h2 className="mt-2 text-xl font-semibold text-stone-950">Как идет сбор</h2>
      <div className="mt-5 divide-y divide-stone-100">
        <Stat label="Подтвержденных вкладов" value={String(stats.contributions_count)} />
        <Stat label="Уникальных участников" value={String(stats.unique_contributors_count)} />
        <Stat label="Средний вклад" value={formatMoney(stats.average_contribution)} />
        <Stat label="Сегодня" value={`+${formatMoney(stats.today_amount)}`} />
        {campaignsCount > 1 ? <Stat label="Всего ваших сборов" value={String(campaignsCount)} /> : null}
      </div>
    </section>
  );
}

function Stat({ label, value }: { label: string; value: string }) {
  return <div className="flex items-center justify-between gap-3 py-3 text-sm"><span className="text-stone-500">{label}</span><strong className="text-stone-950">{value}</strong></div>;
}

function RecentDonations({ donations }: { donations: RecentDonation[] }) {
  return (
    <section className="rounded-[28px] border border-stone-200 bg-white p-6 shadow-[0_18px_55px_rgba(28,25,23,0.07)]">
      <div className="flex items-end justify-between gap-3">
        <div><p className="text-xs font-semibold uppercase tracking-[0.18em] text-emerald-700">поступления</p><h2 className="mt-2 text-xl font-semibold text-stone-950">Последние вклады</h2></div>
        <span className="flex items-center gap-2 text-xs font-semibold text-emerald-700"><span className="h-2 w-2 rounded-full bg-emerald-500" />обновляются</span>
      </div>
      <div className="mt-5 space-y-2">
        {donations.length ? donations.map((donation) => (
          <div key={donation.id} className="flex items-center justify-between gap-3 rounded-2xl bg-stone-50 px-4 py-3">
            <div className="flex min-w-0 items-center gap-3">
              <span className="flex h-9 w-9 shrink-0 items-center justify-center rounded-full bg-emerald-100 text-sm font-semibold text-emerald-800">{donation.username.slice(0, 1).toUpperCase()}</span>
              <span className="min-w-0"><span className="block truncate text-sm font-semibold text-stone-800">{donation.username}</span><span className="mt-0.5 block text-xs text-stone-400">{relativeTime(donation.created_at)}</span></span>
            </div>
            <strong className="shrink-0 text-sm text-emerald-700">+{formatMoney(donation.amount)}</strong>
          </div>
        )) : <p className="rounded-2xl bg-stone-50 px-4 py-5 text-sm leading-6 text-stone-600">Здесь появятся первые поступления. Поделитесь страницей сбора, чтобы ее увидели близкие.</p>}
      </div>
    </section>
  );
}

function LoadingCard() {
  return <div className="rounded-[28px] border border-stone-200 bg-white p-5 text-stone-600 shadow-sm">Загружаем кабинет...</div>;
}

function DashboardSkeleton() {
  return <div className="grid grid-cols-2 gap-3 lg:grid-cols-4">{Array.from({ length: 4 }, (_, index) => <div key={index} className="h-24 animate-pulse rounded-[22px] bg-white shadow-sm" />)}</div>;
}

function DashboardError({ message }: { message: string }) {
  return <div className="rounded-[24px] border border-rose-100 bg-rose-50 px-5 py-4 text-sm leading-6 text-rose-800">{message}</div>;
}

function relativeTime(value: string) {
  const minutes = Math.max(0, Math.floor((Date.now() - new Date(value).getTime()) / 60000));
  if (minutes < 1) return "только что";
  if (minutes < 60) return `${minutes} мин назад`;
  const hours = Math.floor(minutes / 60);
  if (hours < 24) return `${hours} ч назад`;
  return `${Math.floor(hours / 24)} дн назад`;
}
