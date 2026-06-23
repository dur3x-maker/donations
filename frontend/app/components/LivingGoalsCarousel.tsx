"use client";

import Link from "next/link";
import { useRouter } from "next/navigation";
import { PointerEvent, useCallback, useEffect, useRef, useState } from "react";
import { fetchCampaigns } from "@/lib/api";
import type { CampaignListItem, CampaignUpdatedEvent } from "@/lib/types";
import { amountLeft, formatMoney } from "@/lib/format";
import { useLiveRefresh } from "@/lib/use-live-refresh";
import { subscribeCatalogUpdates, type RealtimeStatus } from "@/lib/ws";
import { ProgressBar } from "./ProgressBar";

type LivingGoalsCarouselProps = {
  campaigns: CampaignListItem[];
};

const DRAG_THRESHOLD_PX = 12;

const categoryLabels: Record<string, string> = {
  medical: "лечение",
  education: "образование",
  emergency: "срочно",
  pets: "животные",
  community: "сообщество",
  personal: "личное",
  other: "другое",
};

export function LivingGoalsCarousel({ campaigns: initialCampaigns }: LivingGoalsCarouselProps) {
  const router = useRouter();
  const trackRef = useRef<HTMLDivElement | null>(null);
  const dragStartX = useRef(0);
  const scrollStartLeft = useRef(0);
  const activePointerId = useRef<number | null>(null);
  const suppressNextClick = useRef(false);
  const [isDragging, setIsDragging] = useState(false);
  const [campaigns, setCampaigns] = useState(initialCampaigns);
  const [wsStatus, setWsStatus] = useState<RealtimeStatus>("disconnected");

  const refresh = useCallback(async () => {
    setCampaigns(await fetchCampaigns({ page_size: initialCampaigns.length || 7 }));
  }, [initialCampaigns.length]);

  useLiveRefresh(refresh, wsStatus === "connected");

  useEffect(() => subscribeCatalogUpdates((event) => {
    if (event.type === "campaign_lifecycle_changed") {
      refresh().catch(() => undefined);
      router.refresh();
      return;
    }
    setCampaigns((current) => current.map((campaign) => patchCampaign(campaign, event)));
  }, setWsStatus), [refresh, router]);

  useEffect(() => {
    setCampaigns(initialCampaigns);
  }, [initialCampaigns]);

  function handlePointerDown(event: PointerEvent<HTMLDivElement>) {
    if (event.pointerType !== "mouse" || event.button !== 0) return;
    const track = trackRef.current;
    if (!track) return;

    activePointerId.current = event.pointerId;
    suppressNextClick.current = false;
    dragStartX.current = event.clientX;
    scrollStartLeft.current = track.scrollLeft;
  }

  function handlePointerMove(event: PointerEvent<HTMLDivElement>) {
    const track = trackRef.current;
    if (activePointerId.current !== event.pointerId || !track) return;

    const dragDistance = Math.abs(event.clientX - dragStartX.current);
    if (dragDistance < DRAG_THRESHOLD_PX) return;

    event.preventDefault();
    if (!isDragging) {
      setIsDragging(true);
      track.setPointerCapture(event.pointerId);
    }
    suppressNextClick.current = true;
    track.scrollLeft = scrollStartLeft.current - (event.clientX - dragStartX.current);
  }

  function stopDragging(event: PointerEvent<HTMLDivElement>) {
    const track = trackRef.current;
    if (activePointerId.current !== event.pointerId) return;
    activePointerId.current = null;
    setIsDragging(false);
    if (track?.hasPointerCapture(event.pointerId)) {
      track.releasePointerCapture(event.pointerId);
    }
  }

  if (!campaigns.length) {
    return (
      <div className="rounded-[24px] border border-stone-200 bg-white p-6 text-stone-600 shadow-sm">
        Первые сборы скоро появятся здесь.
      </div>
    );
  }

  return (
    <div
      ref={trackRef}
      className={`-mx-4 flex snap-x snap-mandatory gap-5 overflow-x-auto overscroll-x-contain px-4 pb-4 pt-1 touch-auto scrollbar-none [-webkit-overflow-scrolling:touch] md:-mx-6 md:px-6 ${
        isDragging ? "cursor-grabbing select-none scroll-auto" : "cursor-grab scroll-smooth"
      }`}
      onPointerDown={handlePointerDown}
      onPointerMove={handlePointerMove}
      onPointerUp={stopDragging}
      onPointerCancel={stopDragging}
      onPointerLeave={(event) => {
        if (!isDragging) stopDragging(event);
      }}
      onDragStart={(event) => event.preventDefault()}
      onClickCapture={(event) => {
        if (suppressNextClick.current && event.button === 0 && !event.metaKey && !event.ctrlKey && !event.shiftKey && !event.altKey) {
          event.preventDefault();
          event.stopPropagation();
          suppressNextClick.current = false;
        }
      }}
    >
      {campaigns.map((campaign) => (
        <LivingGoalCard key={campaign.id} campaign={campaign} />
      ))}

      <Link
        href="/campaigns"
        className="flex min-h-[430px] w-[82vw] max-w-[360px] shrink-0 snap-start flex-col justify-between rounded-[26px] border border-stone-200 bg-stone-950 p-6 text-white shadow-[0_18px_55px_rgba(28,25,23,0.14)] outline-none transition hover:bg-emerald-800 focus-visible:ring-4 focus-visible:ring-emerald-200 sm:w-[360px]"
      >
        <div>
          <p className="text-sm font-semibold uppercase tracking-[0.16em] text-emerald-200">еще истории</p>
          <h3 className="mt-4 text-3xl font-semibold leading-tight">Смотреть все сборы</h3>
          <p className="mt-4 text-sm leading-6 text-stone-300">Найдите цель, которая отзовется именно вам.</p>
        </div>
        <span className="text-lg font-semibold">Перейти →</span>
      </Link>
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

function LivingGoalCard({ campaign }: { campaign: CampaignListItem }) {
  const left = amountLeft(campaign.current_amount, campaign.target_amount);

  return (
    <Link
      href={`/campaigns/${campaign.id}`}
      className="group block w-[82vw] max-w-[380px] shrink-0 snap-start overflow-hidden rounded-[26px] border border-stone-200 bg-white shadow-[0_18px_55px_rgba(28,25,23,0.08)] outline-none transition hover:border-emerald-200 hover:shadow-[0_22px_65px_rgba(28,25,23,0.12)] focus-visible:ring-4 focus-visible:ring-emerald-200 sm:w-[380px]"
    >
      <div className="relative aspect-[16/11] overflow-hidden bg-stone-100">
        {campaign.cover_image_url ? (
          <img src={campaign.cover_image_url} alt="" className="h-full w-full object-cover transition duration-500 group-hover:scale-[1.025]" draggable={false} />
        ) : (
          <div className="h-full w-full bg-[#e9ded1]" />
        )}
        <div className="absolute left-4 top-4 rounded-full bg-white/92 px-3 py-1 text-xs font-medium text-stone-700 shadow-sm">
          {categoryLabels[campaign.category] ?? campaign.category}
        </div>
      </div>

      <div className="p-5">
        <h3 className="text-xl font-semibold leading-tight text-stone-950">{campaign.title}</h3>
        <p className="mt-3 line-clamp-3 text-sm leading-6 text-stone-600">{campaign.description_preview}</p>

        <div className="mt-6">
          <div className="mb-3 flex items-end justify-between gap-4">
            <div>
              <p className="text-xs text-stone-400">собрано</p>
              <p className="text-2xl font-semibold text-stone-950">{formatMoney(campaign.current_amount)}</p>
            </div>
            <p className="max-w-28 text-right text-sm leading-5 text-stone-500">осталось {formatMoney(left)}</p>
          </div>
          <ProgressBar value={campaign.progress_percentage} />
          <div className="mt-4 flex items-center justify-between gap-3 text-sm">
            <span className="text-stone-500">{campaign.progress_percentage}% цели</span>
            <span className="font-semibold text-stone-950 group-hover:text-emerald-800">Открыть</span>
          </div>
        </div>
      </div>
    </Link>
  );
}
