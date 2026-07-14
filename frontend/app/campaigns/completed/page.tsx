import Link from "next/link";
import { CompletedCampaignCard } from "@/app/components/CompletedCampaignCard";
import { fetchCompletedCampaigns } from "@/lib/api";

export const dynamic = "force-dynamic";

export default async function CompletedCampaignsPage({
  searchParams,
}: {
  searchParams: { page?: string; q?: string };
}) {
  const page = Number(searchParams.page || 1);
  const query = searchParams.q?.trim() || "";
  const campaigns = await fetchCompletedCampaigns({ page, q: query });

  return (
    <section className="pb-12 md:pb-20">
      <header className="max-w-4xl pb-4 md:pb-8">
        <p className="text-xs font-semibold uppercase tracking-[0.18em] text-emerald-700">результаты поддержки</p>
        <h1 className="mt-3 max-w-3xl text-4xl font-semibold tracking-[-0.035em] text-stone-950 md:text-6xl">Истории, где помощь уже дошла</h1>
        <p className="mt-4 max-w-2xl text-lg leading-8 text-stone-600">
          Здесь собраны завершённые истории, итоговые отчёты и фотографии результатов.
        </p>
      </header>

      <div className="editorial-plane editorial-plane-white mt-10 flex flex-col gap-4 py-6 md:mt-14 md:flex-row md:items-center md:justify-between md:py-8">
        <form action="/campaigns/completed" className="flex flex-1 gap-2">
          <input
            type="search"
            name="q"
            defaultValue={query}
            placeholder="Поиск по истории, автору или итоговому отчёту"
            className="min-w-0 flex-1 rounded-xl border border-stone-300 bg-white px-4 py-3 outline-none transition focus:border-emerald-500 focus:ring-4 focus:ring-emerald-100"
          />
          <button type="submit" className="rounded-full bg-emerald-800 px-5 py-3 font-semibold text-white transition hover:bg-emerald-900">
            Найти
          </button>
        </form>
        <Link href="/campaigns" className="text-center text-sm font-semibold text-stone-700 hover:text-stone-950">
          Открытые сборы →
        </Link>
      </div>

      {campaigns.length ? (
        <div className="mt-14 grid gap-5 md:mt-20 md:grid-cols-2 xl:grid-cols-3">
          {campaigns.map((campaign) => <CompletedCampaignCard key={campaign.id} campaign={campaign} />)}
        </div>
      ) : (
        <div className="editorial-plane editorial-plane-quiet mt-14 py-12 text-center md:mt-20 md:py-16">
          <h2 className="text-xl font-semibold text-stone-950">
            {query ? "По вашему запросу историй не найдено" : "Завершённые истории скоро появятся"}
          </h2>
          <p className="mt-2 text-stone-600">
            {query ? "Попробуйте другое название, имя автора или фразу из отчёта." : "После публикации итоговых отчётов они будут доступны здесь."}
          </p>
        </div>
      )}
    </section>
  );
}
