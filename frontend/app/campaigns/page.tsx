import Link from "next/link";
import { CampaignsClient } from "@/app/campaigns/CampaignsClient";
import { fetchCampaigns } from "@/lib/api";

export const dynamic = "force-dynamic";

export default async function CampaignsPage({
  searchParams,
}: {
  searchParams: { page?: string; sort?: "newest" | "oldest" | "most_funded" | "least_funded"; q?: string };
}) {
  const page = Number(searchParams.page || 1);
  const sort = searchParams.sort || "newest";
  const query = searchParams.q?.trim() || "";
  const campaigns = await fetchCampaigns({ page, sort, q: query });

  return (
    <section className="space-y-10 pb-10">
      <header className="max-w-3xl border-b border-stone-200 pb-8">
        <p className="text-xs font-semibold uppercase tracking-[0.18em] text-emerald-700">открытые истории</p>
        <h1 className="mt-3 text-4xl font-semibold tracking-[-0.035em] text-stone-950 md:text-6xl">Кому сейчас нужна помощь</h1>
        <p className="mt-4 max-w-2xl text-lg leading-8 text-stone-600">Выберите историю, узнайте человека и посмотрите, как движется его цель.</p>
      </header>

      <div className="flex flex-col gap-4 md:flex-row md:items-center md:justify-between">
        <form action="/campaigns" className="flex flex-1 gap-2">
          <input
            type="search"
            name="q"
            defaultValue={query}
            placeholder="Поиск по названию, описанию или автору"
            className="min-w-0 flex-1 rounded-xl border border-stone-300 bg-white px-4 py-3 outline-none transition focus:border-emerald-600 focus:ring-4 focus:ring-emerald-100"
          />
          <button type="submit" className="rounded-full bg-stone-950 px-5 py-3 font-semibold text-white transition hover:bg-emerald-800">
            Найти
          </button>
        </form>
        <Link href="/campaigns/completed" className="text-center text-sm font-semibold text-emerald-800 hover:text-emerald-950">
          Смотреть завершённые истории →
        </Link>
      </div>

      <CampaignsClient initialCampaigns={campaigns} page={page} sort={sort} query={query} />
    </section>
  );
}
