import { ProgressBar } from "@/app/components/ProgressBar";
import type { ContributionProgress } from "@/lib/types";

type ParticipationCardProps = {
  progress: ContributionProgress;
  compact?: boolean;
};

export function ParticipationCard({ progress, compact = false }: ParticipationCardProps) {
  const count = progress.confirmed_contributions_count;
  const required = progress.required_contributions_count;
  const thresholdReached = count >= required;
  const canCreate = progress.can_create_campaign;
  const isEmpty = count === 0;
  const percent = Math.min(100, Math.round((count / required) * 100));

  return (
    <section className={`border-t border-stone-200 ${compact ? "pt-5" : "pt-6"}`}>
      <div className="flex items-start justify-between gap-3">
        <div>
          <p className="text-xs font-semibold uppercase tracking-[0.18em] text-stone-400">участие</p>
          <h2 className="mt-2 text-xl font-semibold text-stone-950">{thresholdReached ? "Право на создание сбора получено" : "Прогресс открытия сбора"}</h2>
        </div>
        <span className={`rounded-full px-3 py-1.5 text-xs font-semibold ${thresholdReached ? "bg-emerald-50 text-emerald-800" : "bg-stone-100 text-stone-600"}`}>
          {thresholdReached ? "порог пройден" : `порог: ${required} вкладов`}
        </span>
      </div>

      <p className="mt-5 text-3xl font-semibold tracking-tight text-stone-950">
        {thresholdReached ? (canCreate ? "Вы можете создать сбор." : "Порог выполнен.") : isEmpty ? "Первый вклад откроет ваш путь к созданию собственного сбора" : `${count} из ${required}`}
      </p>
      <p className="mt-2 text-sm leading-6 text-stone-600">
        {thresholdReached
          ? canCreate
            ? `${count} подтвержденных вкладов в чужие сборы. Возможность создать сбор уже открыта.`
            : "Новый сбор станет доступен после завершения вашей текущей истории."
          : "Поддержите пять чужих целей, чтобы открыть собственный сбор. Вклады в свои сборы сюда не засчитываются."}
      </p>

      {!thresholdReached ? <div className="mt-5"><ProgressBar value={percent} /></div> : null}
    </section>
  );
}
