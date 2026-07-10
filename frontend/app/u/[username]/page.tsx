import { CampaignCard } from "@/app/components/CampaignCard";
import { fetchPublicProfile } from "@/lib/api";
import { formatMoney } from "@/lib/format";

export default async function PublicProfilePage({ params }: { params: { username: string } }) {
  const profile = await fetchPublicProfile(params.username);
  const displayName = fullName(profile.first_name, profile.last_name) || profile.username;
  const authorReputation = profile.author_reputation;
  const totalRaisedAmount = Number(authorReputation.total_raised_amount);
  const hasRaisedAmount = totalRaisedAmount > 0;
  const authorFacts = [
    `Создал ${formatCount(authorReputation.campaigns_created, ["историю", "истории", "историй"])}`,
    authorReputation.campaigns_completed > 0
      ? `Довёл до результата ${formatCount(authorReputation.campaigns_completed, ["историю", "истории", "историй"])}`
      : "Завершённые истории ещё впереди",
    authorReputation.campaigns_with_reports > 0
      ? `Опубликовал ${formatCount(authorReputation.campaigns_with_reports, ["итоговый отчёт", "итоговых отчёта", "итоговых отчётов"])}`
      : "Итоговых отчётов пока нет",
  ];

  return (
    <section className="space-y-8">
      <div className="overflow-hidden rounded-[32px] bg-stone-950 p-6 text-white shadow-[0_24px_80px_rgba(28,25,23,0.20)] md:p-10">
        <div className="grid gap-6 md:grid-cols-[auto_minmax(0,1fr)] md:items-center">
          <ProfileAvatar name={displayName} username={profile.username} avatarUrl={profile.avatar_url} />
          <div className="min-w-0">
            <div className="flex flex-wrap items-center gap-2">
              <h1 className="min-w-0 text-3xl font-semibold tracking-tight md:text-5xl">{displayName}</h1>
              {profile.is_verified ? <span className="rounded-full bg-emerald-100 px-3 py-1.5 text-xs font-semibold text-emerald-900">Проверенный пользователь</span> : null}
            </div>
            <p className="mt-2 text-lg font-medium text-stone-300">@{profile.username}</p>
            <div className="mt-4 flex flex-wrap gap-2 text-sm text-stone-200">
              <span className="rounded-full bg-white/10 px-3 py-1.5 ring-1 ring-white/10">С нами с {formatProfileMonth(profile.created_at)}</span>
              {profile.city ? <span className="rounded-full bg-white/10 px-3 py-1.5 ring-1 ring-white/10">{profile.city}</span> : null}
            </div>
            {profile.bio ? (
              <p className="mt-5 max-w-3xl text-lg leading-8 text-stone-100">&ldquo;{profile.bio}&rdquo;</p>
            ) : (
              <p className="mt-5 max-w-3xl text-sm leading-6 text-stone-300">Пользователь пока не добавил описание, но его участие и созданные сборы уже видны ниже.</p>
            )}
          </div>
        </div>
      </div>

      <div className="grid gap-4 md:grid-cols-3">
        <StatCard label="Поддержано" value={String(profile.supported_campaigns_count)} />
        <StatCard label="Внесено" value={formatMoney(profile.total_donated_amount)} />
        <StatCard label="Закрыто" value={String(profile.completed_campaigns_count)} />
      </div>

      <section className="rounded-[28px] border border-stone-200 bg-white p-5 shadow-[0_18px_60px_rgba(28,25,23,0.08)]">
        <div className="flex items-end justify-between gap-4">
          <div>
            <p className="text-sm uppercase tracking-[0.16em] text-stone-400">отметки</p>
            <h2 className="mt-2 text-2xl font-semibold tracking-[-0.02em] text-stone-950">{profile.achievements_count} получено</h2>
          </div>
        </div>
        {profile.achievements.length ? (
          <div className="mt-4 flex flex-wrap gap-2">
            {profile.achievements.map((achievement) => (
              <span key={achievement} className="rounded-full bg-emerald-50 px-4 py-2 text-sm font-semibold text-emerald-800 ring-1 ring-emerald-100">
                {achievementLabel(achievement)}
              </span>
            ))}
          </div>
        ) : (
          <p className="mt-4 text-sm leading-6 text-stone-600">Пока без отметок. Первый вклад обычно самый тёплый.</p>
        )}
      </section>

      <section className="overflow-hidden rounded-[28px] border border-stone-200 bg-white shadow-[0_18px_60px_rgba(28,25,23,0.08)]">
        <div className="grid gap-0 md:grid-cols-[minmax(0,1fr)_minmax(280px,0.7fr)]">
          <div className="p-5 md:p-7">
            <p className="text-sm uppercase tracking-[0.16em] text-stone-400">репутация автора</p>
            <h2 className="mt-2 max-w-2xl text-2xl font-semibold tracking-[-0.02em] text-stone-950">Факты об историях автора</h2>
            <p className="mt-5 max-w-2xl text-lg leading-8 text-stone-700">
              {hasRaisedAmount ? "За всё время благодаря этому автору удалось собрать" : "Этот автор только начинает собирать истории помощи"}
            </p>
            {hasRaisedAmount ? (
              <p className="mt-3 text-4xl font-semibold tracking-[-0.04em] text-stone-950 md:text-6xl">{formatMoney(authorReputation.total_raised_amount)}</p>
            ) : (
              <p className="mt-3 max-w-xl text-base leading-7 text-stone-600">Первые собранные суммы появятся здесь, когда его истории получат поддержку.</p>
            )}
          </div>
          <div className="border-t border-stone-200 bg-stone-50/80 p-5 md:border-l md:border-t-0 md:p-7">
            <div className="space-y-4">
              {authorFacts.map((fact) => (
                <p key={fact} className="border-b border-stone-200 pb-4 text-base leading-7 text-stone-800 last:border-0 last:pb-0">
                  {fact}
                </p>
              ))}
              {authorReputation.campaigns_without_reports > 0 ? (
                <p className="text-sm leading-6 text-stone-500">
                  Без итогового отчёта сейчас {formatCount(authorReputation.campaigns_without_reports, ["история", "истории", "историй"])}.
                </p>
              ) : null}
            </div>
          </div>
        </div>
      </section>

      <section>
        <h2 className="text-2xl font-semibold tracking-[-0.02em] text-stone-950">Созданные сборы</h2>
        {profile.campaigns_created.length ? (
          <div className="mt-5 grid gap-5 md:grid-cols-2 xl:grid-cols-3">
            {profile.campaigns_created.map((campaign) => (
              <CampaignCard key={campaign.id} campaign={campaign} />
            ))}
          </div>
        ) : (
          <div className="mt-5 rounded-[28px] border border-stone-200 bg-white p-5 text-stone-600 shadow-[0_18px_60px_rgba(28,25,23,0.08)]">
            Этот участник пока не открывал сбор, но каждая поддержка всё равно укрепляет сообщество.
          </div>
        )}
      </section>
    </section>
  );
}

