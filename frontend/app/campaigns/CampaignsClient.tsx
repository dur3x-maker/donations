"use client";

import Link from "next/link";
import { useCallback, useEffect, useState } from "react";
import { CampaignCard } from "@/app/components/CampaignCard";
import { fetchCampaigns } from "@/lib/api";
import type { CampaignCategory, CampaignListItem, CampaignUpdatedEvent } from "@/lib/types";
import { useLiveRefresh } from "@/lib/use-live-refresh";
import { subscribeCatalogUpdates, type RealtimeStatus } from "@/lib/ws";

type CampaignSort = "newest" | "oldest" | "most_funded" | "least_funded";
type CategoryFilter = CampaignCategory | "all";

const categoryOptions: Array<{ value: CategoryFilter; label: string }> = [
  { value: "all", label: "Все" },
  { value: "emergency", label: "❤️ Срочно" },
  { value: "medical", label: "🏥 Лечение" },
  { value: "pets", label: "🐶 Животные" },
  { value: "education", label: "🎓 Образование" },
  { value: "community", label: "🤝 Сообщество" },
  { value: "personal", label: "👤 Личное" },
  { value: "other", label: "✨ Другое" },
];

export function CampaignsClient({
  initialCampaigns,
  initialCategory,
  page,
  sort,
  query,
}: {
  initialCampaigns: CampaignListItem[];
  initialCategory?: string;
  page: number;
  sort: CampaignSort;
  query?: string;
}) {
  const [campaigns, setCampaigns] = useState(initialCampaigns);
  const [selectedCategory, setSelectedCategory] = useState<CategoryFilter>(() => normalizeCategory(initialCategory));
  const [status, setStatus] = useState<RealtimeStatus>("disconnected");

  const refresh = useCallback(async () => {
    setCampaigns(await fetchCampaigns({ page, sort, q: query }));
  }, [page, query, sort]);

  useLiveRefresh(refresh, status === "connected");

  useEffect(() => subscribeCatalogUpdates((event) => {
    if (event.type === "campaign_lifecycle_changed") {
      refresh().catch(() => undefined);
      return;
    }
    setCampaigns((current) => sortCampaigns(current.map((campaign) => patchCampaign(campaign, event)), sort));
  }, setStatus), [refresh, sort]);

  useEffect(() => {
    setCampaigns(initialCampaigns);
  }, [initialCampaigns]);

  useEffect(() => {
    setSelectedCategory(normalizeCategory(initialCategory));
  }, [initialCategory]);

  const visibleCampaigns = selectedCategory === "all"
    ? campaigns
    : campaigns.filter((campaign) => campaign.category === selectedCategory);

  function handleCategoryChange(category: CategoryFilter) {
    setSelectedCategory(category);

    const url = new URL(window.location.href);
    if (category === "all") url.searchParams.delete("category");
    else url.searchParams.set("category", category);
    url.searchParams.delete("page");
    window.history.replaceState(window.history.state, "", `${url.pathname}${url.search}${url.hash}`);
  }

  return (
    <>
      <div className="editorial-plane editorial-plane-white flex flex-col gap-4 py-6 md:flex-row md:items-center md:justify-between md:py-8">
        <form action="/campaigns" className="flex flex-1 gap-2">
          <input type="hidden" name="category" value={selectedCategory} disabled={selectedCategory === "all"} />
          <input type="hidden" name="sort" value={sort} disabled={sort === "newest"} />
          <input
            key={query}
            type="search"
            name="q"
            defaultValue={query}
            placeholder="Поиск по названию, описанию или автору"
            className="min-w-0 flex-1 rounded-xl border border-stone-300 bg-white px-4 py-3 outline-none transition focus:border-emerald-600 focus:ring-4 focus:ring-emerald-100"
          />
          <button type="submit" className="shrink-0 rounded-full bg-stone-950 px-5 py-3 font-semibold text-white transition hover:bg-emerald-800">
            Найти
          </button>
        </form>
        <Link href="/campaigns/completed" className="text-center text-sm font-semibold text-emerald-800 hover:text-emerald-950">
          Смотреть завершённые истории →
        </Link>
      </div>

      <div
        aria-label="Категории историй"
        className="mt-4 touch-pan-x overflow-x-auto overscroll-x-contain pb-2 [-ms-overflow-style:none] [scrollbar-width:none] [&::-webkit-scrollbar]:hidden"
        role="group"
      >
        <div className="flex w-max min-w-full gap-2">
          {categoryOptions.map((category) => {
            const isActive = selectedCategory === category.value;
            return (
              <button
                key={category.value}
                aria-pressed={isActive}
                className={`min-h-11 shrink-0 whitespace-nowrap rounded-full border px-4 py-2.5 text-sm font-semibold transition focus-visible:outline-none focus-visible:ring-4 focus-visible:ring-emerald-200 ${isActive ? "border-stone-950 bg-stone-950 text-white" : "border-stone-200 bg-white text-stone-700 hover:border-emerald-400 hover:text-emerald-800"}`}
                onClick={() => handleCategoryChange(category.value)}
                type="button"
              >
                {category.label}
              </button>
            );
          })}
        </div>
      </div>

      <div className="mt-10 md:mt-14">
        {visibleCampaigns.length ? (
          <div className="grid gap-5 md:grid-cols-2 xl:grid-cols-3">
            {visibleCampaigns.map((campaign) => <CampaignCard key={campaign.id} campaign={campaign} />)}
          </div>
        ) : (
          <div className="rounded-[24px] border border-stone-200 bg-white p-8 text-center shadow-sm">
            <h2 className="text-xl font-semibold text-stone-950">Истории не найдены</h2>
            <p className="mt-2 text-stone-600">Попробуйте выбрать другую категорию или изменить поисковый запрос.</p>
          </div>
        )}
      </div>
    </>
  );
}

function normalizeCategory(value?: string): CategoryFilter {
  return categoryOptions.some((category) => category.value === value) ? value as CategoryFilter : "all";
}

function patchCampaign(campaign: CampaignListItem, event: CampaignUpdatedEvent) {
  if (campaign.id !== event.campaign_id) return campaign;
  return {
    ...campaign,
    current_amount: event.current_amount,
    target_amount: event.goal_amount,
    progress_percentage: event.progress_percentage,
    contributors_count: event.contributors_count,
  };
}

function sortCampaigns(campaigns: CampaignListItem[], sort: CampaignSort) {
  if (sort !== "most_funded" && sort !== "least_funded") return campaigns;
  const direction = sort === "most_funded" ? -1 : 1;
  return [...campaigns].sort((left, right) => direction * (Number(left.current_amount) - Number(right.current_amount)));
}
