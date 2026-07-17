import { CampaignsClient } from "@/app/campaigns/CampaignsClient";
import { fetchCampaigns } from "@/lib/api";

export const dynamic = "force-dynamic";

export default async function CampaignsPage({
  searchParams,
}: {
  searchParams: { page?: string; sort?: "newest" | "oldest" | "most_funded" | "least_funded"; q?: string; category?: string };
}) {
  const page = Number(searchParams.page || 1);
  const sort = searchParams.sort || "newest";
  const query = searchParams.q?.trim() || "";
  const campaigns = await fetchCampaigns({ page, sort, q: query });

  return (
    <section className="pb-12 md:pb-20">
      <header className="max-w-3xl pb-4 md:pb-8">
        <p className="text-xs font-semibold uppercase tracking-[0.18em] text-emerald-700">открытые истории</p>
        <h1 className="mt-3 text-4xl font-semibold tracking-[-0.035em] text-stone-950 md:text-6xl">Кому сейчас нужна помощь</h1>
        <p className="mt-4 max-w-2xl text-lg leading-8 text-stone-600">Выберите историю, узнайте человека и посмотрите, как движется его цель.</p>
      </header>

      <div className="mt-10 md:mt-14">
        <CampaignsClient initialCampaigns={campaigns} initialCategory={searchParams.category} page={page} sort={sort} query={query} />
      </div>
    </section>
  );
}
