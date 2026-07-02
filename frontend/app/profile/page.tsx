"use client";

import Link from "next/link";
import { useEffect, useState } from "react";
import { useRouter } from "next/navigation";
import { ParticipationCard } from "@/app/components/ParticipationCard";
import { useAuth } from "@/components/providers/auth-provider";
import { fetchProfileImpact, fetchProfileSummary, fetchUserAchievements, resendEmailVerification, updateProfile, uploadAvatar } from "@/lib/api";
import { formatMoney } from "@/lib/format";
import type { AuthUser, ProfileImpact, ProfileSummary, UserAchievement } from "@/lib/types";

const MAX_AVATAR_SIZE = 2 * 1024 * 1024;
const ALLOWED_AVATAR_TYPES = ["image/jpeg", "image/png", "image/webp"];

export default function ProfilePage() {
  const router = useRouter();
  const { user, isAuthenticated, isLoading, refreshAuth } = useAuth();
  const [summary, setSummary] = useState<ProfileSummary | null>(null);
  const [impact, setImpact] = useState<ProfileImpact | null>(null);
  const [achievements, setAchievements] = useState<UserAchievement[]>([]);
  const [error, setError] = useState<string | null>(null);
  const [profileForm, setProfileForm] = useState({
    first_name: "",
    last_name: "",
    username: "",
    bio: "",
    city: "",
    avatar_url: "",
  });
  const [profileStatus, setProfileStatus] = useState<string | null>(null);
  const [emailStatus, setEmailStatus] = useState<string | null>(null);
  const [isProfileSaving, setIsProfileSaving] = useState(false);
  const [isAvatarUploading, setIsAvatarUploading] = useState(false);
  const [isEmailSending, setIsEmailSending] = useState(false);

  useEffect(() => {
    if (!isLoading && !isAuthenticated) router.replace("/login?next=/profile");
  }, [isAuthenticated, isLoading, router]);

  useEffect(() => {
    if (!isAuthenticated) return;
    Promise.all([fetchProfileSummary(), fetchProfileImpact(), fetchUserAchievements()])
      .then(([freshSummary, freshImpact, freshAchievements]) => {
        setSummary(freshSummary);
        setImpact(freshImpact);
        setAchievements(freshAchievements);
      })
      .catch((requestError) => setError(requestError instanceof Error ? requestError.message : "Не удалось загрузить профиль."));
  }, [isAuthenticated]);

  useEffect(() => {
    if (!user) return;
    setProfileForm({
      first_name: user.first_name ?? "",
      last_name: user.last_name ?? "",
      username: user.username,
      bio: user.bio ?? "",
      city: user.city ?? "",
      avatar_url: user.avatar_url ?? "",
    });
  }, [user]);

  if (isLoading || !isAuthenticated || !user) return <LoadingCard />;
  if (!summary || !impact) return error ? <ProfileError message={error} /> : <LoadingCard />;

  const level = impact.current_level ?? "Путь помощи еще не начался";
  const displayName = fullName(user.first_name, user.last_name) || user.username;

  const handleProfileSubmit = async (event: React.FormEvent<HTMLFormElement>) => {
    event.preventDefault();
    setIsProfileSaving(true);
    setProfileStatus(null);

    try {
      const updatedUser = await updateProfile({
        first_name: emptyToNull(profileForm.first_name),
        last_name: emptyToNull(profileForm.last_name),
        username: profileForm.username,
        bio: emptyToNull(profileForm.bio),
        city: emptyToNull(profileForm.city),
        avatar_url: emptyToNull(profileForm.avatar_url),
      });
      syncAuthUser(updatedUser);
      setProfileStatus("Профиль обновлён.");
    } catch (requestError) {
      setProfileStatus(requestError instanceof Error ? requestError.message : "Не удалось обновить профиль.");
    } finally {
      setIsProfileSaving(false);
    }
  };

  const handleAvatarChange = async (event: React.ChangeEvent<HTMLInputElement>) => {
    const file = event.target.files?.[0];
    if (!file) return;

    if (!ALLOWED_AVATAR_TYPES.includes(file.type)) {
      setProfileStatus("Допустимы только JPG, PNG и WebP.");
      event.target.value = "";
      return;
    }
    if (file.size > MAX_AVATAR_SIZE) {
      setProfileStatus("Размер аватара не должен превышать 2 МБ.");
      event.target.value = "";
      return;
    }

    setIsAvatarUploading(true);
    setProfileStatus(null);
    try {
      const uploaded = await uploadAvatar(file);
      setProfileForm((current) => ({ ...current, avatar_url: uploaded.url }));
      setProfileStatus("Фото загружено. Сохраните профиль.");
    } catch (requestError) {
      setProfileStatus(requestError instanceof Error ? requestError.message : "Не удалось загрузить фото.");
    } finally {
      setIsAvatarUploading(false);
      event.target.value = "";
    }
  };

  const handleResendEmail = async () => {
    setIsEmailSending(true);
    setEmailStatus(null);
    try {
      await resendEmailVerification();
      await refreshAuth();
      setEmailStatus("Письмо отправлено повторно.");
    } catch (requestError) {
      setEmailStatus(requestError instanceof Error ? requestError.message : "Не удалось отправить письмо.");
    } finally {
      setIsEmailSending(false);
    }
  };

  return (
    <section className="mx-auto max-w-6xl space-y-5">
      <header className="overflow-hidden rounded-[32px] bg-stone-950 p-6 text-white shadow-[0_24px_80px_rgba(28,25,23,0.18)] md:p-8">
        <div className="grid gap-7 lg:grid-cols-[minmax(0,1fr)_minmax(320px,420px)] lg:items-start">
          <div className="grid gap-5 sm:grid-cols-[auto_minmax(0,1fr)] sm:items-center">
            <ProfileAvatar name={displayName} username={user.username} avatarUrl={profileForm.avatar_url || user.avatar_url} />
            <div className="min-w-0">
              <p className="text-xs font-semibold uppercase tracking-[0.2em] text-emerald-300">профиль участника</p>
              <h1 className="mt-3 text-4xl font-semibold tracking-tight md:text-5xl">{displayName}</h1>
              <p className="mt-2 text-lg font-medium text-stone-300">@{user.username}</p>
              <div className="mt-4 flex flex-wrap gap-2 text-sm text-stone-200">
                {user.is_verified ? <span className="rounded-full bg-emerald-100 px-3 py-1.5 font-semibold text-emerald-900">🟢 Email подтверждён</span> : <span className="rounded-full bg-amber-100 px-3 py-1.5 font-semibold text-amber-900">🟡 Email не подтверждён</span>}
                <span className="rounded-full bg-white/10 px-3 py-1.5 ring-1 ring-white/10">С нами с {formatMonth(user.created_at)}</span>
                {user.city ? <span className="rounded-full bg-white/10 px-3 py-1.5 ring-1 ring-white/10">{user.city}</span> : null}
              </div>
              <p className="mt-5 max-w-2xl text-base leading-7 text-stone-100">
                {user.bio || "Расскажите немного о себе: чем занимаетесь, почему вы на платформе и что для вас значит взаимопомощь."}
              </p>
              <div className="mt-5 w-fit rounded-[22px] bg-white/10 px-5 py-4 ring-1 ring-white/15">
                <p className="text-xs font-semibold uppercase tracking-[0.16em] text-emerald-300">статус участника</p>
                <p className="mt-2 text-xl font-semibold">{level}</p>
              </div>
            </div>
          </div>

          <form onSubmit={handleProfileSubmit} className="rounded-[26px] bg-white p-5 text-stone-950 shadow-[0_18px_55px_rgba(0,0,0,0.18)]">
            <div className="flex items-center justify-between gap-3">
              <div>
                <p className="text-xs font-semibold uppercase tracking-[0.16em] text-emerald-700">редактирование</p>
                <h2 className="mt-1 text-xl font-semibold">О себе</h2>
              </div>
              <label className="cursor-pointer rounded-full bg-stone-100 px-4 py-2 text-sm font-semibold text-stone-800 transition hover:bg-emerald-50 hover:text-emerald-800">
                {isAvatarUploading ? "Загрузка..." : "Фото"}
                <input className="sr-only" type="file" accept="image/jpeg,image/png,image/webp" onChange={handleAvatarChange} disabled={isAvatarUploading || isProfileSaving} />
              </label>
            </div>
            <div className="mt-4 grid gap-3 sm:grid-cols-2">
              <ProfileInput label="Имя" value={profileForm.first_name} onChange={(value) => setProfileForm((current) => ({ ...current, first_name: value }))} maxLength={80} />
              <ProfileInput label="Фамилия" value={profileForm.last_name} onChange={(value) => setProfileForm((current) => ({ ...current, last_name: value }))} maxLength={80} />
            </div>
            <div className="mt-3 grid gap-3 sm:grid-cols-2">
              <ProfileInput label="Nickname" value={profileForm.username} onChange={(value) => setProfileForm((current) => ({ ...current, username: value }))} maxLength={24} />
              <ProfileInput label="Город" value={profileForm.city} onChange={(value) => setProfileForm((current) => ({ ...current, city: value }))} maxLength={80} />
            </div>
            <label className="mt-3 block">
              <span className="text-xs font-semibold uppercase tracking-[0.12em] text-stone-500">О себе</span>
              <textarea
                value={profileForm.bio}
                onChange={(event) => setProfileForm((current) => ({ ...current, bio: event.target.value }))}
                maxLength={250}
                rows={4}
                className="mt-2 w-full resize-none rounded-2xl border border-stone-200 px-4 py-3 text-sm outline-none transition focus:border-emerald-500 focus:ring-4 focus:ring-emerald-100"
              />
            </label>
            <div className="mt-3 flex flex-col gap-3 sm:flex-row sm:items-center sm:justify-between">
              <span className="text-xs text-stone-500">{profileForm.bio.length}/250</span>
              <button className="rounded-full bg-stone-950 px-5 py-3 text-sm font-semibold text-white transition hover:bg-emerald-800 disabled:cursor-wait disabled:opacity-60" disabled={isProfileSaving || isAvatarUploading} type="submit">
                {isProfileSaving ? "Сохраняем..." : "Сохранить профиль"}
              </button>
            </div>
            {profileStatus ? <p className="mt-3 text-sm leading-6 text-stone-600">{profileStatus}</p> : null}
          </form>
        </div>
      </header>

      {!user.is_verified ? (
        <section className="rounded-[26px] border border-amber-100 bg-amber-50 p-5 shadow-sm">
          <div className="flex flex-col gap-4 md:flex-row md:items-center md:justify-between">
            <div>
              <h2 className="text-lg font-semibold text-amber-950">Подтвердите адрес электронной почты.</h2>
              <p className="mt-1 text-sm leading-6 text-amber-800">Мы отправим письмо со ссылкой подтверждения на {user.email}.</p>
              {emailStatus ? <p className="mt-2 text-sm font-medium text-amber-900">{emailStatus}</p> : null}
            </div>
            <button
              type="button"
              onClick={handleResendEmail}
              disabled={isEmailSending}
              className="w-fit rounded-full bg-stone-950 px-5 py-3 text-sm font-semibold text-white transition hover:bg-emerald-700 disabled:cursor-wait disabled:opacity-70"
            >
              {isEmailSending ? "Отправляем..." : "Отправить письмо повторно"}
            </button>
          </div>
        </section>
      ) : null}

      <ParticipationCard progress={summary} compact />

      <CommunityImpact summary={summary} impact={impact} />

      <div className="grid gap-5 lg:grid-cols-[minmax(0,1.12fr)_minmax(320px,0.88fr)]">
        <div className="space-y-5">
          <CommunityContribution summary={summary} />
          <ParticipationHistory contributions={summary.recent_contributions} />
          <ParticipantJourney timeline={summary.timeline} />
        </div>
        <div className="space-y-5">
          <RecentActivity summary={summary} />
          <MyLevel impact={impact} />
          <ContributionOverview impact={impact} achievementsCount={achievements.length} />
          <PatronCircle impact={impact} />
          <Achievements achievements={achievements} />
          <Reputation summary={summary} level={level} />
        </div>
      </div>
    </section>
  );
}

