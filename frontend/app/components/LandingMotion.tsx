const heroMetrics = [
  { value: "12 840", label: "людей помогли" },
  { value: "1 126", label: "целей поддержано" },
  { value: "84", label: "сбора активны" },
];

const donorInitials = ["А", "М", "И", "К"];

export function LandingMotion() {
  return (
    <section className="overflow-hidden rounded-[28px] bg-[#f7f0e8] px-5 py-9 shadow-sm md:px-10 md:py-12 lg:px-12">
      <div className="grid items-center gap-8 lg:grid-cols-[1.02fr_0.98fr] lg:gap-10">
        <div>
          <p className="text-sm font-semibold uppercase tracking-[0.18em] text-emerald-700">теплая поддержка</p>
          <h1 className="mt-4 max-w-3xl text-[38px] font-semibold leading-[1.04] text-stone-950 sm:text-6xl">
            Маленькие вклады двигают большие человеческие цели.
          </h1>
          <p className="mt-5 max-w-2xl text-[16px] leading-7 text-stone-700 md:text-[17px]">
            Выберите историю, поддержите сбор и помогите человеку стать ближе к цели. TipForTea делает помощь понятной, спокойной и заметной.
          </p>

          <div className="mt-7 flex flex-col gap-3 sm:flex-row">
            <a href="#campaigns" className="rounded-full bg-stone-950 px-6 py-3 text-center font-semibold text-white transition hover:bg-emerald-700">
              Смотреть сборы
            </a>
            <a href="/campaigns/new" className="rounded-full border border-stone-300 bg-white/72 px-6 py-3 text-center font-semibold text-stone-800 transition hover:bg-white">
              Открыть сбор
            </a>
          </div>

          <div className="mt-7 grid max-w-xl grid-cols-3 gap-3">
            {heroMetrics.map((metric) => (
              <div key={metric.label} className="rounded-2xl border border-stone-200/80 bg-white/55 px-3 py-3">
                <p className="text-lg font-semibold leading-none text-stone-950 md:text-xl">{metric.value}</p>
                <p className="mt-1 text-xs leading-4 text-stone-500">{metric.label}</p>
              </div>
            ))}
          </div>
        </div>

        <div className="relative min-h-[360px] px-1 py-5 sm:min-h-[430px] lg:min-h-[500px]">
          <div className="absolute left-5 top-8 h-28 w-28 rounded-full bg-emerald-900/10 blur-3xl" />
          <div className="absolute bottom-10 right-2 h-36 w-36 rounded-full bg-rose-900/10 blur-3xl" />

          <div className="relative mx-auto max-w-[430px] rotate-[-2deg] rounded-[30px] border border-white/70 bg-white p-4 shadow-[0_30px_90px_rgba(28,25,23,0.18)] sm:p-5">
            <div className="overflow-hidden rounded-[24px] bg-stone-100">
              <img
                src="https://images.unsplash.com/photo-1497366754035-f200968a6e72?auto=format&fit=crop&w=900&q=80"
                alt=""
                className="aspect-[16/10] w-full object-cover"
              />
            </div>

            <div className="mt-5">
              <div className="flex items-start justify-between gap-4">
                <div>
                  <p className="text-xs font-semibold uppercase tracking-[0.14em] text-emerald-700">сбор недели</p>
                  <h2 className="mt-2 text-xl font-semibold leading-tight text-stone-950">Новый кабинет для занятий после операции</h2>
                </div>
                <span className="shrink-0 rounded-full bg-stone-100 px-3 py-1 text-xs font-medium text-stone-600">68%</span>
              </div>

              <div className="mt-5">
                <div className="mb-2 flex items-end justify-between gap-4">
                  <div>
                    <p className="text-xs text-stone-400">собрано</p>
                    <p className="text-2xl font-semibold text-stone-950">684 200 ₽</p>
                  </div>
                  <p className="text-right text-sm text-stone-500">цель 1 000 000 ₽</p>
                </div>
                <div className="h-2 overflow-hidden rounded-full bg-stone-100">
                  <div className="h-full w-[68%] rounded-full bg-emerald-600" />
                </div>
              </div>

              <div className="mt-5 flex items-center justify-between gap-4">
                <div className="flex -space-x-2">
                  {donorInitials.map((initial, index) => (
                    <span
                      key={initial}
                      className="flex h-9 w-9 items-center justify-center rounded-full border-2 border-white bg-stone-100 text-xs font-semibold text-stone-700"
                      style={{ zIndex: donorInitials.length - index }}
                    >
                      {initial}
                    </span>
                  ))}
                </div>
                <p className="text-sm text-stone-500">184 человека уже помогли</p>
              </div>
            </div>
          </div>

          <div className="absolute bottom-2 left-2 max-w-[260px] rotate-[1.5deg] rounded-2xl border border-stone-200 bg-white/95 p-4 shadow-[0_18px_55px_rgba(28,25,23,0.12)] sm:left-0">
            <p className="text-xs font-semibold uppercase tracking-[0.14em] text-stone-400">только что</p>
            <p className="mt-1 text-sm leading-5 text-stone-700">
              Анонимный вклад добавил <span className="font-semibold text-stone-950">2 000 ₽</span> и оставил теплое сообщение.
            </p>
          </div>
        </div>
      </div>
    </section>
  );
}
