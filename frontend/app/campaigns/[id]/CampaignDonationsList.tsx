import Link from "next/link";
import { formatMoney } from "@/lib/format";
import type { RecentDonation } from "@/lib/types";

export function CampaignDonationsList({
  donations,
  hasMore,
  isLoadingMore,
  newDonationId,
  onLoadMore,
}: {
  donations: RecentDonation[];
  hasMore: boolean;
  isLoadingMore: boolean;
  newDonationId: string | null;
  onLoadMore: () => void;
}) {
  return (
    <section className="editorial-plane editorial-plane-warm mx-auto max-w-3xl py-16 md:py-24">
      <div>
        <h2 className="text-2xl font-semibold tracking-[-0.02em] text-stone-950">Последние участники</h2>
        <p className="mt-1 text-sm text-stone-500">Свежие подтверждённые вклады — от новых к более ранним.</p>
      </div>

      <div className="mt-5 divide-y divide-stone-200 border-y border-stone-200">
        {donations.length ? (
          donations.map((donation) => (
            <DonationRow key={donation.id} donation={donation} isNew={newDonationId === donation.id} />
          ))
        ) : (
          <p className="text-sm leading-6 text-stone-600">
            Станьте первым человеком, который поддержит этот сбор. Даже небольшой первый вклад оживляет страницу.
          </p>
        )}
      </div>

      {hasMore ? (
        <button
          onClick={onLoadMore}
          disabled={isLoadingMore}
          className="mt-4 w-full rounded-full border border-stone-200 bg-white px-5 py-3 text-sm font-semibold text-stone-800 transition hover:border-emerald-300 hover:bg-emerald-50 disabled:cursor-wait disabled:opacity-60"
          type="button"
        >
          {isLoadingMore ? "Загружаем…" : "Показать ещё"}
        </button>
      ) : null}
    </section>
  );
}

function DonationRow({ donation, isNew }: { donation: RecentDonation; isNew: boolean }) {
  const isAnonymous = donation.username === "Анонимно";

  return (
    <div
      className={`py-4 transition duration-500 hover:bg-white/60 ${
        isNew ? "rounded-2xl bg-emerald-50 px-3 ring-4 ring-emerald-100" : ""
      }`}
    >
      <div className="flex items-center justify-between gap-3">
        <div className="flex min-w-0 items-center gap-3">
          <div className="flex h-9 w-9 shrink-0 items-center justify-center rounded-full bg-emerald-50 text-xs font-semibold text-emerald-800 ring-1 ring-emerald-100">
            {isAnonymous ? "А" : donation.username.slice(0, 1).toUpperCase()}
          </div>
          <div className="min-w-0">
            {isAnonymous ? (
              <p className="truncate font-semibold text-stone-950">Анонимно</p>
            ) : (
              <Link href={`/u/${donation.username}`} className="block truncate font-semibold text-stone-950 hover:text-emerald-800">
                {donation.username}
              </Link>
            )}
            <p className="mt-1 text-sm text-stone-500">{relativeTime(donation.created_at)}</p>
          </div>
        </div>
        <p className="shrink-0 font-semibold text-emerald-700">{formatMoney(donation.amount)}</p>
      </div>
    </div>
  );
}

function relativeTime(value: string) {
  const diff = Date.now() - new Date(value).getTime();
  const minutes = Math.max(0, Math.floor(diff / 60000));
  if (minutes < 1) return "только что";
  if (minutes === 1) return "1 минуту назад";
  if (minutes < 60) return `${minutes} мин назад`;

  const hours = Math.floor(minutes / 60);
  if (hours === 1) return "1 час назад";
  if (hours < 24) return `${hours} ч назад`;

  const days = Math.floor(hours / 24);
  return days === 1 ? "1 день назад" : `${days} дн назад`;
}
