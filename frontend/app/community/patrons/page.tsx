import { PatronCommunityCard } from "@/app/community/patrons/PatronCommunityCard";
import { fetchCommunityPatrons } from "@/lib/api";

export const dynamic = "force-dynamic";

export default async function PatronsPage() {
  const patrons = await fetchCommunityPatrons();

  return (
    <section className="mx-auto max-w-6xl space-y-8">
      <header className="overflow-hidden rounded-[34px] bg-emerald-950 p-6 text-white shadow-[0_24px_80px_rgba(6,78,59,0.20)] md:p-10">
        <p className="text-xs font-semibold uppercase tracking-[0.2em] text-emerald-300">постоянная поддержка</p>
        <h1 className="mt-3 max-w-3xl text-4xl font-semibold tracking-tight md:text-6xl">Круг меценатов</h1>
        <p className="mt-5 max-w-3xl text-base leading-7 text-emerald-50/85 md:text-lg">
          Это пространство признания людей, для которых помощь стала регулярной частью жизни сообщества.
          Круг показывает не места и не рейтинг, а продолжительность участия, число поддержанных историй
          и реальный общий вклад.
        </p>
        <div className="mt-7 grid gap-3 sm:grid-cols-3">
          <CommunityPrinciple title="Постоянство" text="Поддержка разных историй на протяжении времени." />
          <CommunityPrinciple title="Признание" text="Благодарность за участие без сравнения людей между собой." />
          <CommunityPrinciple title="Общий результат" text="Видимый след помощи в жизни авторов и сообщества." />
        </div>
      </header>

      <section className="rounded-[28px] border border-emerald-100 bg-white p-6 shadow-sm md:p-8">
        <p className="text-sm font-semibold uppercase tracking-[0.18em] text-emerald-700">возможности круга</p>
        <h2 className="mt-2 text-2xl font-semibold text-stone-950">Участники Круга меценатов получают:</h2>
        <ul className="mt-4 space-y-3 text-stone-700">
          <li>• ранний доступ к новым функциям;</li>
          <li>• возможность участвовать в тестировании;</li>
          <li>• возможность влиять на развитие платформы.</li>
        </ul>
      </section>

      <div>
        <p className="text-sm font-semibold uppercase tracking-[0.18em] text-emerald-700">участники круга</p>
        <h2 className="mt-2 text-3xl font-semibold tracking-tight text-stone-950">Люди, которые остаются рядом</h2>
        <p className="mt-2 max-w-2xl leading-7 text-stone-600">
          Карточки расположены по имени. Здесь нет первых мест — вклад каждого участника важен сам по себе.
        </p>
      </div>

      {patrons.length ? (
        <div className="grid gap-5 lg:grid-cols-2">
          {patrons.map((patron) => <PatronCommunityCard key={patron.user_id} patron={patron} />)}
        </div>
      ) : (
        <section className="rounded-[30px] border border-emerald-100 bg-white p-7 shadow-sm md:p-9">
          <h2 className="text-2xl font-semibold text-stone-950">Круг только формируется</h2>
          <p className="mt-3 max-w-2xl leading-7 text-stone-600">
            Участник присоединяется к Кругу после 50 подтверждённых вкладов в чужие истории.
            Когда это произойдёт, здесь появится история его постоянной поддержки — без рейтингов и соревнования.
          </p>
        </section>
      )}
    </section>
  );
}

function CommunityPrinciple({ title, text }: { title: string; text: string }) {
  return (
    <div className="rounded-[22px] bg-white/8 p-4 ring-1 ring-white/10">
      <p className="font-semibold text-white">{title}</p>
      <p className="mt-1 text-sm leading-6 text-emerald-50/70">{text}</p>
    </div>
  );
}
