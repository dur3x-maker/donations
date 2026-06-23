export function CampaignCardSkeleton() {
  return (
    <div className="overflow-hidden rounded-[26px] border border-stone-200/80 bg-white shadow-[0_18px_60px_rgba(28,25,23,0.06)]">
      <div className="aspect-[16/10] animate-pulse bg-stone-100" />
      <div className="space-y-4 p-5 md:p-6">
        <div className="flex gap-3">
          <div className="h-11 w-11 rounded-full bg-stone-100" />
          <div className="flex-1 space-y-2">
            <div className="h-5 w-3/4 rounded-full bg-stone-100" />
            <div className="h-4 w-full rounded-full bg-stone-100" />
            <div className="h-4 w-2/3 rounded-full bg-stone-100" />
          </div>
        </div>
        <div className="h-3 rounded-full bg-stone-100" />
      </div>
    </div>
  );
}

export function PageShellSkeleton() {
  return (
    <div className="space-y-8 pb-14">
      <section className="rounded-[34px] bg-white/76 p-6 shadow-[0_30px_120px_rgba(41,37,36,0.08)] md:p-10">
        <div className="grid gap-8 lg:grid-cols-2">
          <div className="space-y-5">
            <div className="h-9 w-48 animate-pulse rounded-full bg-stone-100" />
            <div className="space-y-3">
              <div className="h-12 w-full animate-pulse rounded-full bg-stone-100 md:h-16" />
              <div className="h-12 w-4/5 animate-pulse rounded-full bg-stone-100 md:h-16" />
            </div>
            <div className="h-5 w-2/3 animate-pulse rounded-full bg-stone-100" />
          </div>
          <div className="grid gap-3 sm:grid-cols-2">
            <div className="sm:col-span-2">
              <CampaignCardSkeleton />
            </div>
            <CampaignCardSkeleton />
            <CampaignCardSkeleton />
          </div>
        </div>
      </section>
    </div>
  );
}
