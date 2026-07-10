type Partner = {
  name: string;
  mark: string;
  isVisible?: boolean;
};

const partners: Partner[] = [
  { name: "Care Foundation", mark: "CF" },
  { name: "Open Aid Lab", mark: "OA" },
  { name: "KindPay", mark: "KP" },
  { name: "North Clinic", mark: "NC" },
  { name: "EduBridge", mark: "EB" },
  { name: "Local Trust", mark: "LT" },
];

export function PartnersSection() {
  const visiblePartners = partners.filter((partner) => partner.isVisible !== false);

  return (
    <section className="rounded-[18px] border border-stone-200 bg-white/65 p-5 shadow-sm md:p-6">
      <div className="flex flex-col gap-5">
        <div className="max-w-xl">
          <p className="text-xs font-semibold uppercase tracking-[0.18em] text-stone-400">партнеры</p>
          <h2 className="mt-1 text-lg font-semibold text-stone-950">Организации рядом с платформой</h2>
        </div>

        <div className="grid grid-cols-2 gap-2 sm:grid-cols-3">
          {visiblePartners.map((partner) => (
            <div
              key={partner.name}
              className="flex h-14 min-w-0 items-center justify-center rounded-xl border border-stone-200 bg-stone-50 px-3 text-center grayscale"
              aria-label={partner.name}
              title={partner.name}
            >
              <span className="text-sm font-semibold tracking-[0.12em] text-stone-500">{partner.mark}</span>
            </div>
          ))}
        </div>
      </div>
    </section>
  );
}