function CommunityImpact({ summary, impact }: { summary: ProfileSummary; impact: ProfileImpact }) {
  const hasImpact = summary.confirmed_contributions_count > 0;

  return (
    <section className="overflow-hidden rounded-[30px] bg-[linear-gradient(135deg,#064e3b,#047857_62%,#65a30d)] p-6 text-white shadow-[0_22px_70px_rgba(6,78,59,0.24)] md:p-7">
      <p className="text-xs font-semibold uppercase tracking-[0.2em] text-emerald-200">след в сообществе</p>
      <div className="mt-3 grid gap-6 md:grid-cols-[minmax(0,1fr)_auto] md:items-end">
        <div>
          <h2 className="text-2xl font-semibold md:text-3xl">
            {hasImpact ? `Вы участвовали в поддержке ${pluralize(summary.supported_campaigns_count, "истории", "историй", "историй")}` : "Ваш след в сообществе появится после первого вклада"}
          </h2>
          <p className="mt-3 max-w-3xl text-sm leading-6 text-emerald-50">
            {hasImpact ? `Вы участвовали в поддержке историй, которые вместе собрали ${formatMoney(summary.supported_campaigns_current_amount)}.` : "После первой поддержки здесь появится профиль влияния: истории, вклад и место среди участников."}
          </p>
        </div>
        {hasImpact ? <div className="rounded-[22px] bg-white/12 px-5 py-4 ring-1 ring-white/20">
          <p className="text-xs font-semibold uppercase tracking-[0.14em] text-emerald-100">сейчас в этих сборах</p>
          <p className="mt-2 text-3xl font-semibold">{formatMoney(summary.supported_campaigns_current_amount)}</p>
          <p className="mt-1 text-xs leading-5 text-emerald-100">собрано всеми участниками</p>
        </div> : null}
      </div>
      {hasImpact ? <div className="mt-6 grid grid-cols-2 gap-3 md:grid-cols-4">
        <ImpactMetric label="Поддержано сборов" value={String(summary.supported_campaigns_count)} />
        <ImpactMetric label="Ваших вкладов" value={String(summary.confirmed_contributions_count)} />
        <ImpactMetric label="Направлено вами" value={formatMoney(summary.total_donated_amount)} />
        <ImpactMetric label="Последняя поддержка" value={summary.last_contribution_at ? relativeTime(summary.last_contribution_at) : "пока не было"} />
      </div> : null}
    </section>
  );
}

