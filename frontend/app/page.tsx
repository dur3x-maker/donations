import Link from "next/link";
import { fetchActivityFeed, fetchCampaigns, fetchCompletedCampaigns, fetchPlatformStats } from "@/lib/api";
import { ActivityFeed } from "./components/ActivityFeed";
import { CompletedCampaignCard } from "./components/CompletedCampaignCard";
import { LandingMotion } from "./components/LandingMotion";
import { LivingGoalsCarousel } from "./components/LivingGoalsCarousel";
import { PartnersSection } from "./components/PartnersSection";
import { TrustCultureSection } from "./components/TrustCultureSection";

export const dynamic = "force-dynamic";

const homepageFaq = [
  {
    question: "Кому я помогаю?",
    answer: "Конкретному человеку или инициативе из выбранной истории. На карточке видны цель, сумма и прогресс.",
  },
  {
    question: "Почему здесь можно доверять?",
    answer: "Платформа показывает реальные сборы, движение суммы и завершенные истории с итогом.",
  },
  {
    question: "Можно ли открыть свой сбор сразу?",
    answer: "Сначала нужно поддержать другие истории. Это правило помогает сохранять доверие внутри платформы.",
  },
];

export default async function HomePage() {
  const [campaigns, completedCampaigns, activities, stats] = await Promise.all([
    fetchCampaigns({ page_size: 7 }).catch(() => []),
    fetchCompletedCampaigns({ page_size: 3 }).catch(() => []),
    fetchActivityFeed({ page_size: 5 }).catch(() => []),
    fetchPlatformStats().catch(() => null),
  ]);
  const homepageCampaigns = campaigns.slice(0, 7);

  return (
    <div className="space-y-12 pb-14 md:space-y-16">
      <LandingMotion stats={stats} featuredCampaign={homepageCampaigns[0] ?? null} />

      <section id="campaigns" className="scroll-mt-24">
        <div className="mb-6 flex flex-col gap-3 md:flex-row md:items-end md:justify-between">
          <div className="max-w-2xl">
            <p className="text-xs font-semibold uppercase tracking-[0.18em] text-emerald-700">активные истории</p>
            <h2 className="mt-3 text-3xl font-semibold leading-tight text-stone-950 md:text-4xl">
              Люди, которым сейчас нужна помощь
            </h2>
          </div>
          <Link href="/campaigns" className="font-semibold text-emerald-800 transition hover:text-emerald-950">
            Все истории →
          </Link>
        </div>

        <LivingGoalsCarousel campaigns={homepageCampaigns} />
      </section>

      <TrustCultureSection />

      <div className="grid gap-5 lg:grid-cols-[0.9fr_1.1fr]">
        <ActivityFeed activities={activities.slice(0, 5)} />
        <PartnersSection />
      </div>

      <section aria-labelledby="completed-stories-title">
        <div className="mb-6 flex flex-col gap-3 md:flex-row md:items-end md:justify-between">
          <div className="max-w-3xl">
            <p className="text-xs font-semibold uppercase tracking-[0.18em] text-emerald-700">результат</p>
            <h2 id="completed-stories-title" className="mt-3 text-3xl font-semibold leading-tight text-stone-950 md:text-4xl">
              Истории, где помощь уже дошла
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
            className="block rounded-[20px] border border-emerald-100 bg-emerald-950 p-6 text-white shadow-sm transition hover:bg-emerald-900 md:p-8"
          >
            <p className="max-w-2xl text-lg leading-8 text-emerald-50">
              Скоро здесь появятся первые итоговые отчёты и фотографии результатов.
            </p>
            <span className="mt-5 inline-block font-semibold text-emerald-200">Перейти в каталог →</span>
          </Link>
        )}
      </section>

      <section aria-labelledby="homepage-faq-title">
        <div className="mb-5 max-w-2xl">
          <p className="text-xs font-semibold uppercase tracking-[0.18em] text-emerald-700">FAQ</p>
          <h2 id="homepage-faq-title" className="mt-2 text-3xl font-semibold leading-tight text-stone-950 md:text-4xl">
            Коротко о главном
          </h2>
        </div>
        <div className="grid gap-3 md:grid-cols-3">
          {homepageFaq.map((item) => (
            <article key={item.question} className="rounded-[18px] border border-stone-200 bg-white/75 p-5 shadow-sm">
              <h3 className="text-lg font-semibold leading-snug text-stone-950">{item.question}</h3>
              <p className="mt-3 text-sm leading-6 text-stone-600">{item.answer}</p>
            </article>
          ))}
        </div>
      </section>

      <section className="rounded-[22px] bg-stone-950 p-6 text-white shadow-[0_22px_70px_rgba(28,25,23,0.18)] md:p-8">
        <div className="flex flex-col gap-5 md:flex-row md:items-center md:justify-between">
          <div>
            <p className="text-xs font-semibold uppercase tracking-[0.18em] text-emerald-300">начните с истории</p>
            <h2 className="mt-2 text-2xl font-semibold md:text-3xl">Посмотрите, кому можно помочь сегодня.</h2>
          </div>
          <div className="flex flex-col gap-3 sm:flex-row">
            <a href="#campaigns" className="inline-flex justify-center rounded-full bg-white px-5 py-3 font-semibold text-stone-950 transition hover:bg-emerald-100">
              Смотреть истории
            </a>
            <Link href="/campaigns/new" className="inline-flex justify-center rounded-full border border-white/20 px-5 py-3 font-semibold text-white transition hover:bg-white/10">
              Открыть сбор
            </Link>
          </div>
        </div>
      </section>
    </div>
  );
}
