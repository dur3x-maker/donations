import Link from "next/link";
import type { ActivityItem } from "@/lib/types";

type ActivityFeedProps = {
  activities: ActivityItem[];
};

export function ActivityFeed({ activities }: ActivityFeedProps) {
  const visibleActivities = activities.slice(0, 3);

  return (
    <section id="activity" className="scroll-mt-24 grid gap-8 md:grid-cols-[0.5fr_0.5fr] md:items-start">
      <div className="mb-5 flex items-start justify-between gap-4">
        <div className="max-w-2xl">
          <p className="text-xs font-semibold uppercase tracking-[0.18em] text-emerald-700">сейчас происходит</p>
          <h2 className="mt-2 text-3xl font-semibold leading-tight text-stone-950">Платформа движется</h2>
        </div>
      </div>

      {visibleActivities.length ? (
        <div className="border-l border-stone-200 pl-4">
          <div className="space-y-4">
            {visibleActivities.map((activity) => (
              <ActivityRow key={activity.id} activity={activity} />
            ))}
          </div>
        </div>
      ) : (
        <div className="border-y border-stone-200 py-5 text-sm leading-6 text-stone-600">
          Здесь появятся первые действия: поддержка, новые истории и закрытые сборы.
        </div>
      )}
    </section>
  );
}

function ActivityRow({ activity }: { activity: ActivityItem }) {
  const actorName = activity.actor?.username ?? "Кто-то";
  const campaignTitle = activity.campaign?.title;

  return (
    <div className="relative flex items-start gap-3">
      <span className="absolute -left-[21px] top-2 h-2.5 w-2.5 rounded-full bg-emerald-600 ring-4 ring-white" />
      <Link
        href={activity.actor ? `/u/${activity.actor.username}` : "/campaigns"}
        className="flex h-8 w-8 shrink-0 items-center justify-center rounded-full bg-emerald-100 text-xs font-semibold text-emerald-900"
      >
        {actorName.slice(0, 1).toUpperCase()}
      </Link>

      <div className="min-w-0 flex-1">
        <ActivityCopy activity={activity} actorName={actorName} campaignTitle={campaignTitle} />
        <p className="mt-1 text-[11px] text-stone-400">{relativeTime(activity.created_at)}</p>
      </div>
    </div>
  );
}

function ActorLink({ activity, actorName }: { activity: ActivityItem; actorName: string }) {
  if (!activity.actor) {
    return <span className="font-semibold text-stone-950">{actorName}</span>;
  }

  return (
    <Link href={`/u/${activity.actor.username}`} className="font-semibold text-stone-950 transition hover:text-emerald-800">
      {actorName}
    </Link>
  );
}

function ActivityCopy({ activity, actorName, campaignTitle }: { activity: ActivityItem; actorName: string; campaignTitle?: string }) {
  const title = campaignTitle ? `«${campaignTitle}»` : "одну из живых целей";

  if (activity.type === "campaign_created") {
    return (
      <p className="truncate text-sm leading-5 text-stone-600">
        Новая история от <ActorLink activity={activity} actorName={actorName} />: {title}
      </p>
    );
  }

  if (activity.type === "campaign_completed") {
    return (
      <p className="truncate text-sm leading-5 text-stone-600">
        Сбор {title} закрыт при участии <ActorLink activity={activity} actorName={actorName} />
      </p>
    );
  }

  if (activity.type === "unlock_achieved") {
    return (
      <p className="truncate text-sm leading-5 text-stone-600">
        <ActorLink activity={activity} actorName={actorName} /> теперь может рассказать свою историю
      </p>
    );
  }

  return (
    <p className="truncate text-sm leading-5 text-stone-600">
      <ActorLink activity={activity} actorName={actorName} /> поддерживает {title}
    </p>
  );
}

function relativeTime(value: string) {
  const minutes = Math.max(0, Math.floor((Date.now() - new Date(value).getTime()) / 60000));
  if (minutes < 1) return "только что";
  if (minutes < 60) return `${minutes} мин назад`;
  const hours = Math.floor(minutes / 60);
  if (hours < 24) return `${hours} ч назад`;
  return `${Math.floor(hours / 24)} дн назад`;
}
