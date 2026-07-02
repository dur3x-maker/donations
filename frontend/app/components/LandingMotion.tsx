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
    { value: stats ? formatNumber(stats.users_count) : "—", label: "пользователей" },
    { value: stats ? formatMoney(stats.total_donated_amount) : "—", label: "собрано" },
    { value: stats ? formatNumber(stats.campaigns_completed) : "—", label: "завершённых историй" },
  ];

  return (
    <section className="overflow-hidden rounded-[28px] bg-[#f7f0e8] px-5 py-9 shadow-sm md:px-10 md:py-12 lg:px-12">
      <div className="grid items-center gap-8 lg:grid-cols-[1.02fr_0.98fr] lg:gap-10">
        <div>
          <p className="text-sm font-semibold uppercase tracking-[0.18em] text-emerald-700">тёплая поддержка</p>
          <h1 className="mt-4 max-w-3xl text-[38px] font-semibold leading-[1.04] text-stone-950 sm:text-6xl">
            Маленькие вклады двигают большие человеческие цели.
          </h1>
          <p className="mt-5 max-w-2xl text-[16px] leading-7 text-stone-700 md:text-[17px]">
            Выберите историю, поддержите сбор и помогите человеку стать ближе к цели. TipForTea делает помощь понятной, спокойной и заметной.
          </p>

          <div className="mt-7 flex flex-col gap-3 sm:flex-row">
            <a href="#campaigns" className="rounded-full bg-stone-950 px-6 py-3 text-center font-semibold text-white transition hover:bg-emerald-700">
              Смотреть сборы
            </a>
            <Link href="/campaigns/new" className="rounded-full border border-stone-300 bg-white/72 px-6 py-3 text-center font-semibold text-stone-800 transition hover:bg-white">
              Открыть сбор
            </Link>
          </div>

          <div className="mt-7 grid max-w-xl grid-cols-3 gap-3">
            {metrics.map((metric) => (
              <div key={metric.label} className="rounded-2xl border border-stone-200/80 bg-white/55 px-3 py-3">
                <p className="text-lg font-semibold leading-none text-stone-950 md:text-xl">{metric.value}</p>
                <p className="mt-1 text-xs leading-4 text-stone-500">{metric.label}</p>
              </div>
            ))}
          </div>
        </div>

        <div className="relative min-h-[360px] px-1 py-5 sm:min-h-[430px] lg:min-h-[500px]">
          <div className="absolute left-5 top-8 h-28 w-28 rounded-full bg-emerald-900/10 blur-3xl" />
          <div className="absolute bottom-10 right-2 h-36 w-36 rounded-full bg-rose-900/10 blur-3xl" />

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
      className="relative mx-auto block max-w-[430px] rotate-[-2deg] rounded-[30px] border border-white/70 bg-white p-4 shadow-[0_30px_90px_rgba(28,25,23,0.18)] transition hover:rotate-0 hover:shadow-[0_34px_100px_rgba(28,25,23,0.22)] sm:p-5"
    >
      <div className="overflow-hidden rounded-[24px] bg-stone-100">
        {campaign.cover_image_url ? (
          <img src={campaign.cover_image_url} alt="" className="aspect-[16/10] w-full object-cover" />
        ) : (
          <div className="aspect-[16/10] w-full bg-[linear-gradient(135deg,#e9ded1,#d9f99d)]" />
        )}
      </div>

      <div className="mt-5">
        <div className="flex items-start justify-between gap-4">
          <div>
            <p className="text-xs font-semibold uppercase tracking-[0.14em] text-emerald-700">живой сбор</p>
            <h2 className="mt-2 text-xl font-semibold leading-tight text-stone-950">{campaign.title}</h2>
          </div>
          <span className="shrink-0 rounded-full bg-stone-100 px-3 py-1 text-xs font-medium text-stone-600">{campaign.progress_percentage}%</span>
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
          <span className="text-sm font-semibold text-emerald-800">Открыть</span>
        </div>
      </div>
    </Link>
  );
}

function EmptyFeaturedCampaign() {
  return (
    <div className="relative mx-auto max-w-[430px] rotate-[-2deg] rounded-[30px] border border-white/70 bg-white p-6 shadow-[0_30px_90px_rgba(28,25,23,0.18)]">
      <div className="rounded-[24px] bg-stone-100 p-8">
        <p className="text-xs font-semibold uppercase tracking-[0.14em] text-emerald-700">первые истории впереди</p>
        <h2 className="mt-3 text-2xl font-semibold leading-tight text-stone-950">Когда появятся реальные сборы, мы покажем их здесь.</h2>
        <p className="mt-4 text-sm leading-6 text-stone-600">Платформа не подставляет демонстрационные суммы и показывает только данные из базы.</p>
      </div>
    </div>
  );
}

function formatNumber(value: number) {
  return new Intl.NumberFormat("ru-RU").format(value);
}
