const trustSteps = [
  {
    title: "Поддержите",
    text: "Выберите историю и сделайте вклад, который вам по силам.",
  },
  {
    title: "Сохраните участие",
    text: "Подтверждённая помощь засчитывается в вашем профиле.",
  },
  {
    title: "Откройте цель",
    text: "После участия в других сборах можно рассказать свою историю.",
  },
];

export function TrustCultureSection() {
  return (
    <section className="rounded-[32px] bg-stone-950 p-6 text-white shadow-[0_24px_80px_rgba(28,25,23,0.20)] md:p-8 lg:p-10">
      <div className="grid gap-8 lg:grid-cols-[0.95fr_1.05fr] lg:items-center">
        <div className="max-w-2xl">
          <p className="text-sm font-semibold uppercase tracking-[0.18em] text-emerald-300">культура доверия</p>
          <h2 className="mt-4 text-4xl font-semibold leading-[1.05] tracking-tight md:text-5xl">
            Сначала участвуете.
            <br />
            Потом открываете своё.
          </h2>
          <p className="mt-5 max-w-xl text-base leading-7 text-stone-300">
            TipForTea устроен так, чтобы площадка начиналась с помощи. Здесь люди не только просят поддержки, но и сначала становятся частью общего круга участия.
          </p>
        </div>

        <div className="grid gap-3 sm:grid-cols-3 lg:gap-4">
          {trustSteps.map((step) => (
            <div key={step.title} className="rounded-[24px] border border-white/10 bg-white/[0.04] p-5">
              <h3 className="text-xl font-semibold text-white">{step.title}</h3>
              <p className="mt-3 text-sm leading-6 text-stone-300">{step.text}</p>
            </div>
          ))}
        </div>
      </div>
    </section>
  );
}
