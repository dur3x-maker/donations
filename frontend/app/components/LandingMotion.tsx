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
    <section className="relative overflow-hidden py-4 md:py-8">
      <div className="grid items-center gap-8 lg:grid-cols-[0.82fr_1.18fr] lg:gap-12">
        <div className="max-w-2xl">
          <p className="text-xs font-semibold uppercase tracking-[0.18em] text-emerald-800">помощь, которую видно</p>
          <h1 className="mt-3 text-[36px] font-semibold leading-[1.02] text-stone-950 sm:text-5xl lg:text-[62px]">
            Сначала человек. Потом сумма.
          </h1>
          <p className="mt-5 max-w-xl text-[16px] leading-7 text-stone-700 md:text-[17px]">
            TipForTea помогает выбрать реальную историю, увидеть цель и поддержать человека без лишнего шума.
          </p>

          <div className="mt-7 flex flex-col gap-3 sm:flex-row sm:items-center">
            <a href="#campaigns" className="rounded-full bg-stone-950 px-6 py-3 text-center font-semibold text-white shadow-[0_14px_30px_rgba(28,25,23,0.18)] transition hover:bg-emerald-800">
              Смотреть истории
            </a>
            <Link href="/campaigns/new" className="rounded-full border border-stone-300 bg-transparent px-6 py-3 text-center font-semibold text-stone-700 transition hover:border-stone-400 hover:bg-white">
              Открыть сбор
            </Link>
          </div>

          <div className="mt-9 grid max-w-xl grid-cols-1 gap-2 border-y border-stone-200 py-4 sm:grid-cols-3 sm:gap-4">
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
      className="group relative mx-auto block max-w-[680px] overflow-hidden rounded-[26px] bg-stone-950 text-white shadow-[0_34px_100px_rgba(28,25,23,0.24)] transition hover:-translate-y-0.5 hover:shadow-[0_40px_110px_rgba(28,25,23,0.28)]"
    >
      <div className="relative min-h-[360px] overflow-hidden bg-stone-900 md:min-h-[500px]">
        {campaign.cover_image_url ? (
          <img src={campaign.cover_image_url} alt="" className="absolute inset-0 h-full w-full object-cover transition duration-700 group-hover:scale-[1.025]" />
        ) : (
          <StoryPlaceholderVisual />
        )}
        <div className="absolute inset-0 bg-[linear-gradient(180deg,rgba(28,25,23,0.02)_0%,rgba(28,25,23,0.34)_45%,rgba(28,25,23,0.88)_100%)]" />
        <span className="absolute left-5 top-5 rounded-full bg-white/90 px-3 py-1 text-xs font-semibold text-stone-900 shadow-sm">сейчас собирают</span>

        <div className="absolute inset-x-0 bottom-0 p-5 md:p-7">
          <div className="max-w-xl">
            <p className="text-xs font-semibold uppercase tracking-[0.14em] text-emerald-200">история на главной</p>
            <h2 className="mt-2 text-3xl font-semibold leading-tight text-white md:text-4xl">{campaign.title}</h2>
          </div>

          <div className="mt-6 rounded-[18px] border border-white/12 bg-white/10 p-4 backdrop-blur">
            <div className="mb-3 flex items-end justify-between gap-4">
              <div>
                <p className="text-xs text-stone-300">собрано</p>
                <p className="text-2xl font-semibold text-white">{formatMoney(campaign.current_amount)}</p>
              </div>
              <p className="text-right text-sm text-stone-300">цель {formatMoney(campaign.target_amount)}</p>
            </div>
            <ProgressBar value={campaign.progress_percentage} />
          </div>

          <div className="mt-5 flex items-center justify-between gap-4">
            <p className="text-sm text-stone-300">{formatNumber(campaign.contributors_count)} участников</p>
            <span className="text-sm font-semibold text-emerald-200 group-hover:text-white">Посмотреть историю →</span>
          </div>
        </div>
      </div>
    </Link>
  );
}

function EmptyFeaturedCampaign() {
  return (
    <div className="relative mx-auto max-w-[680px] overflow-hidden rounded-[26px] bg-stone-950 text-white shadow-[0_34px_100px_rgba(28,25,23,0.24)]">
      <div className="relative min-h-[360px] md:min-h-[500px]">
        <StoryPlaceholderVisual />
        <div className="absolute inset-0 bg-[linear-gradient(180deg,rgba(28,25,23,0)_0%,rgba(28,25,23,0.24)_42%,rgba(28,25,23,0.88)_100%)]" />
        <div className="absolute inset-x-0 bottom-0 p-5 md:p-7">
          <p className="text-xs font-semibold uppercase tracking-[0.14em] text-emerald-200">первые истории впереди</p>
          <h2 className="mt-2 max-w-md text-3xl font-semibold leading-tight text-white md:text-4xl">Здесь будут только реальные сборы.</h2>
          <p className="mt-4 max-w-md text-sm leading-6 text-stone-300">Без демонстрационных сумм и выдуманных историй.</p>
        </div>
      </div>
    </div>
  );
}

function StoryPlaceholderVisual() {
  return (
    <div className="absolute inset-0 overflow-hidden bg-[linear-gradient(135deg,#292524_0%,#1c1917_42%,#064e3b_100%)]">
      <div className="absolute inset-x-6 top-6 h-28 rounded-[28px] border border-white/10 bg-[linear-gradient(90deg,rgba(255,255,255,0.12),rgba(255,255,255,0.02))] md:inset-x-8 md:top-8 md:h-36" />
      <div className="absolute left-6 top-40 h-px w-28 bg-emerald-200/40 md:left-8 md:top-52" />
      <div className="absolute bottom-0 left-0 right-0 h-56 bg-[linear-gradient(0deg,rgba(6,78,59,0.44),rgba(6,78,59,0))]" />
    </div>
  );
}

function formatNumber(value: number) {
  return new Intl.NumberFormat("ru-RU").format(value);
}