function ImpactMetric({ label, value }: { label: string; value: string }) {
  return <div className="rounded-[18px] bg-white/10 px-4 py-3 ring-1 ring-white/15"><p className="text-[11px] font-semibold uppercase tracking-[0.12em] text-emerald-100">{label}</p><p className="mt-2 text-lg font-semibold">{value}</p></div>;
}

function CommunityContribution({ summary }: { summary: ProfileSummary }) {
  const hasImpact = summary.confirmed_contributions_count > 0;
  const metrics = [
    ["Подтвержденных вкладов", String(summary.confirmed_contributions_count)],
    ["Поддержано сборов", String(summary.supported_campaigns_count)],
    ["Пожертвовано", formatMoney(summary.total_donated_amount)],
    ["Последний вклад", summary.last_contribution_at ? relativeTime(summary.last_contribution_at) : "пока не было"],
  ];
  return (
    <section className="rounded-[28px] border border-stone-200 bg-white p-6 shadow-[0_18px_55px_rgba(28,25,23,0.07)]">
      <p className="text-xs font-semibold uppercase tracking-[0.18em] text-emerald-700">ваш вклад в сообщество</p>
      <h2 className="mt-2 text-2xl font-semibold text-stone-950">Поддержка, которая уже стала частью платформы</h2>
      {hasImpact ? <div className="mt-5 grid grid-cols-2 gap-3">
        {metrics.map(([label, value]) => <div key={label} className="rounded-[20px] bg-stone-50 p-4"><p className="text-xs font-semibold uppercase tracking-[0.12em] text-stone-400">{label}</p><p className="mt-2 text-xl font-semibold text-stone-950">{value}</p></div>)}
      </div> : <p className="mt-4 rounded-2xl bg-stone-50 px-4 py-5 text-sm leading-6 text-stone-600">Профиль влияния появится после первой поддержки. Здесь не будет пустой статистики ради статистики.</p>}
    </section>
  );
}

