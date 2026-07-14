"use client";

import Link from "next/link";
import { FormEvent, useState } from "react";
import { useRouter, useSearchParams } from "next/navigation";
import { useAuth } from "@/components/providers/auth-provider";
import { UserErrorAlert } from "@/components/user-error-alert";
import { toUserError, type UserError } from "@/lib/user-errors";
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
  const [error, setError] = useState<UserError | null>(null);
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
      setError(toUserError(err, { title: "Не удалось зарегистрироваться" }));
    } finally {
      setIsSubmitting(false);
    }
  }

  return (
    <section className="mx-auto max-w-xl space-y-8 py-4 md:py-8">
      <header className="border-b border-stone-200 pb-7">
        <p className="text-xs font-semibold uppercase tracking-[0.18em] text-emerald-700">новый профиль</p>
        <h1 className="mt-3 text-4xl font-semibold tracking-[-0.035em] text-stone-950 md:text-5xl">Создать аккаунт</h1>
        <p className="mt-4 leading-7 text-stone-600">Имя пользователя: 3–24 символа, латиница, цифры и подчёркивание.</p>
      </header>

      <form onSubmit={handleSubmit} className="space-y-5">
        <label className="block text-sm font-medium text-stone-700">
          Эл. почта
          <input
            aria-describedby="email-help"
            className="mt-2 w-full rounded-xl border border-stone-300 bg-white px-4 py-3 outline-none transition focus:border-emerald-500 focus:ring-4 focus:ring-emerald-100"
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
            className="mt-2 w-full rounded-xl border border-stone-300 bg-white px-4 py-3 outline-none transition focus:border-emerald-500 focus:ring-4 focus:ring-emerald-100"
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
            className="mt-2 w-full rounded-xl border border-stone-300 bg-white px-4 py-3 outline-none transition focus:border-emerald-500 focus:ring-4 focus:ring-emerald-100"
            minLength={8}
            type="password"
            value={password}
            onChange={(event) => setPassword(event.target.value)}
            required
          />
          <span id="password-help" className="mt-2 block text-xs font-normal text-stone-500">Минимум 8 символов</span>
        </div>
        <div className="block text-sm font-medium text-stone-700">
          <label htmlFor="confirm-password">Повторите пароль</label>
          <input
            id="confirm-password"
            aria-describedby={confirmPassword ? "confirm-password-status" : undefined}
            className="mt-2 w-full rounded-xl border border-stone-300 bg-white px-4 py-3 outline-none transition focus:border-emerald-500 focus:ring-4 focus:ring-emerald-100"
            minLength={8}
            type="password"
            value={confirmPassword}
            onChange={(event) => setConfirmPassword(event.target.value)}
            required
          />
          {confirmPassword ? (
            <span id="confirm-password-status" aria-live="polite" className={`mt-2 block text-xs font-normal ${isPasswordConfirmed ? "text-emerald-700" : "text-rose-500"}`}>
              {isPasswordConfirmed ? "Пароли совпадают" : "Пароли не совпадают"}
            </span>
          ) : null}
        </div>
        <div className="flex flex-wrap items-center gap-3">
          <button
            className="rounded-full bg-stone-950 px-5 py-3 font-medium text-white transition hover:bg-emerald-700 disabled:cursor-not-allowed disabled:opacity-70"
            disabled={isSubmitDisabled}
            type="submit"
          >
            {isSubmitting ? "Создаем..." : "Зарегистрироваться"}
          </button>
          <Link href="/login" className="text-sm font-medium text-emerald-800 hover:text-emerald-900">
            Уже есть аккаунт
          </Link>
        </div>
      </form>

      {error ? <UserErrorAlert error={error} /> : null}
    </section>
  );
}
