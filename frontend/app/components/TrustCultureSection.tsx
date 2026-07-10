const trustReasons = [
  {
    title: "Видна цель",
    text: "У каждого сбора есть сумма, прогресс и человек за историей.",
  },
  {
    title: "Есть след",
    text: "Завершенные сборы показывают итог, отчет и фотографии результата.",
  },
  {
    title: "Сначала помощь",
    text: "Перед своим сбором человек участвует в чужих историях.",
  },
];

const workSteps = [
  {
    title: "Выберите историю",
    text: "Откройте сбор, который кажется вам важным.",
  },
  {
    title: "Сделайте вклад",
    text: "Даже небольшая сумма двигает цель вперед.",
  },
  {
    title: "Следите за итогом",
    text: "После завершения автор публикует результат.",
  },
];

export function TrustCultureSection() {
  return (
    <div className="space-y-8">
      <section className="rounded-[22px] bg-stone-950 p-6 text-white shadow-[0_22px_70px_rgba(28,25,23,0.18)] md:p-8 lg:p-10">
        <div className="grid gap-8 lg:grid-cols-[0.85fr_1.15fr] lg:items-center">
          <div className="max-w-2xl">
            <p className="text-xs font-semibold uppercase tracking-[0.18em] text-emerald-300">почему можно доверять</p>
            <h2 className="mt-3 text-3xl font-semibold leading-[1.08] tracking-tight md:text-5xl">
              Не обещания. Следы реальной помощи.
            </h2>
            <p className="mt-5 max-w-xl text-base leading-7 text-stone-300">
              TipForTea показывает не витрину сервиса, а путь денег: от истории к прогрессу и результату.
            </p>
          </div>

          <div className="grid gap-3 sm:grid-cols-3 lg:gap-4">
            {trustReasons.map((step) => (
              <div key={step.title} className="rounded-[18px] border border-white/10 bg-white/[0.05] p-5">
                <h3 className="text-lg font-semibold text-white">{step.title}</h3>
                <p className="mt-3 text-sm leading-6 text-stone-300">{step.text}</p>
              </div>
            ))}
          </div>
        </div>
      </section>

      <section aria-labelledby="how-it-works-title">
        <div className="mb-5 max-w-2xl">
          <p className="text-xs font-semibold uppercase tracking-[0.18em] text-emerald-700">как работает</p>
          <h2 id="how-it-works-title" className="mt-2 text-3xl font-semibold leading-tight text-stone-950 md:text-4xl">
            Помощь без лишних шагов
          </h2>
        </div>

        <div className="grid gap-3 md:grid-cols-3">
          {workSteps.map((step, index) => (
            <article key={step.title} className="rounded-[18px] border border-stone-200 bg-white/75 p-5 shadow-sm">
              <span className="text-sm font-semibold text-emerald-800">0{index + 1}</span>
              <h3 className="mt-3 text-xl font-semibold text-stone-950">{step.title}</h3>
              <p className="mt-2 text-sm leading-6 text-stone-600">{step.text}</p>
            </article>
          ))}
        </div>
      </section>
    </div>
  );
}
