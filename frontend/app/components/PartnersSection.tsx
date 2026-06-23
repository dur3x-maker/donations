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
    <section className="rounded-[28px] border border-stone-200 bg-white/70 p-6 shadow-sm md:p-8">
      <div className="flex flex-col gap-5 md:flex-row md:items-center md:justify-between">
        <div className="max-w-xl">
          <p className="text-sm font-semibold uppercase tracking-[0.18em] text-stone-400">нам доверяют</p>
          <h2 className="mt-2 text-2xl font-semibold text-stone-950 md:text-3xl">Партнеры платформы</h2>
          <p className="mt-3 text-sm leading-6 text-stone-600">
            Здесь будет аккуратная база фондов, сервисов и интеграций, которые помогают делать поддержку надежнее.
          </p>
        </div>

        <div className="grid grid-cols-2 gap-3 sm:grid-cols-3 lg:grid-cols-6">
          {visiblePartners.map((partner) => (
            <div
              key={partner.name}
              className="flex h-20 min-w-0 items-center justify-center rounded-2xl border border-stone-200 bg-stone-50 px-4 text-center grayscale"
              aria-label={partner.name}
              title={partner.name}
            >
              <span className="text-lg font-semibold tracking-[0.12em] text-stone-500">{partner.mark}</span>
            </div>
          ))}
        </div>
      </div>
    </section>
  );
}
