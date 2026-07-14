import Link from "next/link";
import { formatDate, formatMoney } from "@/lib/format";
import type { CommunityPatron } from "@/lib/types";

export function PatronCommunityCard({ patron }: { patron: CommunityPatron }) {
  return (
    <article className="flex h-full flex-col border-t border-stone-200 pt-6">
      <div className="flex items-start gap-3">
        <div className="flex h-12 w-12 shrink-0 items-center justify-center rounded-full bg-emerald-100 text-lg font-semibold text-emerald-900">
          {patron.username.slice(0, 1).toUpperCase()}
        </div>
        <div className="min-w-0">
          <Link href={`/u/${patron.username}`} className="block truncate text-xl font-semibold text-stone-950 hover:text-emerald-800">
            {patron.username}
          </Link>
          <p className="mt-1 text-sm text-stone-500">В Круге с {formatDate(patron.patron_since)}</p>
        </div>
      </div>

      <div className="mt-5 grid grid-cols-3 gap-2">
        <PatronMetric label="Вкладов" value={String(patron.confirmed_contributions_count)} />
        <PatronMetric label="Историй" value={String(patron.supported_campaigns_count)} />
        <PatronMetric label="Помощь" value={formatMoney(patron.total_donated_amount)} compact />
      </div>

      <div className="mt-6 border-t border-stone-100 pt-5">
        <h3 className="font-semibold text-stone-950">Недавно поддержал</h3>
        {patron.recent_supported_campaigns.length ? (
          <div className="mt-3 space-y-2">
            {patron.recent_supported_campaigns.map((campaign) => (
              <Link
                key={campaign.id}
                href={`/campaigns/${campaign.id}`}
                className="group flex items-center gap-3 border-b border-stone-100 py-3 transition hover:text-emerald-900"
              >
                {campaign.cover_image_url ? (
                  <img src={campaign.cover_image_url} alt="" className="h-12 w-12 shrink-0 rounded-xl object-cover" />
                ) : (
                  <div className="h-12 w-12 shrink-0 rounded-xl bg-[#e9ded1]" />
                )}
                <div className="min-w-0">
                  <p className="line-clamp-1 font-semibold text-stone-800 group-hover:text-emerald-900">{campaign.title}</p>
                  <p className="mt-0.5 text-xs text-stone-500">Поддержана {formatDate(campaign.last_supported_at)}</p>
                </div>
              </Link>
            ))}
          </div>
        ) : (
          <p className="mt-2 text-sm leading-6 text-stone-500">Истории поддержки появятся после следующих вкладов.</p>
        )}
      </div>
    </article>
  );
}

function PatronMetric({ label, value, compact = false }: { label: string; value: string; compact?: boolean }) {
  return (
    <div className="min-w-0 border-l border-stone-200 px-3 py-2">
      <p className="text-[10px] font-semibold uppercase tracking-[0.1em] text-stone-400">{label}</p>
      <p className={`mt-1 truncate font-semibold text-stone-950 ${compact ? "text-sm" : "text-lg"}`} title={value}>
        {value}
      </p>
    </div>
  );
}
