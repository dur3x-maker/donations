"use client";

import Link from "next/link";
import { FormEvent, useState } from "react";
import { forgotPassword } from "@/lib/api";
import { UserErrorAlert } from "@/components/user-error-alert";
import { toUserError, type UserError } from "@/lib/user-errors";
import { EMAIL_HINT, EMAIL_PATTERN } from "@/lib/validation";

export default function ForgotPasswordPage() {
  const [email, setEmail] = useState("");
  const [isSubmitting, setIsSubmitting] = useState(false);
  const [message, setMessage] = useState<string | null>(null);
  const [error, setError] = useState<UserError | null>(null);

  async function handleSubmit(event: FormEvent<HTMLFormElement>) {
    event.preventDefault();
    setError(null);
    setMessage(null);
    setIsSubmitting(true);

    try {
      const response = await forgotPassword(email);
      setMessage(response.message);
    } catch (requestError) {
      setError(toUserError(requestError, { title: "Не удалось отправить письмо" }));
    } finally {
      setIsSubmitting(false);
    }
  }

  return (
    <section className="mx-auto max-w-xl space-y-6">
      <div className="rounded-[24px] bg-stone-950 p-6 text-white shadow-[0_24px_80px_rgba(28,25,23,0.20)] md:rounded-[32px] md:p-10">
        <p className="text-sm font-medium uppercase tracking-[0.18em] text-emerald-300">доступ</p>
        <h1 className="mt-3 text-3xl font-semibold tracking-tight md:text-5xl">Восстановить пароль</h1>
        <p className="mt-4 leading-7 text-stone-300">Укажите email, и мы отправим ссылку для смены пароля.</p>
      </div>

      <form onSubmit={handleSubmit} className="space-y-4 rounded-[24px] border border-stone-200 bg-white p-5 shadow-[0_18px_60px_rgba(28,25,23,0.08)] md:rounded-[28px]">
        <label className="block text-sm font-medium text-stone-700">
          Эл. почта
          <input
            className="mt-2 w-full rounded-2xl border border-stone-200 bg-stone-50 px-4 py-3 outline-none transition focus:border-emerald-500 focus:bg-white"
            pattern={EMAIL_PATTERN}
            title={EMAIL_HINT}
            type="email"
            value={email}
            onChange={(event) => setEmail(event.target.value)}
            required
          />
        </label>
        <div className="flex flex-wrap items-center gap-3">
          <button className="rounded-full bg-stone-950 px-5 py-3 font-medium text-white transition hover:bg-emerald-700 disabled:cursor-not-allowed disabled:opacity-70" disabled={isSubmitting} type="submit">
            {isSubmitting ? "Отправляем..." : "Отправить письмо"}
          </button>
          <Link href="/login" className="text-sm font-medium text-emerald-800 hover:text-emerald-900">
            Войти
          </Link>
        </div>
      </form>

      {message ? <div className="rounded-2xl border border-emerald-100 bg-emerald-50 p-4 text-sm font-medium text-emerald-900">{message}</div> : null}
      {error ? <UserErrorAlert error={error} /> : null}
    </section>
  );
}