function RecentActivity({ summary }: { summary: ProfileSummary }) {
  const hasRecentActivity = summary.contributions_last_30_days > 0;
  return (
    <section className="rounded-[28px] border border-lime-100 bg-lime-50/70 p-6 shadow-[0_18px_55px_rgba(28,25,23,0.06)]">
      <p className="text-xs font-semibold uppercase tracking-[0.18em] text-lime-800">последние 30 дней</p>
      <h2 className="mt-2 text-xl font-semibold text-stone-950">{hasRecentActivity ? "Поддержка продолжается" : "Спокойный период"}</h2>
      {hasRecentActivity ? (
        <div className="mt-4 grid grid-cols-3 gap-2">
          <SmallMetric value={summary.contributions_last_30_days} label="вкладов" />
          <SmallMetric value={summary.achievements_last_30_days} label="достижений" prefix="+" />
          <SmallMetric value={summary.supported_campaigns_last_30_days} label="сборов" />
        </div>
      ) : <p className="mt-3 text-sm leading-6 text-stone-600">{summary.last_contribution_at ? `Последний вклад был ${relativeTime(summary.last_contribution_at)}.` : "История поддержки начнется с первого вклада."}</p>}
    </section>
  );
}

function SmallMetric({ value, label, prefix = "" }: { value: number; label: string; prefix?: string }) {
  return <div className="rounded-2xl bg-white px-3 py-3 text-center shadow-sm"><p className="text-xl font-semibold text-stone-950">{prefix}{value}</p><p className="mt-1 text-[11px] uppercase tracking-wide text-stone-500">{label}</p></div>;
}

