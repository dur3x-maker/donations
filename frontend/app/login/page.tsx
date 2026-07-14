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
    <section className="mx-auto max-w-xl space-y-8 py-4 md:py-8">
      <header className="border-b border-stone-200 pb-7">
        <p className="text-xs font-semibold uppercase tracking-[0.18em] text-emerald-700">аккаунт</p>
        <h1 className="mt-3 text-4xl font-semibold tracking-[-0.035em] text-stone-950 md:text-5xl">Войти в профиль</h1>
        <p className="mt-4 leading-7 text-stone-600">Продолжите с email и паролем, чтобы открыть личные разделы.</p>
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
        <label className="block text-sm font-medium text-stone-700">
          Пароль
          <input
            className="mt-2 w-full rounded-xl border border-stone-300 bg-white px-4 py-3 outline-none transition focus:border-emerald-500 focus:ring-4 focus:ring-emerald-100"
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
