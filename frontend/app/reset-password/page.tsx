"use client";

import Link from "next/link";
import { FormEvent, useState } from "react";
import { useRouter, useSearchParams } from "next/navigation";
import { resetPassword, saveAuth } from "@/lib/api";
import { UserErrorAlert } from "@/components/user-error-alert";
import { toUserError, type UserError } from "@/lib/user-errors";

export default function ResetPasswordPage() {
  const router = useRouter();
  const searchParams = useSearchParams();
  const token = searchParams.get("token") || "";
  const [password, setPassword] = useState("");
  const [confirmPassword, setConfirmPassword] = useState("");
  const [isSubmitting, setIsSubmitting] = useState(false);
  const [error, setError] = useState<UserError | null>(null);
  const isPasswordConfirmed = confirmPassword.length > 0 && password === confirmPassword;
  const isSubmitDisabled = isSubmitting || !token || !isPasswordConfirmed || password.length < 8;

  async function handleSubmit(event: FormEvent<HTMLFormElement>) {
    event.preventDefault();
    if (isSubmitDisabled) return;

    setError(null);
    setIsSubmitting(true);
    try {
      const auth = await resetPassword({ token, password });
      saveAuth(auth);
      window.dispatchEvent(new CustomEvent("auth:updated", { detail: auth.user }));
      router.push("/dashboard");
    } catch (requestError) {
      setError(toUserError(requestError, { title: "Не удалось изменить пароль" }));
    } finally {
      setIsSubmitting(false);
    }
  }

  return (
    <section className="mx-auto max-w-xl space-y-8 py-4 md:py-8">
      <header className="border-b border-stone-200 pb-7">
        <p className="text-xs font-semibold uppercase tracking-[0.18em] text-emerald-700">новый пароль</p>
        <h1 className="mt-3 text-4xl font-semibold tracking-[-0.035em] text-stone-950 md:text-5xl">Задайте новый пароль</h1>
        <p className="mt-4 leading-7 text-stone-600">После смены пароля вы сразу войдёте в аккаунт.</p>
      </header>

      {!token ? (
        <UserErrorAlert error={{ title: "Ссылка недействительна", message: "В ссылке нет токена восстановления.", actions: [{ label: "Запросить новую ссылку", href: "/forgot-password" }] }} />
      ) : (
        <form onSubmit={handleSubmit} className="space-y-5">
          <label className="block text-sm font-medium text-stone-700">
            Новый пароль
            <input
              className="mt-2 w-full rounded-xl border border-stone-300 bg-white px-4 py-3 outline-none transition focus:border-emerald-500 focus:ring-4 focus:ring-emerald-100"
              minLength={8}
              type="password"
              value={password}
              onChange={(event) => setPassword(event.target.value)}
              required
            />
          </label>
          <label className="block text-sm font-medium text-stone-700">
            Повторите пароль
            <input
              className="mt-2 w-full rounded-xl border border-stone-300 bg-white px-4 py-3 outline-none transition focus:border-emerald-500 focus:ring-4 focus:ring-emerald-100"
              minLength={8}
              type="password"
              value={confirmPassword}
              onChange={(event) => setConfirmPassword(event.target.value)}
              required
            />
            {confirmPassword ? <span className={`mt-2 block text-xs font-normal ${isPasswordConfirmed ? "text-emerald-700" : "text-rose-500"}`}>{isPasswordConfirmed ? "Пароли совпадают" : "Пароли не совпадают"}</span> : null}
          </label>
          <div className="flex flex-wrap items-center gap-3">
            <button className="rounded-full bg-stone-950 px-5 py-3 font-medium text-white transition hover:bg-emerald-700 disabled:cursor-not-allowed disabled:opacity-70" disabled={isSubmitDisabled} type="submit">
              {isSubmitting ? "Сохраняем..." : "Изменить пароль"}
            </button>
            <Link href="/login" className="text-sm font-medium text-emerald-800 hover:text-emerald-900">
              Войти
            </Link>
          </div>
        </form>
      )}

      {error ? <UserErrorAlert error={error} /> : null}
    </section>
  );
}