function MyLevel({ impact }: { impact: ProfileImpact }) {
  return (
    <section className="rounded-[28px] border border-stone-200 bg-white p-6 shadow-[0_18px_55px_rgba(28,25,23,0.07)]">
      <p className="text-xs font-semibold uppercase tracking-[0.18em] text-emerald-700">мой уровень</p>
      <h2 className="mt-2 text-xl font-semibold text-stone-950">{impact.current_level ?? "Путь помощи еще не начался"}</h2>
      <p className="mt-3 text-sm leading-6 text-stone-600">
        {impact.next_level ? `${impact.confirmed_contributions_count} из ${nextLevelThreshold(impact.next_level)} вкладов до уровня «${impact.next_level}».` : "Вы достигли верхнего уровня участия."}
      </p>
      <div className="mt-4 h-2 overflow-hidden rounded-full bg-stone-100">
        <div className="h-full rounded-full bg-emerald-600" style={{ width: `${impact.progress_percent}%` }} />
      </div>
      <p className="mt-3 text-sm text-stone-500">{impact.confirmed_contributions_count} подтвержденных вкладов</p>
      <div className="mt-4 grid grid-cols-3 gap-2">
        <SmallMetric value={impact.completed_supported_campaigns} label="завершены" />
        <SmallMetric value={impact.active_supported_campaigns} label="в процессе" />
        <SmallMetric value={impact.fundraising_supported_campaigns} label="собирают" />
      </div>
    </section>
  );
}

function ParticipantJourney({ timeline }: { timeline: ProfileSummary["timeline"] }) {
  return (
    <section className="rounded-[28px] border border-stone-200 bg-white p-6 shadow-[0_18px_55px_rgba(28,25,23,0.07)]">
      <p className="text-xs font-semibold uppercase tracking-[0.18em] text-emerald-700">путь участника</p>
      <h2 className="mt-2 text-xl font-semibold text-stone-950">Как рос ваш вклад</h2>
      <div className="mt-5 space-y-0">
        {timeline.length ? timeline.map((item, index) => (
          <div key={item.id} className="relative flex gap-4 pb-5 last:pb-0">
            {index < timeline.length - 1 ? <span className="absolute left-[7px] top-4 h-full w-px bg-emerald-200" /> : null}
            <span className="relative mt-1 h-4 w-4 shrink-0 rounded-full border-4 border-emerald-100 bg-emerald-600" />
            <div><p className="text-xs font-semibold uppercase tracking-[0.12em] text-stone-400">{formatMonth(item.created_at)}</p><p className="mt-1 text-sm font-semibold text-stone-800">{item.title}</p></div>
          </div>
        )) : <p className="text-sm leading-6 text-stone-600">Первый этап появится после подтвержденного вклада.</p>}
      </div>
    </section>
  );
}

function ParticipationHistory({ contributions }: { contributions: ProfileSummary["recent_contributions"] }) {
  return (
    <section className="rounded-[28px] border border-stone-200 bg-white p-6 shadow-[0_18px_55px_rgba(28,25,23,0.07)]">
      <p className="text-xs font-semibold uppercase tracking-[0.18em] text-emerald-700">история участия</p>
      <h2 className="mt-2 text-xl font-semibold text-stone-950">Последние действия</h2>
      <div className="mt-5 space-y-2">
        {contributions.length ? contributions.map((contribution) => (
          <Link href={`/campaigns/${contribution.campaign_id}`} key={contribution.id} className="flex items-center justify-between gap-3 rounded-2xl bg-stone-50 px-4 py-3 transition hover:bg-emerald-50">
            <span className="min-w-0"><span className="block truncate text-sm font-semibold text-stone-800">Поддержал сбор «{contribution.campaign_title}»</span><span className="mt-1 block text-xs text-stone-400">{relativeTime(contribution.created_at)}</span></span>
            <strong className="shrink-0 text-sm text-emerald-700">+{formatMoney(contribution.amount)}</strong>
          </Link>
        )) : <p className="rounded-2xl bg-stone-50 px-4 py-5 text-sm leading-6 text-stone-600">Здесь появится ваша история поддержки. Выберите первый сбор, который вам близок.</p>}
      </div>
    </section>
  );
}

