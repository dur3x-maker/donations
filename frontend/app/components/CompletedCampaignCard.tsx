import Link from "next/link";
import type { CompletedCampaignListItem } from "@/lib/types";
import { formatDate, formatMoney } from "@/lib/format";

export function CompletedCampaignCard({ campaign }: { campaign: CompletedCampaignListItem }) {
  return (
    <Link
      href={`/campaigns/${campaign.id}`}
      className="group flex h-full flex-col overflow-hidden rounded-[20px] border border-stone-200 bg-white shadow-sm outline-none transition hover:-translate-y-0.5 hover:border-emerald-200 hover:shadow-[0_22px_60px_rgba(28,25,23,0.10)] focus-visible:ring-4 focus-visible:ring-emerald-200"
    >
      <div className="relative aspect-[16/10] overflow-hidden bg-stone-100">
        {campaign.cover_image_url ? (
          <img
            src={campaign.cover_image_url}
            alt=""
            className="h-full w-full object-cover transition duration-500 group-hover:scale-[1.025]"
          />
        ) : (
          <div className="h-full w-full bg-[#e9ded1]" />
        )}
        <span className="absolute left-3 top-3 rounded-full bg-emerald-700 px-3 py-1 text-xs font-semibold text-white shadow-sm">
          помощь дошла
        </span>
      </div>

      <div className="flex flex-1 flex-col p-5">
        <h3 className="text-xl font-semibold leading-tight text-stone-950">{campaign.title}</h3>
        <div className="mt-2 flex flex-wrap items-center gap-x-3 gap-y-1 text-sm text-stone-500">
          <span>{campaign.owner?.username ? `Автор: ${campaign.owner.username}` : "Автор не указан"}</span>
          {campaign.report_completed_at ? <span>Завершена {formatDate(campaign.report_completed_at)}</span> : null}
        </div>

        {campaign.completion_report_preview ? (
          <p className="mt-4 line-clamp-2 text-sm leading-6 text-stone-600">{campaign.completion_report_preview}</p>
        ) : (
          <p className="mt-4 text-sm leading-6 text-stone-400">Итоговый отчёт пока без описания.</p>
        )}

        {campaign.completion_photos.length ? (
          <div className="mt-4 flex gap-2" aria-label="Фотографии результата">
            {campaign.completion_photos.slice(0, 4).map((photo) => (
              <img
                key={photo.id}
                src={photo.image_url}
                alt=""
                className="h-14 w-14 rounded-xl border border-stone-200 object-cover"
              />
            ))}
          </div>
        ) : null}

        <div className="mt-auto flex items-end justify-between gap-4 border-t border-stone-100 pt-5">
          <div>
            <p className="text-xs text-stone-400">собрано</p>
            <p className="mt-1 text-2xl font-semibold text-stone-950">{formatMoney(campaign.current_amount)}</p>
          </div>
          <span className="text-sm font-semibold text-emerald-800 group-hover:text-emerald-950">Результат →</span>
        </div>
      </div>
    </Link>
  );
}