function ProfileAvatar({ name, username, avatarUrl }: { name: string; username: string; avatarUrl?: string | null }) {
  if (avatarUrl) {
    return (
      <div
        aria-label={`Фото пользователя ${name}`}
        className="h-28 w-28 rounded-full bg-cover bg-center shadow-[0_18px_50px_rgba(0,0,0,0.28)] ring-4 ring-white/15 md:h-36 md:w-36"
        style={{ backgroundImage: `url(${avatarUrl})` }}
      />
    );
  }

  return (
    <div
      aria-label={`Аватар пользователя ${username}`}
      className="flex h-28 w-28 items-center justify-center rounded-full bg-[linear-gradient(135deg,#bbf7d0,#6ee7b7_45%,#fef3c7)] text-4xl font-semibold text-stone-950 shadow-[0_18px_50px_rgba(0,0,0,0.22)] ring-4 ring-white/15 md:h-36 md:w-36 md:text-5xl"
    >
      {initialsFor(name, username)}
    </div>
  );
}

function StatCard({ label, value }: { label: string; value: string }) {
  return (
    <div className="rounded-[28px] border border-stone-200 bg-white p-5 shadow-[0_18px_60px_rgba(28,25,23,0.08)]">
      <p className="text-sm uppercase tracking-[0.16em] text-stone-400">{label}</p>
      <p className="mt-2 text-3xl font-semibold text-stone-950">{value}</p>
    </div>
  );
}

function fullName(firstName?: string | null, lastName?: string | null) {
  return [firstName, lastName].filter(Boolean).join(" ").trim();
}

function initialsFor(name: string, username: string) {
  return (name || username).slice(0, 1).toUpperCase();
}

function formatProfileMonth(value: string) {
  return new Intl.DateTimeFormat("ru-RU", { month: "long", year: "numeric" }).format(new Date(value));
}

function formatCount(value: number, forms: [string, string, string]) {
  const mod10 = value % 10;
  const mod100 = value % 100;
  const form = mod10 === 1 && mod100 !== 11 ? forms[0] : mod10 >= 2 && mod10 <= 4 && (mod100 < 12 || mod100 > 14) ? forms[1] : forms[2];

  return `${value} ${form}`;
}

function achievementLabel(value: string) {
  if (value === "first_support") return "Первый вклад";
  if (value === "supporter_5") return "5 поддержек";
  if (value === "campaign_creator") return "Автор сбора";
  if (value === "fundraiser_completed") return "Сбор закрыт";
  return value;
}
