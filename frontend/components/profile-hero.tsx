import type { ReactNode } from "react";

type ProfileHeroProps = {
  name: string;
  username: string;
  avatarUrl?: string | null;
  eyebrow?: ReactNode;
  metadata: ReactNode[];
  description: string;
  quoteDescription?: boolean;
  action?: ReactNode;
};

export function ProfileHero({
  name,
  username,
  avatarUrl,
  eyebrow,
  metadata,
  description,
  quoteDescription = false,
  action,
}: ProfileHeroProps) {
  return (
    <header className="relative left-1/2 -mt-7 w-screen -translate-x-1/2 bg-stone-950 text-white md:-mt-12">
      <div className="mx-auto grid max-w-[1180px] gap-4 px-4 py-6 sm:grid-cols-[auto_minmax(0,1fr)] sm:items-center sm:gap-6 md:px-8 md:py-10 lg:py-12">
        <ProfileAvatar name={name} username={username} avatarUrl={avatarUrl} />
        <div className="min-w-0">
          {eyebrow ? <p className="text-xs font-semibold uppercase tracking-[0.2em] text-emerald-300">{eyebrow}</p> : null}
          <h1 className={`${eyebrow ? "mt-2 md:mt-3" : ""} break-words text-4xl font-semibold tracking-tight [overflow-wrap:anywhere] md:text-5xl`}>
            {name}
          </h1>
          <p className="mt-1.5 break-words text-base font-medium text-stone-300 [overflow-wrap:anywhere] md:mt-2 md:text-lg">@{username}</p>
          <div className="mt-3 flex flex-wrap gap-x-3 gap-y-1 text-sm text-stone-200 md:mt-4">
            {metadata.map((item, index) => <span key={index}>{item}</span>)}
          </div>
          <p className="mt-4 max-w-3xl break-words text-base leading-7 text-stone-100 [overflow-wrap:anywhere] md:mt-5">
            {quoteDescription ? <>&ldquo;{description}&rdquo;</> : description}
          </p>
          {action ? <div className="mt-4 md:mt-5">{action}</div> : null}
        </div>
      </div>
    </header>
  );
}

function ProfileAvatar({ name, username, avatarUrl }: { name: string; username: string; avatarUrl?: string | null }) {
  const sharedClassName = "h-20 w-20 rounded-full ring-2 ring-white/20 sm:h-28 sm:w-28 md:h-32 md:w-32";

  if (avatarUrl) {
    return (
      <div
        aria-label={`Фото пользователя ${name}`}
        className={`${sharedClassName} bg-cover bg-center`}
        style={{ backgroundImage: `url(${avatarUrl})` }}
      />
    );
  }

  return (
    <div
      aria-label={`Аватар пользователя ${username}`}
      className={`${sharedClassName} flex items-center justify-center bg-emerald-200 text-3xl font-semibold text-emerald-950 sm:text-4xl md:text-5xl`}
    >
      {(name || username).slice(0, 1).toUpperCase()}
    </div>
  );
}
