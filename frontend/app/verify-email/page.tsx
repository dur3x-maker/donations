"use client";

import Link from "next/link";
import { useEffect, useState } from "react";
import { useSearchParams } from "next/navigation";
import { useAuth } from "@/components/providers/auth-provider";
import { verifyEmail } from "@/lib/api";

type VerifyState = "loading" | "success" | "error";

export default function VerifyEmailPage() {
  const searchParams = useSearchParams();
  const { isAuthenticated, refreshAuth } = useAuth();
  const [state, setState] = useState<VerifyState>("loading");
  const [message, setMessage] = useState("Проверяем ссылку подтверждения.");

  useEffect(() => {
    const token = searchParams.get("token");
    if (!token) {
      setState("error");
      setMessage("Ссылка подтверждения недействительна.");
      return;
    }

    verifyEmail(token)
      .then(async () => {
        if (isAuthenticated) await refreshAuth();
        setState("success");
        setMessage("Email подтверждён ✅");
      })
      .catch((error) => {
        setState("error");
        setMessage(error instanceof Error ? error.message : "Не удалось подтвердить email.");
      });
  }, [isAuthenticated, refreshAuth, searchParams]);

  return (
    <section className="mx-auto max-w-2xl rounded-[32px] border border-emerald-100 bg-white p-6 text-center shadow-[0_24px_80px_rgba(28,25,23,0.10)] md:p-10">
      <p className="text-xs font-semibold uppercase tracking-[0.2em] text-emerald-700">подтверждение email</p>
      <h1 className="mt-4 text-3xl font-semibold tracking-tight text-stone-950 md:text-5xl">
        {state === "success" ? "Email подтверждён ✅" : state === "loading" ? "Проверяем email" : "Ссылка не сработала"}
      </h1>
      <p className="mx-auto mt-4 max-w-xl text-sm leading-6 text-stone-600">{message}</p>
      <div className="mt-7 flex justify-center">
        <Link href="/profile" className="rounded-full bg-stone-950 px-5 py-3 text-sm font-semibold text-white transition hover:bg-emerald-700">
          Перейти в профиль
        </Link>
      </div>
    </section>
  );
}
