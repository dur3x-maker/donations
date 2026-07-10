const trustNotes = [
  "Реальные сборы вместо демонстрационных историй",
  "Видимый прогресс по каждой цели",
  "Итоги и отчеты после завершения",
];

export function PartnersSection() {
  return (
    <section className="rounded-[22px] border border-stone-200 bg-[#fbfaf7] p-5 shadow-sm md:p-6">
      <div className="grid gap-5 md:grid-cols-[0.8fr_1.2fr] md:items-start">
        <div>
          <p className="text-xs font-semibold uppercase tracking-[0.18em] text-stone-400">без декораций</p>
          <h2 className="mt-2 text-2xl font-semibold leading-tight text-stone-950">Доверие держится на видимых следах</h2>
        </div>

        <div className="divide-y divide-stone-200 border-y border-stone-200">
          {trustNotes.map((note) => (
            <p key={note} className="py-3 text-sm leading-6 text-stone-600">
              {note}
            </p>
          ))}
        </div>
      </div>
    </section>
  );
}