function ContributionOverview({ impact, achievementsCount }: { impact: ProfileImpact; achievementsCount: number }) {
  return (
    <section className="rounded-[28px] border border-stone-200 bg-white p-6 shadow-[0_18px_55px_rgba(28,25,23,0.07)]">
      <p className="text-xs font-semibold uppercase tracking-[0.18em] text-emerald-700">вклад в сообщество</p>
      <h2 className="mt-2 text-xl font-semibold text-stone-950">История постоянной помощи</h2>
      <div className="mt-5 grid grid-cols-2 gap-3">
        <SmallMetric value={impact.confirmed_contributions_count} label="вкладов" />
        <SmallMetric value={impact.supported_campaigns_count} label="историй" />
        <SmallMetric value={impact.completed_supported_campaigns} label="завершены" />
        <SmallMetric value={achievementsCount} label="достижений" />
      </div>
    </section>
  );
}

function PatronCircle({ impact }: { impact: ProfileImpact }) {
  if (!impact.is_patron) return null;

  return (
    <section className="rounded-[28px] border border-emerald-100 bg-white p-6 shadow-[0_18px_55px_rgba(28,25,23,0.07)]">
      <p className="text-xs font-semibold uppercase tracking-[0.18em] text-emerald-700">круг меценатов</p>
      <h2 className="mt-2 text-xl font-semibold text-stone-950">Круг меценатов</h2>
      <p className="mt-3 text-sm leading-6 text-stone-600">Спасибо за вклад в развитие сообщества.</p>
      {impact.patron_since ? <p className="mt-2 text-sm text-stone-500">В круге с {formatMonth(impact.patron_since)}</p> : null}
      <Link href="/community/patrons" className="mt-4 inline-flex rounded-full bg-stone-100 px-4 py-2 text-sm font-semibold text-stone-800 transition hover:bg-emerald-50 hover:text-emerald-800">
        Посмотреть Круг меценатов
      </Link>
    </section>
  );
}

function Achievements({ achievements }: { achievements: UserAchievement[] }) {
  return (
    <section id="achievements" className="scroll-mt-24 rounded-[28px] border border-stone-200 bg-white p-6 shadow-[0_18px_55px_rgba(28,25,23,0.07)]">
      <p className="text-xs font-semibold uppercase tracking-[0.18em] text-amber-700">достижения</p>
      <h2 className="mt-2 text-xl font-semibold text-stone-950">Ваши отметки участия</h2>
      <div className="mt-5 space-y-2">
        {achievements.length ? achievements.map((achievement) => (
          <div key={achievement.code} className="flex gap-3 rounded-2xl bg-amber-50/70 px-4 py-3">
            <span className="flex h-9 w-9 shrink-0 items-center justify-center rounded-full bg-white text-lg shadow-sm" aria-hidden="true">★</span>
            <span>
              <strong className="block text-sm text-stone-900">{achievement.title}</strong>
              <span className="mt-1 block text-xs leading-5 text-stone-500">{achievement.description}</span>
              <span className="mt-1 block text-xs text-stone-400">{formatMonth(achievement.unlocked_at)}</span>
            </span>
          </div>
        )) : <p className="text-sm leading-6 text-stone-600">Ваш путь помощи только начинается.</p>}
      </div>
    </section>
  );
}

