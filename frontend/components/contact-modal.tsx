"use client";

import { useEffect, useState } from "react";
import { sendContactRequest } from "@/lib/api";
import type { AuthUser, ContactSubject } from "@/lib/types";

const subjects: ContactSubject[] = ["Общий вопрос", "Сообщить об ошибке", "Предложение", "Проблема со сбором", "Другое"];
const emailPattern = /^[^\s@]+@[^\s@]+\.[^\s@]+$/;

type ContactModalProps = {
  isOpen: boolean;
  onClose: () => void;
  user: AuthUser | null;
};

export function ContactModal({ isOpen, onClose, user }: ContactModalProps) {
  const [form, setForm] = useState({
    name: "",
    email: "",
    subject: subjects[0],
    message: "",
  });
  const [status, setStatus] = useState<"idle" | "sending" | "success" | "error">("idle");
  const [error, setError] = useState<string | null>(null);

  useEffect(() => {
    if (!isOpen) {
      setStatus("idle");
      setError(null);
      return;
    }
  }, [isOpen]);

  useEffect(() => {
    if (!isOpen) return;
    setForm((current) => ({
      ...current,
      name: current.name || userDisplayName(user),
      email: current.email || user?.email || "",
    }));
  }, [isOpen, user]);

  useEffect(() => {
    if (!isOpen) return;
    const onKeyDown = (event: KeyboardEvent) => {
      if (event.key === "Escape") onClose();
    };
    window.addEventListener("keydown", onKeyDown);
    return () => window.removeEventListener("keydown", onKeyDown);
  }, [isOpen, onClose]);

  if (!isOpen) return null;

  const validationError = validateForm(form);
  const canSubmit = !validationError && status !== "sending";

  const handleSubmit = async (event: React.FormEvent<HTMLFormElement>) => {
    event.preventDefault();
    const nextError = validateForm(form);
    if (nextError) {
      setError(nextError);
      return;
    }

    setStatus("sending");
    setError(null);
    try {
      await sendContactRequest(form);
      setStatus("success");
    } catch (requestError) {
      setStatus("error");
      setError(requestError instanceof Error ? requestError.message : "Не удалось отправить сообщение.");
    }
  };

  return (
    <div className="fixed inset-0 z-50 flex items-center justify-center px-4 py-6" role="dialog" aria-modal="true" aria-labelledby="contact-modal-title">
      <button className="absolute inset-0 bg-stone-950/60 backdrop-blur-sm" onClick={onClose} type="button" aria-label="Закрыть обратную связь" />
      <div className="relative max-h-[calc(100vh-3rem)] w-full max-w-2xl overflow-y-auto rounded-[28px] bg-white p-5 text-stone-950 shadow-[0_28px_110px_rgba(0,0,0,0.28)] md:p-7">
        {status === "success" ? (
          <div className="py-8 text-center">
            <p className="text-sm font-semibold uppercase tracking-[0.18em] text-emerald-700">Спасибо!</p>
            <h2 id="contact-modal-title" className="mt-3 text-3xl font-semibold">Мы получили ваше сообщение.</h2>
            <p className="mx-auto mt-4 max-w-md leading-7 text-stone-600">Обычно отвечаем в течение 1–2 рабочих дней.</p>
            <button className="mt-7 rounded-full bg-stone-950 px-6 py-3 font-semibold text-white transition hover:bg-emerald-800" onClick={onClose} type="button">
              Закрыть
            </button>
          </div>
        ) : (
          <>
            <div className="flex items-start justify-between gap-4">
              <div>
                <p className="text-sm font-semibold uppercase tracking-[0.18em] text-emerald-700">обратная связь</p>
                <h2 id="contact-modal-title" className="mt-2 text-2xl font-semibold md:text-3xl">Напишите нам</h2>
              </div>
              <button className="rounded-full bg-stone-100 px-4 py-2 text-sm font-semibold text-stone-700 transition hover:bg-stone-200" onClick={onClose} type="button">
                Закрыть
              </button>
            </div>

            <form onSubmit={handleSubmit} className="mt-6 space-y-4">
              <div className="grid gap-4 md:grid-cols-2">
                <ContactInput label="Имя" value={form.name} onChange={(value) => setForm((current) => ({ ...current, name: value }))} maxLength={120} />
                <ContactInput label="Email" value={form.email} onChange={(value) => setForm((current) => ({ ...current, email: value }))} type="email" maxLength={255} />
              </div>

              <label className="block">
                <span className="text-sm font-semibold text-stone-700">Тема</span>
                <select
                  value={form.subject}
                  onChange={(event) => setForm((current) => ({ ...current, subject: event.target.value as ContactSubject }))}
                  className="mt-2 w-full rounded-2xl border border-stone-200 bg-white px-4 py-3 outline-none transition focus:border-emerald-500 focus:ring-4 focus:ring-emerald-100"
                  required
                >
                  {subjects.map((subject) => (
                    <option key={subject} value={subject}>
                      {subject}
                    </option>
                  ))}
                </select>
              </label>

              <label className="block">
                <span className="text-sm font-semibold text-stone-700">Сообщение</span>
                <textarea
                  value={form.message}
                  onChange={(event) => setForm((current) => ({ ...current, message: event.target.value }))}
                  minLength={20}
                  maxLength={3000}
                  rows={7}
                  className="mt-2 w-full resize-none rounded-2xl border border-stone-200 px-4 py-3 leading-6 outline-none transition focus:border-emerald-500 focus:ring-4 focus:ring-emerald-100"
                  required
                />
                <span className="mt-2 block text-xs text-stone-500">{form.message.length}/3000</span>
              </label>

              {error ? <p className="rounded-2xl bg-rose-50 px-4 py-3 text-sm leading-6 text-rose-800">{error}</p> : null}

              <div className="flex flex-col gap-3 sm:flex-row sm:items-center sm:justify-between">
                <p className="text-sm leading-6 text-stone-500">Все поля обязательны.</p>
                <button className="rounded-full bg-stone-950 px-6 py-3 font-semibold text-white transition hover:bg-emerald-800 disabled:cursor-not-allowed disabled:opacity-60" disabled={!canSubmit} type="submit">
                  {status === "sending" ? "Отправляем..." : "Отправить"}
                </button>
              </div>
            </form>
          </>
        )}
      </div>
    </div>
  );
}

function ContactInput({ label, value, onChange, type = "text", maxLength }: { label: string; value: string; onChange: (value: string) => void; type?: string; maxLength: number }) {
  return (
    <label className="block">
      <span className="text-sm font-semibold text-stone-700">{label}</span>
      <input
        value={value}
        onChange={(event) => onChange(event.target.value)}
        type={type}
        maxLength={maxLength}
        className="mt-2 w-full rounded-2xl border border-stone-200 px-4 py-3 outline-none transition focus:border-emerald-500 focus:ring-4 focus:ring-emerald-100"
        required
      />
    </label>
  );
}

function validateForm(form: { name: string; email: string; subject: ContactSubject; message: string }) {
  if (!form.name.trim() || !form.email.trim() || !form.subject || !form.message.trim()) return "Заполните все поля.";
  if (!emailPattern.test(form.email)) return "Укажите корректный email.";
  if (form.message.trim().length < 20) return "Сообщение должно быть не короче 20 символов.";
  if (form.message.length > 3000) return "Сообщение должно быть не длиннее 3000 символов.";
  return null;
}

function userDisplayName(user: AuthUser | null) {
  if (!user) return "";
  return [user.first_name, user.last_name].filter(Boolean).join(" ").trim() || user.username;
}
