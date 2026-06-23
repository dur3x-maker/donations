"use client";

export default function Error({ reset }: { reset: () => void }) {
  return (
    <section className="mx-auto max-w-2xl rounded-[32px] border border-stone-200 bg-white p-6 text-center shadow-[0_24px_90px_rgba(28,25,23,0.10)] md:p-10">
      <p className="text-sm font-semibold uppercase tracking-[0.18em] text-emerald-700">связь прервалась</p>
      <h1 className="mt-3 text-3xl font-semibold tracking-[-0.03em] text-stone-950">Не получилось загрузить живые сборы</h1>
      <p className="mt-4 leading-7 text-stone-600">
        Обычно это занимает пару секунд. Попробуйте обновить данные, и мы вернем вас к историям поддержки.
      </p>
      <button
        onClick={reset}
        className="mt-6 rounded-full bg-stone-950 px-5 py-3 font-semibold text-white transition hover:bg-emerald-700"
        type="button"
      >
        Попробовать снова
      </button>
    </section>
  );
}