function Reputation({ summary, level }: { summary: ProfileSummary; level: string }) {
  return (
    <section className="rounded-[28px] border border-emerald-100 bg-[linear-gradient(145deg,#ffffff,#ecfdf5)] p-6 shadow-[0_18px_55px_rgba(28,25,23,0.07)]">
      <p className="text-xs font-semibold uppercase tracking-[0.18em] text-emerald-700">репутация</p>
      <h2 className="mt-2 text-xl font-semibold text-stone-950">Статус в сообществе</h2>
      <div className="mt-5 divide-y divide-emerald-100">
        {summary.confirmed_contributions_count === 0 ? <ReputationRow label="История участия еще не началась" value="" /> : <ReputationRow label="Подтвержденных вкладов" value={String(summary.confirmed_contributions_count)} />}
        <ReputationRow label="Уровень участия" value={level} />
        <ReputationRow label="Создание сборов" value={summary.can_create_campaign ? "Открыто" : "Пока закрыто"} />
      </div>
    </section>
  );
}

function ReputationRow({ label, value }: { label: string; value: string }) {
  return <div className="flex items-center justify-between gap-3 py-3 text-sm"><span className="text-stone-500">{label}</span><strong className="text-right text-stone-950">{value}</strong></div>;
}

function relativeTime(value: string) {
  const minutes = Math.max(0, Math.floor((Date.now() - new Date(value).getTime()) / 60000));
  if (minutes < 1) return "только что";
  if (minutes < 60) return `${minutes} мин назад`;
  const hours = Math.floor(minutes / 60);
  if (hours < 24) return `${hours} ч назад`;
  return `${Math.floor(hours / 24)} дн назад`;
}

function formatMonth(value: string) {
  return new Intl.DateTimeFormat("ru-RU", { month: "long", year: "numeric" }).format(new Date(value));
}

function nextLevelThreshold(level: string) {
  if (level === "Помощник") return 1;
  if (level === "Участник") return 5;
  if (level === "Наставник") return 20;
  if (level === "Меценат") return 50;
  return 100;
}

function pluralize(value: number, one: string, few: string, many: string) {
  const mod10 = value % 10;
  const mod100 = value % 100;
  const word = mod10 === 1 && mod100 !== 11 ? one : mod10 >= 2 && mod10 <= 4 && (mod100 < 12 || mod100 > 14) ? few : many;
  return `${value} ${word}`;
}

function ProfileAvatar({ name, username, avatarUrl }: { name: string; username: string; avatarUrl?: string | null }) {
  if (avatarUrl) {
    return (
      <div
        aria-label={`Фото пользователя ${name}`}
        className="h-28 w-28 rounded-full bg-cover bg-center shadow-[0_18px_50px_rgba(0,0,0,0.28)] ring-4 ring-white/15 md:h-32 md:w-32"
        style={{ backgroundImage: `url(${avatarUrl})` }}
      />
    );
  }

  return (
    <div
      aria-label={`Аватар пользователя ${username}`}
      className="flex h-28 w-28 items-center justify-center rounded-full bg-[linear-gradient(135deg,#bbf7d0,#6ee7b7_45%,#fef3c7)] text-4xl font-semibold text-stone-950 shadow-[0_18px_50px_rgba(0,0,0,0.22)] ring-4 ring-white/15 md:h-32 md:w-32"
    >
      {(name || username).slice(0, 1).toUpperCase()}
    </div>
  );
}

function ProfileInput({ label, value, onChange, maxLength }: { label: string; value: string; onChange: (value: string) => void; maxLength: number }) {
  return (
    <label className="block">
      <span className="text-xs font-semibold uppercase tracking-[0.12em] text-stone-500">{label}</span>
      <input
        value={value}
        onChange={(event) => onChange(event.target.value)}
        maxLength={maxLength}
        className="mt-2 w-full rounded-2xl border border-stone-200 px-4 py-3 text-sm outline-none transition focus:border-emerald-500 focus:ring-4 focus:ring-emerald-100"
      />
    </label>
  );
}

function fullName(firstName?: string | null, lastName?: string | null) {
  return [firstName, lastName].filter(Boolean).join(" ").trim();
}

function emptyToNull(value: string) {
  const trimmed = value.trim();
  return trimmed || null;
}

function syncAuthUser(user: AuthUser) {
  localStorage.setItem("auth_user", JSON.stringify(user));
  window.dispatchEvent(new CustomEvent("auth:updated", { detail: user }));
}

function LoadingCard() {
  return <div className="rounded-[28px] border border-stone-200 bg-white p-5 text-stone-600 shadow-sm">Загружаем профиль...</div>;
}

function ProfileError({ message }: { message: string }) {
  return <div className="rounded-[24px] border border-rose-100 bg-rose-50 px-5 py-4 text-sm leading-6 text-rose-800">{message}</div>;
}
