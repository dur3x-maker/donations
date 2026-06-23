"use client";

import Link from "next/link";
import { FormEvent, useState } from "react";
import { useRouter, useSearchParams } from "next/navigation";
import { useAuth } from "@/components/providers/auth-provider";
import { EMAIL_HINT, EMAIL_PATTERN, USERNAME_HINT, USERNAME_PATTERN } from "@/lib/validation";

export default function RegisterPage() {
  const router = useRouter();
  const searchParams = useSearchParams();
  const { register } = useAuth();
  const [email, setEmail] = useState("");
  const [username, setUsername] = useState("");
  const [password, setPassword] = useState("");
  const [confirmPassword, setConfirmPassword] = useState("");
  const [isSubmitting, setIsSubmitting] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const isPasswordConfirmed = confirmPassword.length > 0 && password === confirmPassword;
  const isSubmitDisabled = isSubmitting || !isPasswordConfirmed;

  async function handleSubmit(event: FormEvent<HTMLFormElement>) {
    event.preventDefault();
    if (isSubmitDisabled) return;

    setError(null);
    setIsSubmitting(true);

    try {
      await register({ email, username, password });
      router.push(searchParams.get("next") || "/dashboard");
    } catch (err) {
      setError(err instanceof Error ? err.message : "Не получилось зарегистрироваться");
    } finally {
      setIsSubmitting(false);
    }
  }

  return (
    <section className="mx-auto max-w-xl space-y-6">
      <div className="rounded-[32px] bg-stone-950 p-6 text-white shadow-[0_24px_80px_rgba(28,25,23,0.20)] md:p-10">
        <p className="text-sm font-medium uppercase tracking-[0.18em] text-emerald-300">новый профиль</p>
        <h1 className="mt-3 text-3xl font-semibold tracking-tight md:text-5xl">Создать аккаунт</h1>
        <p className="mt-4 leading-7 text-stone-300">Имя пользователя: 3-24 символа, латиница, цифры и подчеркивание.</p>
      </div>

      <form onSubmit={handleSubmit} className="space-y-4 rounded-[28px] border border-stone-200 bg-white p-5 shadow-[0_18px_60px_rgba(28,25,23,0.08)]">
        <label className="block text-sm font-medium text-stone-700">
          Эл. почта
          <input
            aria-describedby="email-help"
            className="mt-2 w-full rounded-2xl border border-stone-200 bg-stone-50 px-4 py-3 outline-none transition focus:border-emerald-500 focus:bg-white"
            pattern={EMAIL_PATTERN}
            title={EMAIL_HINT}
            type="email"
            value={email}
            onChange={(event) => setEmail(event.target.value)}
            required
          />
          <span id="email-help" className="mt-2 block text-xs font-normal text-stone-500">{EMAIL_HINT}</span>
        </label>
        <label className="block text-sm font-medium text-stone-700">
          Имя пользователя
          <input
            aria-describedby="username-help"
            className="mt-2 w-full rounded-2xl border border-stone-200 bg-stone-50 px-4 py-3 outline-none transition focus:border-emerald-500 focus:bg-white"
            minLength={3}
            maxLength={24}
            pattern={USERNAME_PATTERN}
            title={USERNAME_HINT}
            value={username}
            onChange={(event) => setUsername(event.target.value)}
            required
          />
          <span id="username-help" className="mt-2 block text-xs font-normal text-stone-500">{USERNAME_HINT}</span>
        </label>
        <div className="block text-sm font-medium text-stone-700">
          <label htmlFor="password">Пароль</label>
          <input
            id="password"
            aria-describedby="password-help"
            className="mt-2 w-full rounded-2xl border border-stone-200 bg-stone-50 px-4 py-3 outline-none transition focus:border-emerald-500 focus:bg-white"
            minLength={8}
            type="password"
            value={password}
            onChange={(event) => setPassword(event.target.value)}
            required
          />
          <span id="password-help" className="mt-2 block text-xs font-normal text-stone-500">
            Минимум 8 символов
          </span>
        </div>
        <div className="block text-sm font-medium text-stone-700">
          <label htmlFor="confirm-password">Повторите пароль</label>
          <input
            id="confirm-password"
            aria-describedby={confirmPassword ? "confirm-password-status" : undefined}
            className="mt-2 w-full rounded-2xl border border-stone-200 bg-stone-50 px-4 py-3 outline-none transition focus:border-emerald-500 focus:bg-white"
            minLength={8}
            type="password"
            value={confirmPassword}
            onChange={(event) => setConfirmPassword(event.target.value)}
            required
          />
          {confirmPassword ? (
            <span
              id="confirm-password-status"
              aria-live="polite"
              className={`mt-2 block text-xs font-normal ${
                isPasswordConfirmed ? "text-emerald-700" : "text-rose-500"
              }`}
            >
              {isPasswordConfirmed ? "Пароли совпадают" : "Пароли не совпадают"}
            </span>
          ) : null}
        </div>
        <button
          className="rounded-full bg-stone-950 px-5 py-3 font-medium text-white transition hover:bg-emerald-700 disabled:cursor-not-allowed disabled:opacity-70"
          disabled={isSubmitDisabled}
          type="submit"
        >
          {isSubmitting ? "Создаем..." : "Зарегистрироваться"}
        </button>
        <Link href="/login" className="ml-3 text-sm font-medium text-emerald-800 hover:text-emerald-900">
          Уже есть аккаунт
        </Link>
      </form>

      {error ? <pre className="whitespace-pre-wrap rounded-2xl border border-red-100 bg-red-50 p-4 text-xs text-red-700">{error}</pre> : null}
    </section>
  );
}
