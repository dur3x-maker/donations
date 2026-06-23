import Link from "next/link";
import { fetchActivityFeed, fetchCampaigns, fetchCompletedCampaigns } from "@/lib/api";
import { ActivityFeed } from "./components/ActivityFeed";
import { CompletedCampaignCard } from "./components/CompletedCampaignCard";
import { LandingMotion } from "./components/LandingMotion";
import { LivingGoalsCarousel } from "./components/LivingGoalsCarousel";
import { PartnersSection } from "./components/PartnersSection";
import { TrustCultureSection } from "./components/TrustCultureSection";

export const dynamic = "force-dynamic";

export default async function HomePage() {
  const [campaigns, completedCampaigns, activities] = await Promise.all([
    fetchCampaigns({ page_size: 7 }).catch(() => []),
    fetchCompletedCampaigns({ page_size: 3 }).catch(() => []),
    fetchActivityFeed({ page_size: 5 }).catch(() => []),
  ]);
  const homepageCampaigns = campaigns.slice(0, 7);

  return (
    <div className="space-y-12 pb-14 md:space-y-14">
      <LandingMotion />

      <section id="campaigns" className="scroll-mt-24">
        <div className="mb-6 flex flex-col gap-3 md:flex-row md:items-end md:justify-between">
          <div className="max-w-2xl">
            <p className="text-sm font-semibold uppercase tracking-[0.18em] text-emerald-700">живые цели</p>
            <h2 className="mt-3 text-3xl font-semibold leading-tight text-stone-950 md:text-4xl">
              Выберите историю, которой хочется помочь
            </h2>
          </div>
          <p className="max-w-sm text-sm leading-6 text-stone-600">
            Небольшая подборка сборов, где прямо сейчас особенно важны внимание и участие.
          </p>
        </div>

        <LivingGoalsCarousel campaigns={homepageCampaigns} />
      </section>

      <TrustCultureSection />

      <section aria-labelledby="completed-stories-title">
        <div className="mb-6 flex flex-col gap-3 md:flex-row md:items-end md:justify-between">
          <div className="max-w-3xl">
            <p className="text-sm font-semibold uppercase tracking-[0.18em] text-emerald-700">поддержка работает</p>
            <h2 id="completed-stories-title" className="mt-3 text-3xl font-semibold leading-tight text-stone-950 md:text-4xl">
              Истории, которые уже получили поддержку
            </h2>
          </div>
          <Link href="/campaigns/completed" className="font-semibold text-emerald-800 transition hover:text-emerald-950">
            Все завершённые истории →
          </Link>
        </div>

        {completedCampaigns.length ? (
          <div className="grid gap-5 md:grid-cols-2 xl:grid-cols-3">
            {completedCampaigns.map((campaign) => <CompletedCampaignCard key={campaign.id} campaign={campaign} />)}
          </div>
        ) : (
          <Link
            href="/campaigns/completed"
            className="block rounded-[28px] border border-emerald-100 bg-emerald-950 p-6 text-white shadow-sm transition hover:bg-emerald-900 md:p-8"
          >
            <p className="max-w-2xl text-lg leading-8 text-emerald-50">
              Скоро здесь появятся первые итоговые отчёты и фотографии результатов.
            </p>
            <span className="mt-5 inline-block font-semibold text-emerald-200">Перейти в каталог →</span>
          </Link>
        )}
      </section>

      <ActivityFeed activities={activities.slice(0, 5)} />

      <PartnersSection />

      <section className="rounded-[28px] bg-stone-950 p-6 text-white md:p-8">
        <div className="flex flex-col gap-5 md:flex-row md:items-center md:justify-between">
          <div>
            <p className="text-sm font-semibold uppercase tracking-[0.18em] text-emerald-300">свой сбор</p>
            <h2 className="mt-2 text-2xl font-semibold md:text-3xl">Готовы рассказать свою историю?</h2>
          </div>
          <Link href="/campaigns/new" className="inline-flex rounded-full bg-white px-5 py-3 font-semibold text-stone-950 transition hover:bg-emerald-100">
            Открыть сбор
          </Link>
        </div>
      </section>
    </div>
  );
}
