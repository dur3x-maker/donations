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
    <div className="space-y-14 pb-14 md:space-y-20">
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

      <section className="relative left-1/2 w-screen -translate-x-1/2 bg-stone-100/70 px-4 py-10 md:px-6 md:py-12">
        <div className="mx-auto grid max-w-7xl gap-5 lg:grid-cols-[0.78fr_1.22fr]">
          <ActivityFeed activities={activities.slice(0, 5)} />
          <PartnersSection />
        </div>
      </section>

      <section aria-labelledby="completed-stories-title" className="rounded-[26px] bg-[#f7f0e8] p-5 shadow-[0_18px_55px_rgba(28,25,23,0.08)] md:p-8 lg:p-10">
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
            className="grid gap-6 rounded-[22px] bg-white p-6 shadow-sm transition hover:bg-stone-50 md:grid-cols-[1fr_auto] md:items-end md:p-8"
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

      <section className="relative left-1/2 w-screen -translate-x-1/2 bg-stone-950 px-4 py-12 text-white md:px-6 md:py-16">
        <div className="mx-auto flex max-w-7xl flex-col gap-6 md:flex-row md:items-center md:justify-between">
          <div>
            <p className="text-xs font-semibold uppercase tracking-[0.18em] text-emerald-300">начните с истории</p>
            <h2 className="mt-2 max-w-2xl text-3xl font-semibold text-white md:text-5xl">Откройте каталог и выберите человека, которому поможете.</h2>
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
