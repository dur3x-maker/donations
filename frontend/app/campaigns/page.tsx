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
    <section className="space-y-8">
      <div className="rounded-[32px] bg-stone-950 p-6 text-white shadow-[0_24px_80px_rgba(28,25,23,0.20)] md:p-10">
        <p className="text-sm font-medium uppercase tracking-[0.18em] text-emerald-300">сборы</p>
        <h1 className="mt-3 text-3xl font-semibold tracking-tight md:text-5xl">Открытые сборы</h1>
        <p className="mt-4 max-w-2xl leading-7 text-stone-300">Выберите цель и посмотрите, как идет поддержка.</p>
      </div>

      <div className="flex flex-col gap-4 rounded-[24px] border border-stone-200 bg-white p-4 shadow-sm md:flex-row md:items-center md:justify-between">
        <form action="/campaigns" className="flex flex-1 gap-2">
          <input
            type="search"
            name="q"
            defaultValue={query}
            placeholder="Поиск по названию, описанию или автору"
            className="min-w-0 flex-1 rounded-full border border-stone-200 px-4 py-3 outline-none transition focus:border-emerald-500 focus:ring-4 focus:ring-emerald-100"
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
