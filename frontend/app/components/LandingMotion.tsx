import Link from "next/link";
import type { CampaignListItem, PlatformStats } from "@/lib/types";
import { formatMoney } from "@/lib/format";
import { ProgressBar } from "./ProgressBar";

type LandingMotionProps = {
  stats: PlatformStats | null;
  featuredCampaign?: CampaignListItem | null;
};

export function LandingMotion({ stats, featuredCampaign }: LandingMotionProps) {
  return (
    <section className="py-3 md:py-6">
      <div className="grid items-center gap-10 lg:grid-cols-[0.9fr_1.1fr] lg:gap-16">
        <div className="max-w-2xl">
          <p className="text-xs font-semibold uppercase tracking-[0.18em] text-emerald-800">помощь, которую видно</p>
          <h1 className="mt-3 text-[38px] font-semibold leading-[1.02] tracking-[-0.035em] text-stone-950 sm:text-5xl lg:text-[62px]">
            Сначала человек. Потом сумма.
          </h1>
          <p className="mt-5 max-w-xl text-[16px] leading-7 text-stone-700 md:text-[17px]">
            TipForTea помогает выбрать реальную историю, увидеть цель и поддержать человека без лишнего шума.
          </p>

          <div className="mt-7 flex flex-col gap-3 sm:flex-row sm:items-center">
            <a href="#campaigns" className="rounded-full bg-stone-950 px-6 py-3 text-center font-semibold text-white transition hover:bg-emerald-800">
              Смотреть истории
            </a>
            <Link href="/campaigns/new" className="rounded-full border border-stone-300 bg-transparent px-6 py-3 text-center font-semibold text-stone-700 transition hover:border-stone-400 hover:bg-white">
              Открыть сбор
            </Link>
          </div>

          {stats ? (
            <p className="mt-8 max-w-xl border-t border-stone-200 pt-4 text-sm leading-6 text-stone-500">
              Сейчас открыто {formatNumber(stats.campaigns_active)} историй; {formatNumber(stats.campaigns_completed)} уже завершены с итогом.
            </p>
          ) : null}
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
      className="group relative mx-auto block max-w-[680px] overflow-hidden rounded-[18px] bg-stone-950 text-white transition hover:bg-stone-900"
    >
      <div className="relative min-h-[360px] overflow-hidden bg-stone-900 md:min-h-[500px]">
        {campaign.cover_image_url ? (
          <img src={campaign.cover_image_url} alt="" className="absolute inset-0 h-full w-full object-cover transition duration-700 group-hover:scale-[1.025]" />
        ) : (
          <div className="absolute inset-0 flex items-center justify-center bg-stone-800 text-sm text-stone-400">Обложка истории пока не добавлена</div>
        )}
        <div className="absolute inset-0 bg-[linear-gradient(180deg,rgba(28,25,23,0.02)_0%,rgba(28,25,23,0.34)_45%,rgba(28,25,23,0.88)_100%)]" />
        <span className="absolute left-5 top-5 bg-white/90 px-3 py-1 text-xs font-semibold text-stone-900">сейчас собирают</span>

        <div className="absolute inset-x-0 bottom-0 p-5 md:p-7">
          <div className="max-w-xl">
            <p className="text-xs font-semibold uppercase tracking-[0.14em] text-emerald-200">история на главной</p>
            <h2 className="mt-2 text-3xl font-semibold leading-tight text-white md:text-4xl">{campaign.title}</h2>
          </div>

          <div className="mt-6 border-t border-white/20 pt-4">
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
    <div className="mx-auto max-w-[680px] border-y border-stone-300 py-8 lg:py-14">
      <p className="text-xs font-semibold uppercase tracking-[0.14em] text-emerald-800">первые истории впереди</p>
      <h2 className="mt-3 max-w-md text-3xl font-semibold leading-tight text-stone-950 md:text-4xl">Здесь будут только реальные сборы.</h2>
      <p className="mt-4 max-w-md text-sm leading-6 text-stone-600">Без демонстрационных сумм и выдуманных историй.</p>
      <Link href="/campaigns" className="mt-6 inline-flex font-semibold text-emerald-800 hover:text-emerald-950">Перейти в каталог →</Link>
    </div>
  );
}

function formatNumber(value: number) {
  return new Intl.NumberFormat("ru-RU").format(value);
}
