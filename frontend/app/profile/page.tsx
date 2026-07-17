"use client";

import Link from "next/link";
import { useEffect, useState } from "react";
import { useRouter } from "next/navigation";
import { CampaignCard } from "@/app/components/CampaignCard";
import { ProfileHero } from "@/components/profile-hero";
import { useAuth } from "@/components/providers/auth-provider";
import { fetchProfileImpact, fetchProfileSummary, fetchPublicProfile, fetchUserAchievements, resendEmailVerification, updateProfile, uploadAvatar } from "@/lib/api";
import { formatMoney } from "@/lib/format";
import { getImageValidationError, IMAGE_INPUT_ACCEPT, MAX_IMAGE_SIZE_MB } from "@/lib/image-upload";
import type { AuthUser, CampaignListItem, ProfileImpact, ProfileSummary, UserAchievement } from "@/lib/types";

export default function ProfilePage() {
  const router = useRouter();
  const { user, isAuthenticated, isLoading, refreshAuth } = useAuth();
  const [summary, setSummary] = useState<ProfileSummary | null>(null);
  const [impact, setImpact] = useState<ProfileImpact | null>(null);
  const [achievements, setAchievements] = useState<UserAchievement[]>([]);
  const [createdCampaigns, setCreatedCampaigns] = useState<CampaignListItem[] | null>(null);
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
    if (!isAuthenticated || !user?.username) return;
    Promise.all([fetchProfileSummary(), fetchProfileImpact(), fetchUserAchievements(), fetchPublicProfile(user.username)])
      .then(([freshSummary, freshImpact, freshAchievements, publicProfile]) => {
        setSummary(freshSummary);
        setImpact(freshImpact);
        setAchievements(freshAchievements);
        setCreatedCampaigns(publicProfile.campaigns_created);
      })
      .catch((requestError) => setError(requestError instanceof Error ? requestError.message : "Не удалось загрузить профиль."));
  }, [isAuthenticated, user?.username]);

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
  if (!summary || !impact || createdCampaigns === null) return error ? <ProfileError message={error} /> : <LoadingCard />;

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

    const validationError = getImageValidationError(file);
    if (validationError) {
      setProfileStatus(validationError);
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
    <section className="pb-12 md:pb-20">
      <ProfileHero
        name={displayName}
        username={user.username}
        avatarUrl={profileForm.avatar_url || user.avatar_url}
        eyebrow="ваш профиль"
        metadata={[
          user.is_verified ? <span className="font-semibold text-emerald-200">Email подтверждён</span> : null,
          <>С нами с {formatMonth(user.created_at)}</>,
          user.city ? <span className="break-words [overflow-wrap:anywhere]">{user.city}</span> : null,
        ].filter(Boolean)}
        description={user.bio || "Расскажите немного о себе: чем занимаетесь, почему вы на платформе и что для вас значит взаимопомощь."}
        action={
          <Link href={`/u/${user.username}`} className="inline-flex min-h-11 items-center text-sm font-semibold text-emerald-200 underline decoration-emerald-200/30 underline-offset-4 hover:decoration-emerald-200">
            Посмотреть публичный профиль →
          </Link>
        }
      />

      <details className="group mt-5 border-b border-stone-200 md:mt-7">
        <summary className="flex min-h-14 cursor-pointer list-none items-center justify-between gap-4 py-3 [&::-webkit-details-marker]:hidden">
          <span>
            <span className="block font-semibold text-stone-950">Редактировать профиль</span>
            <span className="mt-0.5 block text-sm text-stone-500">Имя, фотография, город и описание</span>
          </span>
          <span className="text-xl text-stone-400 transition group-open:rotate-45" aria-hidden="true">+</span>
        </summary>
        <form onSubmit={handleProfileSubmit} className="max-w-4xl pb-8 pt-3 text-stone-950">
            <div className="flex items-center justify-between gap-3">
              <div>
                <h2 className="text-xl font-semibold">Личные данные</h2>
                <p className="mt-1 text-sm text-stone-500">Эти данные будут видны в вашем публичном профиле.</p>
              </div>
              <label className="flex min-h-11 cursor-pointer items-center rounded-full bg-stone-100 px-4 py-2 text-sm font-semibold text-stone-800 transition hover:bg-emerald-50 hover:text-emerald-800">
                {isAvatarUploading ? "Загрузка..." : "Изменить фото"}
                <input className="sr-only" type="file" accept={IMAGE_INPUT_ACCEPT} onChange={handleAvatarChange} disabled={isAvatarUploading || isProfileSaving} />
              </label>
            </div>
            <p className="mt-2 text-xs text-stone-500">JPG, PNG или WebP, до {MAX_IMAGE_SIZE_MB} МБ.</p>
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
                className="mt-2 w-full resize-none rounded-xl border border-stone-300 bg-white px-4 py-3 text-sm outline-none transition focus:border-emerald-500 focus:ring-4 focus:ring-emerald-100"
              />
            </label>
            <div className="mt-3 flex flex-col gap-3 sm:flex-row sm:items-center sm:justify-between">
              <span className="text-xs text-stone-500">{profileForm.bio.length}/250</span>
              <button className="min-h-12 w-full rounded-full bg-stone-950 px-5 py-3 text-sm font-semibold text-white transition hover:bg-emerald-800 disabled:cursor-wait disabled:opacity-60 sm:w-auto" disabled={isProfileSaving || isAvatarUploading} type="submit">
                {isProfileSaving ? "Сохраняем..." : "Сохранить профиль"}
              </button>
            </div>
            {profileStatus ? <p className="mt-3 text-sm leading-6 text-stone-600">{profileStatus}</p> : null}
        </form>
      </details>

      {!user.is_verified ? (
        <section className="mt-6 border-y border-amber-200 bg-amber-50/60 py-5">
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

      <section aria-labelledby="profile-reputation-title" className="editorial-plane editorial-plane-white mt-16 grid gap-10 py-14 md:mt-24 md:py-20 lg:grid-cols-[0.8fr_1.2fr]">
        <div>
          <p className="text-xs font-semibold uppercase tracking-[0.18em] text-emerald-700">репутация участника</p>
          <h2 id="profile-reputation-title" className="mt-2 text-3xl font-semibold tracking-[-0.025em] text-stone-950">Факты о помощи</h2>
          <p className="mt-3 max-w-md text-sm leading-6 text-stone-600">Подтверждённые действия важнее декоративных статусов.</p>
        </div>
        <div>
          <Reputation summary={summary} level={level} />
        </div>
      </section>

      <Achievements achievements={achievements} />

      <section aria-labelledby="participation-history-title" className="editorial-plane editorial-plane-warm py-16 md:py-24">
        <h2 id="participation-history-title" className="text-3xl font-semibold tracking-[-0.025em] text-stone-950">История участия</h2>
        <div className="mt-6 grid gap-6 lg:grid-cols-2">
          <ParticipationHistory contributions={summary.recent_contributions} />
          <ParticipantJourney timeline={summary.timeline} />
        </div>
        <div className="mt-6 grid gap-6 lg:grid-cols-2">
          <RecentActivity summary={summary} />
          <PatronCircle impact={impact} />
        </div>
      </section>

      <section aria-labelledby="created-campaigns-title" className="editorial-plane editorial-plane-white py-16 md:py-24">
        <p className="text-xs font-semibold uppercase tracking-[0.18em] text-emerald-700">созданные сборы</p>
        <h2 id="created-campaigns-title" className="mt-2 text-3xl font-semibold tracking-[-0.025em] text-stone-950">Ваши истории</h2>
        {createdCampaigns.length ? (
          <div className="mt-6 grid gap-5 md:grid-cols-2 xl:grid-cols-3">
            {createdCampaigns.map((campaign) => <CampaignCard key={campaign.id} campaign={campaign} />)}
          </div>
        ) : (
          <div className="mt-5 border-y border-stone-200 py-6">
            <p className="text-sm leading-6 text-stone-600">Вы пока не создавали сборов. Сначала поддержите другие истории — возможность рассказать свою откроется после выполнения условий участия.</p>
            {summary.can_create_campaign ? <Link href="/campaigns/new" className="mt-4 inline-flex min-h-11 items-center font-semibold text-emerald-800 hover:text-emerald-950">Открыть сбор →</Link> : null}
          </div>
        )}
      </section>
    </section>
  );
}

function RecentActivity({ summary }: { summary: ProfileSummary }) {
  const hasRecentActivity = summary.contributions_last_30_days > 0;
  return (
    <section className="border-t border-stone-200 pt-6">
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
  return <div className="border-l border-stone-200 px-3 py-2"><p className="text-xl font-semibold text-stone-950">{prefix}{value}</p><p className="mt-1 text-[11px] uppercase tracking-wide text-stone-500">{label}</p></div>;
}

function ParticipantJourney({ timeline }: { timeline: ProfileSummary["timeline"] }) {
  return (
    <section className="border-t border-stone-200 pt-6">
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
    <section className="border-t border-stone-200 pt-6">
      <p className="text-xs font-semibold uppercase tracking-[0.18em] text-emerald-700">история участия</p>
      <h2 className="mt-2 text-xl font-semibold text-stone-950">Последние действия</h2>
      <div className="mt-5 space-y-2">
        {contributions.length ? contributions.map((contribution) => (
          <Link href={`/campaigns/${contribution.campaign_id}`} key={contribution.id} className="flex items-center justify-between gap-3 border-b border-stone-100 py-3 transition hover:text-emerald-800">
            <span className="min-w-0"><span className="block truncate text-sm font-semibold text-stone-800">Поддержал сбор «{contribution.campaign_title}»</span><span className="mt-1 block text-xs text-stone-400">{relativeTime(contribution.created_at)}</span></span>
            <strong className="shrink-0 text-sm text-emerald-700">+{formatMoney(contribution.amount)}</strong>
          </Link>
        )) : <p className="rounded-2xl bg-stone-50 px-4 py-5 text-sm leading-6 text-stone-600">Здесь появится ваша история поддержки. Выберите первый сбор, который вам близок.</p>}
      </div>
    </section>
  );
}

function PatronCircle({ impact }: { impact: ProfileImpact }) {
  if (!impact.is_patron) return null;

  return (
    <section className="border-t border-stone-200 pt-6">
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
    <section id="achievements" className="editorial-plane editorial-plane-quiet scroll-mt-24 py-14 md:py-20">
      <p className="text-xs font-semibold uppercase tracking-[0.18em] text-amber-700">достижения</p>
      <h2 className="mt-2 text-xl font-semibold text-stone-950">Ваши отметки участия</h2>
      <div className="mt-5 space-y-2">
        {achievements.length ? achievements.map((achievement) => (
          <div key={achievement.code} className="flex gap-3 border-l-2 border-amber-400 bg-amber-50/60 px-4 py-3">
            <span className="flex h-9 w-9 shrink-0 items-center justify-center text-lg" aria-hidden="true">★</span>
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
    <section className="border-t border-stone-200 pt-6">
      <p className="text-xs font-semibold uppercase tracking-[0.18em] text-emerald-700">репутация</p>
      <h2 className="mt-2 text-xl font-semibold text-stone-950">Статус в сообществе</h2>
      <div className="mt-5 divide-y divide-stone-200">
        {summary.confirmed_contributions_count === 0 ? <ReputationRow label="История участия ещё не началась" value="" /> : <ReputationRow label="Подтверждённых вкладов" value={String(summary.confirmed_contributions_count)} />}
        <ReputationRow label="Поддержано историй" value={String(summary.supported_campaigns_count)} />
        <ReputationRow label="Уровень участия" value={level} />
        <ReputationRow label={`Создание сборов · порог ${summary.required_contributions_count}`} value={summary.can_create_campaign ? "Доступно" : `${summary.confirmed_contributions_count} из ${summary.required_contributions_count}`} />
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

function ProfileInput({ label, value, onChange, maxLength }: { label: string; value: string; onChange: (value: string) => void; maxLength: number }) {
  return (
    <label className="block">
      <span className="text-xs font-semibold uppercase tracking-[0.12em] text-stone-500">{label}</span>
      <input
        value={value}
        onChange={(event) => onChange(event.target.value)}
        maxLength={maxLength}
        className="mt-2 w-full rounded-xl border border-stone-300 bg-white px-4 py-3 text-sm outline-none transition focus:border-emerald-500 focus:ring-4 focus:ring-emerald-100"
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
  return <div className="border-y border-stone-200 py-6 text-stone-600">Загружаем профиль...</div>;
}

function ProfileError({ message }: { message: string }) {
  return <div className="border-y border-rose-200 bg-rose-50/60 py-5 text-sm leading-6 text-rose-800">{message}</div>;
}
