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
    <div className="space-y-10">
      <section className="relative left-1/2 w-screen -translate-x-1/2 bg-stone-950 px-4 py-14 text-white md:px-8 md:py-16 lg:py-20">
        <div className="mx-auto grid max-w-[1180px] gap-10 lg:grid-cols-[1.15fr_0.85fr] lg:items-end">
          <div className="max-w-4xl">
            <p className="text-xs font-semibold uppercase tracking-[0.18em] text-emerald-300">почему можно доверять</p>
            <h2 className="mt-4 text-4xl font-semibold leading-[1.02] tracking-tight md:text-6xl lg:text-7xl">
              Доверие появляется, когда помощь можно проследить.
            </h2>
            <p className="mt-6 max-w-2xl text-base leading-7 text-stone-300 md:text-lg md:leading-8">
              TipForTea показывает путь истории: зачем нужен сбор, как движется сумма и чем все закончилось.
            </p>
          </div>

          <div className="space-y-5 border-l border-white/12 pl-5">
            {trustReasons.map((step) => (
              <div key={step.title}>
                <h3 className="text-lg font-semibold text-white">{step.title}</h3>
                <p className="mt-1 text-sm leading-6 text-stone-300">{step.text}</p>
              </div>
            ))}
          </div>
        </div>
      </section>

      <section aria-labelledby="how-it-works-title">
        <div className="grid gap-8 lg:grid-cols-[0.55fr_1.45fr] lg:items-start">
          <div className="max-w-xl">
            <p className="text-xs font-semibold uppercase tracking-[0.18em] text-emerald-700">как работает</p>
            <h2 id="how-it-works-title" className="mt-2 text-3xl font-semibold leading-tight text-stone-950 md:text-4xl">
              Три простых шага, без лишней механики
            </h2>
          </div>
          <div className="grid gap-0 divide-y divide-stone-200 border-y border-stone-200 md:grid-cols-3 md:divide-x md:divide-y-0">
          {workSteps.map((step, index) => (
            <article key={step.title} className="py-5 md:px-5 md:py-6">
              <span className="text-sm font-semibold text-emerald-800">0{index + 1}</span>
              <h3 className="mt-3 text-xl font-semibold text-stone-950">{step.title}</h3>
              <p className="mt-2 text-sm leading-6 text-stone-600">{step.text}</p>
            </article>
          ))}
          </div>
        </div>
      </section>
    </div>
  );
}
