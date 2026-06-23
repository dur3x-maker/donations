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
    <section className="space-y-8">
      <div className="overflow-hidden rounded-[32px] bg-emerald-950 p-6 text-white shadow-[0_24px_80px_rgba(6,78,59,0.22)] md:p-10">
        <p className="text-sm font-semibold uppercase tracking-[0.18em] text-emerald-300">результаты поддержки</p>
        <h1 className="mt-3 max-w-3xl text-3xl font-semibold tracking-tight md:text-5xl">Истории, которые уже получили поддержку</h1>
        <p className="mt-4 max-w-2xl leading-7 text-emerald-100/80">
          Здесь собраны завершённые истории, итоговые отчёты и фотографии результатов.
        </p>
      </div>

      <div className="flex flex-col gap-4 rounded-[24px] border border-stone-200 bg-white p-4 shadow-sm md:flex-row md:items-center md:justify-between">
        <form action="/campaigns/completed" className="flex flex-1 gap-2">
          <input
            type="search"
            name="q"
            defaultValue={query}
            placeholder="Поиск по истории, автору или итоговому отчёту"
            className="min-w-0 flex-1 rounded-full border border-stone-200 px-4 py-3 outline-none transition focus:border-emerald-500 focus:ring-4 focus:ring-emerald-100"
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
        <div className="grid gap-5 md:grid-cols-2 xl:grid-cols-3">
          {campaigns.map((campaign) => <CompletedCampaignCard key={campaign.id} campaign={campaign} />)}
        </div>
      ) : (
        <div className="rounded-[24px] border border-stone-200 bg-white p-10 text-center shadow-sm">
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
