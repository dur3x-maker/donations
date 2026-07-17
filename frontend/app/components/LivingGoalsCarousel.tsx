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
  excludedCampaignId?: string;
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

export function LivingGoalsCarousel({ campaigns: initialCampaigns, excludedCampaignId }: LivingGoalsCarouselProps) {
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
    const requestedCount = Math.max(initialCampaigns.length + (excludedCampaignId ? 1 : 0), 7);
    const refreshedCampaigns = await fetchCampaigns({ page_size: requestedCount });
    setCampaigns(
      refreshedCampaigns
        .filter((campaign) => campaign.id !== excludedCampaignId)
        .slice(0, initialCampaigns.length || 7)
    );
  }, [excludedCampaignId, initialCampaigns.length]);

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
      <div className="border-y border-stone-200 py-6 text-stone-600">
        Первые сборы скоро появятся здесь.
      </div>
    );
  }

  return (
    <div
      ref={trackRef}
      className={`-mx-4 flex snap-x snap-mandatory gap-5 overflow-x-auto overscroll-x-contain px-4 pb-4 pt-1 touch-auto scrollbar-none [-webkit-overflow-scrolling:touch] md:-mx-6 md:px-6 lg:mx-0 lg:grid lg:auto-rows-[220px] lg:grid-cols-4 lg:overflow-visible lg:px-0 lg:pb-0 ${
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
      {campaigns.map((campaign, index) => (
        <LivingGoalCard key={campaign.id} campaign={campaign} variant={getStoryVariant(index)} />
      ))}

      <Link
        href="/campaigns"
        className="flex min-h-[410px] w-[82vw] max-w-[350px] shrink-0 snap-start flex-col justify-between rounded-[14px] bg-stone-950 p-6 text-white outline-none transition hover:bg-emerald-900 focus-visible:ring-4 focus-visible:ring-emerald-200 sm:w-[350px] lg:col-span-2 lg:min-h-0 lg:w-auto lg:max-w-none"
      >
        <div>
          <p className="text-xs font-semibold uppercase tracking-[0.16em] text-emerald-200">еще истории</p>
          <h3 className="mt-4 text-3xl font-semibold leading-tight">Открыть весь каталог</h3>
          <p className="mt-4 text-sm leading-6 text-stone-300">Больше людей, которым сейчас нужна помощь.</p>
        </div>
        <span className="text-base font-semibold">Смотреть →</span>
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

type StoryVariant = "large" | "tall" | "wide" | "compact";

function getStoryVariant(index: number): StoryVariant {
  if (index === 0) return "large";
  if (index === 1) return "tall";
  if (index === 4) return "wide";
  return "compact";
}

function LivingGoalCard({ campaign, variant }: { campaign: CampaignListItem; variant: StoryVariant }) {
  if (variant === "large") {
    return <MainStoryCard campaign={campaign} />;
  }

  const left = amountLeft(campaign.current_amount, campaign.target_amount);
  const variantClass = {
    large: "lg:col-span-2 lg:row-span-2",
    tall: "lg:row-span-2",
    wide: "lg:col-span-2",
    compact: "",
  }[variant];
  const imageClass = variant === "tall" ? "lg:aspect-auto lg:min-h-0 lg:flex-1" : "";
  const titleClass = variant === "tall" ? "lg:text-2xl" : "";

  return (
    <Link
      href={`/campaigns/${campaign.id}`}
      className={`group block w-[82vw] max-w-[380px] shrink-0 snap-start overflow-hidden rounded-[14px] border border-stone-200 bg-white outline-none transition hover:border-emerald-400 focus-visible:ring-4 focus-visible:ring-emerald-200 sm:w-[380px] lg:flex lg:h-full lg:w-auto lg:max-w-none lg:flex-col ${variantClass}`}
    >
      <div className={`relative aspect-[16/10] overflow-hidden bg-stone-100 ${imageClass}`}>
        {campaign.cover_image_url ? (
          <img src={campaign.cover_image_url} alt="" className="h-full w-full object-cover transition duration-500 group-hover:scale-[1.025]" draggable={false} />
        ) : (
          <div className="h-full w-full bg-stone-200" />
        )}
        <div className="absolute left-3 top-3 bg-white/95 px-3 py-1 text-xs font-medium text-stone-700">
          {categoryLabels[campaign.category] ?? campaign.category}
        </div>
      </div>

      <div className="p-5 lg:flex lg:min-h-0 lg:flex-col">
        <h3 className={`text-xl font-semibold leading-tight text-stone-950 ${titleClass}`}>{campaign.title}</h3>
        <p className="mt-3 line-clamp-2 text-sm leading-6 text-stone-600">{campaign.description_preview}</p>

        <div className="mt-6 lg:mt-auto">
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
            <span className="font-semibold text-stone-950 group-hover:text-emerald-800">История →</span>
          </div>
        </div>
      </div>
    </Link>
  );
}

function MainStoryCard({ campaign }: { campaign: CampaignListItem }) {
  const left = amountLeft(campaign.current_amount, campaign.target_amount);

  return (
    <Link
      href={`/campaigns/${campaign.id}`}
      className="group relative block min-h-[460px] w-[86vw] max-w-[420px] shrink-0 snap-start overflow-hidden rounded-[18px] bg-stone-950 text-white outline-none transition focus-visible:ring-4 focus-visible:ring-emerald-200 sm:w-[420px] lg:col-span-2 lg:row-span-2 lg:h-full lg:w-auto lg:max-w-none"
    >
      {campaign.cover_image_url ? (
        <img src={campaign.cover_image_url} alt="" className="absolute inset-0 h-full w-full object-cover transition duration-700 group-hover:scale-[1.025]" draggable={false} />
      ) : (
        <div className="absolute inset-0 bg-stone-800" />
      )}
      <div className="absolute inset-0 bg-[linear-gradient(180deg,rgba(28,25,23,0.05)_0%,rgba(28,25,23,0.36)_42%,rgba(28,25,23,0.92)_100%)]" />
      <div className="absolute left-4 top-4 bg-white/90 px-3 py-1 text-xs font-semibold text-stone-900">
        главная история
      </div>

      <div className="absolute inset-x-0 bottom-0 p-5 md:p-6">
        <p className="text-xs font-semibold uppercase tracking-[0.16em] text-emerald-200">
          {categoryLabels[campaign.category] ?? campaign.category}
        </p>
        <h3 className="mt-3 max-w-xl text-3xl font-semibold leading-tight text-white md:text-4xl">{campaign.title}</h3>
        <p className="mt-3 line-clamp-2 max-w-lg text-sm leading-6 text-stone-200">{campaign.description_preview}</p>

        <div className="mt-6 border-t border-white/20 pt-4">
          <div className="mb-3 flex items-end justify-between gap-4">
            <div>
              <p className="text-xs text-stone-300">собрано</p>
              <p className="text-2xl font-semibold text-white">{formatMoney(campaign.current_amount)}</p>
            </div>
            <p className="max-w-28 text-right text-sm leading-5 text-stone-300">осталось {formatMoney(left)}</p>
          </div>
          <ProgressBar value={campaign.progress_percentage} />
        </div>

        <div className="mt-5 flex items-center justify-between gap-3 text-sm">
          <span className="text-stone-300">{campaign.progress_percentage}% цели</span>
          <span className="font-semibold text-emerald-200 group-hover:text-white">Открыть историю →</span>
        </div>
      </div>
    </Link>
  );
}
