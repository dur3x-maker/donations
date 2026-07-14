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
    <section className="mx-auto max-w-xl space-y-8 py-4 md:py-8">
      <header className="border-b border-stone-200 pb-7">
        <p className="text-xs font-semibold uppercase tracking-[0.18em] text-emerald-700">доступ</p>
        <h1 className="mt-3 text-4xl font-semibold tracking-[-0.035em] text-stone-950 md:text-5xl">Восстановить пароль</h1>
        <p className="mt-4 leading-7 text-stone-600">Укажите email, и мы отправим ссылку для смены пароля.</p>
      </header>

      <form onSubmit={handleSubmit} className="space-y-5">
        <label className="block text-sm font-medium text-stone-700">
          Эл. почта
          <input
            className="mt-2 w-full rounded-xl border border-stone-300 bg-white px-4 py-3 outline-none transition focus:border-emerald-500 focus:ring-4 focus:ring-emerald-100"
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
