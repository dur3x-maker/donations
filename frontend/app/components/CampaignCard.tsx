import Link from "next/link";
import type { CampaignListItem } from "@/lib/types";
import { amountLeft, formatMoney } from "@/lib/format";
import { ProgressBar } from "./ProgressBar";

type CampaignCardProps = {
  campaign: CampaignListItem;
};

const categoryLabels: Record<string, string> = {
  medical: "лечение",
  education: "образование",
  emergency: "срочно",
  pets: "животные",
  community: "сообщество",
  personal: "личное",
  other: "другое",
};

export function CampaignCard({ campaign }: CampaignCardProps) {
  const left = amountLeft(campaign.current_amount, campaign.target_amount);

  return (
    <Link
      href={`/campaigns/${campaign.id}`}
      className="group block h-full overflow-hidden rounded-[14px] border border-stone-200 bg-white outline-none transition hover:border-emerald-400 focus-visible:ring-4 focus-visible:ring-emerald-200"
    >
      <div className="flex h-full flex-col">
        <div className="relative aspect-[16/10] overflow-hidden bg-stone-100">
          {campaign.cover_image_url ? (
            <img src={campaign.cover_image_url} alt="" className="h-full w-full object-cover transition duration-500 group-hover:scale-[1.03]" />
          ) : (
            <div className="h-full w-full bg-[#e9ded1]" />
          )}
          <div className="absolute left-3 top-3 bg-white/95 px-2.5 py-1 text-xs font-medium text-stone-700">
            {categoryLabels[campaign.category] ?? campaign.category}
          </div>
        </div>

        <div className="flex flex-1 flex-col p-5">
          <h3 className="break-words text-xl font-semibold leading-tight tracking-[-0.015em] text-stone-950 [overflow-wrap:anywhere]">{campaign.title}</h3>
          <p className="mt-2 line-clamp-2 text-sm leading-6 text-stone-600">{campaign.description_preview}</p>

          <div className="mt-auto pt-5">
            <div className="mb-2 flex items-end justify-between gap-4 border-t border-stone-100 pt-4">
              <div>
                <p className="text-xs text-stone-400">собрано</p>
                <p className="text-xl font-semibold text-stone-950">{formatMoney(campaign.current_amount)}</p>
              </div>
              <p className="text-right text-sm text-stone-500">осталось {formatMoney(left)}</p>
            </div>
            <ProgressBar value={campaign.progress_percentage} />
            <div className="mt-4 flex items-center justify-between gap-3 text-sm">
              <span className="text-stone-500">{campaign.progress_percentage}% цели</span>
              <span className="font-semibold text-stone-950 group-hover:text-emerald-800">Открыть</span>
            </div>
          </div>
        </div>
      </div>
    </Link>
  );
}
