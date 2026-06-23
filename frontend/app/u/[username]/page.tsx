import { CampaignCard } from "@/app/components/CampaignCard";
import { fetchPublicProfile } from "@/lib/api";
import { formatDate, formatMoney } from "@/lib/format";

export default async function PublicProfilePage({ params }: { params: { username: string } }) {
  const profile = await fetchPublicProfile(params.username);

  return (
    <section className="space-y-8">
      <div className="rounded-[32px] bg-stone-950 p-6 text-white shadow-[0_24px_80px_rgba(28,25,23,0.20)] md:p-10">
        <div className="flex flex-wrap items-center gap-4">
          <div className="flex h-16 w-16 items-center justify-center rounded-full bg-emerald-100 text-2xl font-semibold text-emerald-900">
            {profile.username.slice(0, 1).toUpperCase()}
          </div>
          <div>
            <div className="flex flex-wrap items-center gap-2">
              <h1 className="text-3xl font-semibold tracking-tight md:text-5xl">{profile.username}</h1>
              {profile.is_verified ? <span className="rounded-full bg-emerald-100 px-3 py-1.5 text-xs font-semibold text-emerald-900">проверено</span> : null}
            </div>
            <p className="mt-2 text-sm text-stone-300">С нами с {formatDate(profile.created_at)}</p>
          </div>
        </div>
      </div>

      <div className="grid gap-4 md:grid-cols-3">
        <div className="rounded-[28px] border border-stone-200 bg-white p-5 shadow-[0_18px_60px_rgba(28,25,23,0.08)]">
          <p className="text-sm uppercase tracking-[0.16em] text-stone-400">поддержано</p>
          <p className="mt-2 text-3xl font-semibold text-stone-950">{profile.supported_campaigns_count}</p>
        </div>
        <div className="rounded-[28px] border border-stone-200 bg-white p-5 shadow-[0_18px_60px_rgba(28,25,23,0.08)]">
          <p className="text-sm uppercase tracking-[0.16em] text-stone-400">внесено</p>
          <p className="mt-2 text-3xl font-semibold text-stone-950">{formatMoney(profile.total_donated_amount)}</p>
        </div>
        <div className="rounded-[28px] border border-stone-200 bg-white p-5 shadow-[0_18px_60px_rgba(28,25,23,0.08)]">
          <p className="text-sm uppercase tracking-[0.16em] text-stone-400">закрыто</p>
          <p className="mt-2 text-3xl font-semibold text-stone-950">{profile.completed_campaigns_count}</p>
        </div>
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
          <p className="mt-4 text-sm leading-6 text-stone-600">Пока без отметок. Первый вклад обычно самый теплый.</p>
        )}
      </section>

      <section className="rounded-[28px] border border-stone-200 bg-white p-5 shadow-[0_18px_60px_rgba(28,25,23,0.08)]">
        <p className="text-sm uppercase tracking-[0.16em] text-stone-400">репутация автора</p>
        <h2 className="mt-2 text-2xl font-semibold tracking-[-0.02em] text-stone-950">Факты об историях автора</h2>
        <div className="mt-5 grid gap-3 md:grid-cols-5">
          <AuthorFact label="Историй создано" value={String(profile.author_reputation.campaigns_created)} />
          <AuthorFact label="Успешно завершено" value={String(profile.author_reputation.campaigns_completed)} />
          <AuthorFact label="Всего собрано" value={formatMoney(profile.author_reputation.total_raised_amount)} />
          <AuthorFact label="Отчеты опубликованы" value={String(profile.author_reputation.campaigns_with_reports)} />
          <AuthorFact label="Без отчета" value={String(profile.author_reputation.campaigns_without_reports)} />
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
            Этот участник пока не открывал сбор, но каждая поддержка все равно укрепляет сообщество.
          </div>
        )}
      </section>
    </section>
  );
}

function AuthorFact({ label, value }: { label: string; value: string }) {
  return (
    <div className="rounded-[20px] bg-stone-50 p-4">
      <p className="text-xs font-semibold uppercase tracking-[0.12em] text-stone-400">{label}</p>
      <p className="mt-2 text-xl font-semibold text-stone-950">{value}</p>
    </div>
  );
}

function achievementLabel(value: string) {
  if (value === "first_support") return "Первый вклад";
  if (value === "supporter_5") return "5 поддержек";
  if (value === "campaign_creator") return "Автор сбора";
  if (value === "fundraiser_completed") return "Сбор закрыт";
  return value;
}
