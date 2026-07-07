"use client";

import Link from "next/link";
import { FormEvent, useState } from "react";
import { useRouter, useSearchParams } from "next/navigation";
import { useAuth } from "@/components/providers/auth-provider";
import { UserErrorAlert } from "@/components/user-error-alert";
import { toUserError, type UserError } from "@/lib/user-errors";
import { EMAIL_HINT, EMAIL_PATTERN } from "@/lib/validation";

export default function LoginPage() {
  const router = useRouter();
  const searchParams = useSearchParams();
  const { login } = useAuth();
  const [email, setEmail] = useState("");
  const [password, setPassword] = useState("");
  const [isSubmitting, setIsSubmitting] = useState(false);
  const [error, setError] = useState<UserError | null>(null);

  async function handleSubmit(event: FormEvent<HTMLFormElement>) {
    event.preventDefault();
    setError(null);
    setIsSubmitting(true);

    try {
      await login({ email, password });
      router.push(searchParams.get("next") || "/dashboard");
    } catch (err) {
      setError(toUserError(err, { title: "Не удалось войти" }));
    } finally {
      setIsSubmitting(false);
    }
  }

  return (
    <section className="mx-auto max-w-xl space-y-6">
      <div className="rounded-[24px] bg-stone-950 p-6 text-white shadow-[0_24px_80px_rgba(28,25,23,0.20)] md:rounded-[32px] md:p-10">
        <p className="text-sm font-medium uppercase tracking-[0.18em] text-emerald-300">аккаунт</p>
        <h1 className="mt-3 text-3xl font-semibold tracking-tight md:text-5xl">Войти в профиль</h1>
        <p className="mt-4 leading-7 text-stone-300">Продолжите с email и паролем, чтобы открыть личные разделы.</p>
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
        <label className="block text-sm font-medium text-stone-700">
          Пароль
          <input
            className="mt-2 w-full rounded-2xl border border-stone-200 bg-stone-50 px-4 py-3 outline-none transition focus:border-emerald-500 focus:bg-white"
            type="password"
            value={password}
            onChange={(event) => setPassword(event.target.value)}
            required
          />
        </label>
        <div className="flex flex-wrap items-center gap-3">
          <button
            className="rounded-full bg-stone-950 px-5 py-3 font-medium text-white transition hover:bg-emerald-700 disabled:cursor-not-allowed disabled:opacity-70"
            disabled={isSubmitting}
            type="submit"
          >
            {isSubmitting ? "Входим..." : "Войти"}
          </button>
          <Link href="/forgot-password" className="text-sm font-medium text-stone-600 hover:text-stone-900">
            Забыли пароль?
          </Link>
          <Link href="/register" className="text-sm font-medium text-emerald-800 hover:text-emerald-900">
            Создать аккаунт
          </Link>
        </div>
      </form>

      {error ? <UserErrorAlert error={error} /> : null}
    </section>
  );
}
