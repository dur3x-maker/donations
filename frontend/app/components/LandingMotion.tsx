import Link from "next/link";
import type { CampaignListItem, PlatformStats } from "@/lib/types";
import { formatMoney } from "@/lib/format";
import { ProgressBar } from "./ProgressBar";

type LandingMotionProps = {
  stats: PlatformStats | null;
  featuredCampaign?: CampaignListItem | null;
};

export function LandingMotion({ stats, featuredCampaign }: LandingMotionProps) {
  const metrics = [
    { value: stats ? formatNumber(stats.campaigns_active) : "—", label: "активных историй" },
    { value: stats ? formatMoney(stats.total_donated_amount) : "—", label: "уже передано" },
    { value: stats ? formatNumber(stats.campaigns_completed) : "—", label: "историй закрыто" },
  ];

  return (
    <section className="overflow-hidden rounded-[24px] border border-stone-200 bg-[#fbfaf7] px-5 py-8 shadow-[0_22px_70px_rgba(28,25,23,0.08)] md:px-8 md:py-10 lg:px-10">
      <div className="grid items-center gap-8 lg:grid-cols-[0.92fr_1.08fr] lg:gap-12">
        <div className="max-w-3xl">
          <p className="text-xs font-semibold uppercase tracking-[0.18em] text-emerald-800">помощь, которую видно</p>
          <h1 className="mt-3 text-[36px] font-semibold leading-[1.04] text-stone-950 sm:text-5xl lg:text-[58px]">
            Выберите историю человека, которому нужна поддержка.
          </h1>
          <p className="mt-5 max-w-xl text-[16px] leading-7 text-stone-700 md:text-[17px]">
            На TipForTea видны цель, прогресс и итог. Помогайте тем, чья история вам близка.
          </p>

          <div className="mt-7 flex flex-col gap-3 sm:flex-row sm:items-center">
            <a href="#campaigns" className="rounded-full bg-stone-950 px-6 py-3 text-center font-semibold text-white shadow-[0_14px_30px_rgba(28,25,23,0.18)] transition hover:bg-emerald-800">
              Смотреть истории
            </a>
            <Link href="/campaigns/new" className="rounded-full border border-stone-300 bg-transparent px-6 py-3 text-center font-semibold text-stone-700 transition hover:border-stone-400 hover:bg-white">
              Открыть сбор
            </Link>
          </div>

          <div className="mt-8 grid max-w-xl grid-cols-1 gap-2 border-y border-stone-200 py-4 sm:grid-cols-3 sm:gap-4">
            {metrics.map((metric) => (
              <div key={metric.label}>
                <p className="text-xl font-semibold leading-none text-stone-950 md:text-2xl">{metric.value}</p>
                <p className="mt-1 text-xs leading-4 text-stone-500">{metric.label}</p>
              </div>
            ))}
          </div>
        </div>

        <div className="relative px-0 py-1">
          {featuredCampaign ? <FeaturedCampaignCard campaign={featuredCampaign} /> : <EmptyFeaturedCampaign />}
        </div>
      </div>
    </section>
  );
}

function FeaturedCampaignCard({ campaign }: { campaign: CampaignListItem }) {
  return (
    <Link
      href={`/campaigns/${campaign.id}`}
      className="group relative mx-auto block max-w-[520px] overflow-hidden rounded-[24px] border border-stone-200 bg-white shadow-[0_28px_80px_rgba(28,25,23,0.15)] transition hover:-translate-y-0.5 hover:shadow-[0_34px_90px_rgba(28,25,23,0.18)]"
    >
      <div className="relative overflow-hidden bg-stone-100">
        {campaign.cover_image_url ? (
          <img src={campaign.cover_image_url} alt="" className="aspect-[16/10] w-full object-cover transition duration-500 group-hover:scale-[1.025]" />
        ) : (
          <div className="aspect-[16/10] w-full bg-[#e9ded1]" />
        )}
        <span className="absolute left-4 top-4 rounded-full bg-white/92 px-3 py-1 text-xs font-semibold text-stone-800 shadow-sm">сейчас собирают</span>
      </div>

      <div className="p-5 md:p-6">
        <div className="flex items-start justify-between gap-4">
          <div>
            <p className="text-xs font-semibold uppercase tracking-[0.14em] text-emerald-700">история на главной</p>
            <h2 className="mt-2 text-2xl font-semibold leading-tight text-stone-950">{campaign.title}</h2>
          </div>
          <span className="shrink-0 rounded-full bg-emerald-50 px-3 py-1 text-xs font-semibold text-emerald-800">{campaign.progress_percentage}%</span>
        </div>

        <div className="mt-5">
          <div className="mb-2 flex items-end justify-between gap-4">
            <div>
              <p className="text-xs text-stone-400">собрано</p>
              <p className="text-2xl font-semibold text-stone-950">{formatMoney(campaign.current_amount)}</p>
            </div>
            <p className="text-right text-sm text-stone-500">цель {formatMoney(campaign.target_amount)}</p>
          </div>
          <ProgressBar value={campaign.progress_percentage} />
        </div>

        <div className="mt-5 flex items-center justify-between gap-4">
          <p className="text-sm text-stone-500">{formatNumber(campaign.contributors_count)} участников</p>
          <span className="text-sm font-semibold text-emerald-800 group-hover:text-emerald-950">Посмотреть историю →</span>
        </div>
      </div>
    </Link>
  );
}

function EmptyFeaturedCampaign() {
  return (
    <div className="relative mx-auto max-w-[520px] rounded-[24px] border border-stone-200 bg-white p-6 shadow-[0_28px_80px_rgba(28,25,23,0.15)]">
      <div className="rounded-[20px] bg-stone-100 p-8">
        <p className="text-xs font-semibold uppercase tracking-[0.14em] text-emerald-700">первые истории впереди</p>
        <h2 className="mt-3 text-2xl font-semibold leading-tight text-stone-950">Здесь будут только реальные сборы.</h2>
        <p className="mt-4 text-sm leading-6 text-stone-600">Без демонстрационных сумм и выдуманных историй.</p>
      </div>
    </div>
  );
}

function formatNumber(value: number) {
  return new Intl.NumberFormat("ru-RU").format(value);
}
