"use client";

import { useCallback, useEffect, useState } from "react";
import { CampaignCard } from "@/app/components/CampaignCard";
import { fetchCampaigns } from "@/lib/api";
import type { CampaignListItem, CampaignUpdatedEvent } from "@/lib/types";
import { useLiveRefresh } from "@/lib/use-live-refresh";
import { subscribeCatalogUpdates, type RealtimeStatus } from "@/lib/ws";

type CampaignSort = "newest" | "oldest" | "most_funded" | "least_funded";

export function CampaignsClient({
  initialCampaigns,
  page,
  sort,
  query,
}: {
  initialCampaigns: CampaignListItem[];
  page: number;
  sort: CampaignSort;
  query?: string;
}) {
  const [campaigns, setCampaigns] = useState(initialCampaigns);
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

  if (!campaigns.length) {
    return (
      <div className="rounded-[24px] border border-stone-200 bg-white p-8 text-center shadow-sm">
        <h2 className="text-xl font-semibold text-stone-950">Сборы не найдены</h2>
        <p className="mt-2 text-stone-600">Попробуйте изменить поисковый запрос.</p>
      </div>
    );
  }

  return (
    <div className="grid gap-5 md:grid-cols-2 xl:grid-cols-3">
      {campaigns.map((campaign) => <CampaignCard key={campaign.id} campaign={campaign} />)}
    </div>
  );
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
