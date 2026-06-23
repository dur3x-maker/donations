export default function CampaignLoading() {
  return (
    <div className="grid gap-6 lg:grid-cols-[minmax(0,1fr)_400px]">
      <div className="overflow-hidden rounded-[34px] border border-stone-200 bg-white shadow-[0_24px_90px_rgba(28,25,23,0.08)]">
        <div className="min-h-[420px] animate-pulse bg-stone-100 md:aspect-[16/8.8] md:min-h-0" />
        <div className="space-y-6 p-5 md:p-8">
          <div className="rounded-[28px] border border-stone-200 bg-stone-50 p-5">
            <div className="h-12 w-56 animate-pulse rounded-full bg-stone-100" />
            <div className="mt-5 h-4 animate-pulse rounded-full bg-stone-100" />
          </div>
          <div className="space-y-3">
            <div className="h-5 w-full animate-pulse rounded-full bg-stone-100" />
            <div className="h-5 w-5/6 animate-pulse rounded-full bg-stone-100" />
            <div className="h-5 w-2/3 animate-pulse rounded-full bg-stone-100" />
          </div>
        </div>
      </div>
      <div className="hidden h-96 rounded-[30px] border border-stone-200 bg-white shadow-[0_24px_90px_rgba(28,25,23,0.08)] lg:block" />
    </div>
  );
}
