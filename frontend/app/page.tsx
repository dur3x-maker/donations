import Link from "next/link";
import { fetchActivityFeed, fetchCampaigns, fetchCompletedCampaigns, fetchPlatformStats } from "@/lib/api";
import { ActivityFeed } from "./components/ActivityFeed";
import { CompletedCampaignCard } from "./components/CompletedCampaignCard";
import { LandingMotion } from "./components/LandingMotion";
import { LivingGoalsCarousel } from "./components/LivingGoalsCarousel";
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
    <div className="space-y-16 pb-10 md:space-y-24">
      <LandingMotion stats={stats} featuredCampaign={homepageCampaigns[0] ?? null} />

      <section id="campaigns" className="scroll-mt-24">
        <div className="mb-7 flex flex-col gap-4 md:flex-row md:items-end md:justify-between">
          <div className="max-w-3xl">
            <p className="text-xs font-semibold uppercase tracking-[0.18em] text-emerald-700">активные истории</p>
            <h2 className="mt-3 text-4xl font-semibold leading-tight text-stone-950 md:text-5xl">
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

      <section className="relative left-1/2 w-screen -translate-x-1/2 border-y border-stone-200 bg-white px-4 py-10 md:px-8 md:py-12">
        <div className="mx-auto max-w-[1180px]">
          <ActivityFeed activities={activities.slice(0, 5)} />
        </div>
      </section>

      <section aria-labelledby="completed-stories-title" className="border-y border-stone-200 py-8 md:py-10">
        <div className="mb-7 grid gap-4 md:grid-cols-[0.72fr_0.28fr] md:items-end">
          <div className="max-w-3xl">
            <p className="text-xs font-semibold uppercase tracking-[0.18em] text-emerald-700">результат</p>
            <h2 id="completed-stories-title" className="mt-3 text-4xl font-semibold leading-tight text-stone-950 md:text-5xl">
              Истории, где помощь уже дошла
            </h2>
          </div>
          <Link href="/campaigns/completed" className="font-semibold text-emerald-800 transition hover:text-emerald-950 md:text-right">
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
            className="grid gap-6 border-t border-stone-200 py-6 transition hover:text-emerald-900 md:grid-cols-[1fr_auto] md:items-end"
          >
            <div>
              <p className="text-xs font-semibold uppercase tracking-[0.18em] text-emerald-700">итоги впереди</p>
              <p className="mt-3 max-w-2xl text-xl font-semibold leading-8 text-stone-950">
                Скоро здесь появятся первые отчеты: фотографии, благодарности и закрытые цели.
              </p>
            </div>
            <span className="font-semibold text-emerald-800">Перейти в каталог →</span>
          </Link>
        )}
      </section>

      <section aria-labelledby="homepage-faq-title">
        <div className="grid gap-8 lg:grid-cols-[0.48fr_0.52fr] lg:items-start">
          <div className="max-w-xl">
            <p className="text-xs font-semibold uppercase tracking-[0.18em] text-emerald-700">FAQ</p>
            <h2 id="homepage-faq-title" className="mt-2 text-3xl font-semibold leading-tight text-stone-950 md:text-4xl">
              Коротко о главном
            </h2>
          </div>
          <div className="divide-y divide-stone-200 border-y border-stone-200">
            {homepageFaq.map((item) => (
              <article key={item.question} className="py-5">
                <h3 className="text-lg font-semibold leading-snug text-stone-950">{item.question}</h3>
                <p className="mt-2 text-sm leading-6 text-stone-600">{item.answer}</p>
              </article>
            ))}
          </div>
        </div>
      </section>

    </div>
  );
}
