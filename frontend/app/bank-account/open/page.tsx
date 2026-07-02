"use client";

import Link from "next/link";
import { useEffect, useState } from "react";
import { useRouter } from "next/navigation";
import { createBankAccountApplication, fetchBankAccountApplicationState } from "@/lib/api";
import type { BankAccountApplicationState } from "@/lib/types";
import { useAuth } from "@/components/providers/auth-provider";

export default function OpenBankAccountPage() {
  const router = useRouter();
  const { isAuthenticated, isLoading } = useAuth();
  const [state, setState] = useState<BankAccountApplicationState | null>(null);
  const [isSubmitting, setIsSubmitting] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const [sent, setSent] = useState(false);

  useEffect(() => {
    if (!isLoading && !isAuthenticated) router.replace("/login?next=/bank-account/open");
  }, [isAuthenticated, isLoading, router]);

  useEffect(() => {
    if (!isAuthenticated) return;
    fetchBankAccountApplicationState()
      .then((nextState) => {
        setState(nextState);
        setSent(nextState.application_status === "PENDING");
      })
      .catch((reason) => setError(reason instanceof Error ? reason.message : "Не удалось загрузить статус заявки."));
  }, [isAuthenticated]);

  async function submitApplication() {
    setIsSubmitting(true);
    setError(null);
    try {
      const application = await createBankAccountApplication();
      setState({
        can_open_bank_account: false,
        has_bank_account: false,
        application_status: application.status,
        application,
      });
      setSent(true);
    } catch (reason) {
      setError(reason instanceof Error ? reason.message : "Не удалось отправить заявку.");
    } finally {
      setIsSubmitting(false);
    }
  }

  if (isLoading || !isAuthenticated || !state) {
    return <section className="mx-auto max-w-4xl rounded-[28px] border border-stone-200 bg-white p-6 text-stone-600 shadow-sm">Загружаем открытие счёта...</section>;
  }

  const unavailable = !state.can_open_bank_account && !sent;

  return (
    <section className="mx-auto max-w-5xl overflow-hidden rounded-[32px] border border-emerald-100 bg-white shadow-[0_24px_80px_rgba(28,25,23,0.12)]">
      <div className="grid lg:grid-cols-[minmax(0,1fr)_360px]">
        <div className="p-6 md:p-10">
          <Link href="/dashboard" className="text-sm font-semibold text-emerald-800 hover:text-emerald-950">← Вернуться в кабинет</Link>
          <p className="mt-8 text-xs font-semibold uppercase tracking-[0.2em] text-emerald-700">банк-партнёр</p>
          <h1 className="mt-3 text-4xl font-semibold tracking-tight text-stone-950 md:text-5xl">Открытие счёта</h1>
          <p className="mt-5 max-w-2xl text-base leading-7 text-stone-600">
            Для получения пожертвований необходимо открыть счёт у нашего банка-партнёра.
            После открытия счёта именно на него будут перечисляться средства, собранные в рамках ваших историй.
          </p>
          <p className="mt-4 max-w-2xl text-base leading-7 text-stone-600">
            Процесс занимает всего несколько минут. Сейчас это mock-заявка: банк не вызывается, а интеграция будет подключена позже без изменения этой страницы.
          </p>

          {error ? <div className="mt-6 rounded-2xl border border-rose-100 bg-rose-50 px-4 py-3 text-sm text-rose-800">{error}</div> : null}
          {sent ? (
            <div className="mt-8 rounded-3xl border border-emerald-100 bg-emerald-50 p-6">
              <h2 className="text-2xl font-semibold text-emerald-950">Заявка успешно отправлена.</h2>
              <p className="mt-3 text-sm leading-6 text-emerald-800">
                После подключения банка этот процесс будет происходить автоматически.
              </p>
              <Link href="/dashboard" className="mt-6 inline-flex rounded-full bg-emerald-700 px-5 py-3 text-sm font-semibold text-white transition hover:bg-emerald-800">В личный кабинет</Link>
            </div>
          ) : (
            <div className="mt-8 flex flex-wrap items-center gap-3">
              <button
                type="button"
                onClick={submitApplication}
                disabled={isSubmitting || unavailable}
                className="inline-flex rounded-full bg-stone-950 px-6 py-3 text-sm font-semibold text-white transition hover:bg-emerald-700 disabled:cursor-not-allowed disabled:bg-stone-300"
              >
                {isSubmitting ? "Отправляем..." : "Открыть счёт"}
              </button>
              {unavailable ? <span className="text-sm text-stone-500">Заявка недоступна для текущего статуса аккаунта.</span> : null}
            </div>
          )}
        </div>

        <aside className="bg-stone-950 p-6 text-white md:p-8">
          <p className="text-xs font-semibold uppercase tracking-[0.2em] text-emerald-300">что дальше</p>
          <div className="mt-7 space-y-4">
            <Step index="1" title="Проверим право" text="Минимум 5 подтверждённых донатов уже открывают доступ к заявке." />
            <Step index="2" title="Создадим заявку" text="В mock-версии сохраняем заявку со статусом PENDING." />
            <Step index="3" title="Подключим банк" text="Позже этот же шаг будет отправлять данные в реальный API банка." />
          </div>
        </aside>
      </div>
    </section>
  );
}

function Step({ index, title, text }: { index: string; title: string; text: string }) {
  return (
    <div className="rounded-3xl bg-white/[0.08] p-4 ring-1 ring-white/10">
      <span className="flex h-8 w-8 items-center justify-center rounded-full bg-emerald-400 text-sm font-bold text-stone-950">{index}</span>
      <h2 className="mt-4 text-lg font-semibold">{title}</h2>
      <p className="mt-2 text-sm leading-6 text-stone-300">{text}</p>
    </div>
  );
}
