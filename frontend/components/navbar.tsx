"use client";

import Link from "next/link";
import { useEffect, useState } from "react";
import { ContactModal } from "@/components/contact-modal";
import { useAuth } from "@/components/providers/auth-provider";
import { NotificationsMenu } from "@/components/notifications-menu";
import { OPEN_CONTACT_MODAL_EVENT } from "@/lib/contact-modal-events";

export function Navbar() {
  const { user, isAuthenticated, logout } = useAuth();
  const [isContactOpen, setIsContactOpen] = useState(false);

  useEffect(() => {
    const openContact = () => setIsContactOpen(true);
    window.addEventListener(OPEN_CONTACT_MODAL_EVENT, openContact);
    return () => window.removeEventListener(OPEN_CONTACT_MODAL_EVENT, openContact);
  }, []);

  return (
    <>
      <header className="sticky top-0 z-40 border-b border-white/10 bg-stone-950 text-white shadow-[0_14px_40px_rgba(28,25,23,0.18)]">
        <nav className="mx-auto flex max-w-7xl items-center justify-between gap-3 px-4 py-3 text-sm md:px-6">
          <Link href="/" className="flex min-w-0 items-center gap-2 font-semibold tracking-tight">
            <span className="flex h-9 w-9 shrink-0 items-center justify-center rounded-full bg-white text-stone-950">T</span>
            <span className="truncate">TipForTea</span>
          </Link>

          <div className="flex min-w-0 items-center gap-1 sm:gap-2">
            <button onClick={() => setIsContactOpen(true)} className="rounded-full px-2 py-2 font-medium text-stone-300 transition hover:bg-white/10 hover:text-white sm:px-3" type="button">
              Поддержка
            </button>
            <Link href="/faq" className="rounded-full px-2 py-2 font-medium text-stone-300 transition hover:bg-white/10 hover:text-white sm:px-3">
              FAQ
            </Link>
            <Link href="/campaigns/completed" className="hidden rounded-full px-3 py-2 font-medium text-stone-300 transition hover:bg-white/10 hover:text-white lg:inline-flex">
              Истории успеха
            </Link>
            {isAuthenticated && user ? (
              <>
                <Link href="/profile" className="flex items-center gap-2 rounded-full px-2 py-2 font-medium text-stone-200 transition hover:bg-white/10 hover:text-white sm:px-3">
                  <span className="flex h-8 w-8 items-center justify-center rounded-full bg-emerald-300 text-xs font-semibold text-stone-950">
                    {user.username.slice(0, 1).toUpperCase()}
                  </span>
                  <span className="hidden max-w-28 truncate sm:inline">{user.username}</span>
                </Link>
                <Link href="/dashboard" className="hidden rounded-full px-4 py-2 font-medium text-stone-300 transition hover:bg-white/10 hover:text-white sm:inline-flex">
                  Кабинет
                </Link>
                <NotificationsMenu />
                <button onClick={logout} className="hidden rounded-full px-4 py-2 font-medium text-stone-300 transition hover:bg-white/10 hover:text-white sm:inline-flex" type="button">
                  Выйти
                </button>
              </>
            ) : (
              <>
                <Link href="/login" className="rounded-full px-3 py-2 font-medium text-stone-300 transition hover:bg-white/10 hover:text-white sm:px-4">
                  Войти
                </Link>
                <Link href="/register" className="hidden rounded-full px-4 py-2 font-medium text-stone-300 transition hover:bg-white/10 hover:text-white sm:inline-flex">
                  Регистрация
                </Link>
              </>
            )}
            <Link href="/#campaigns" className="rounded-full bg-white px-3 py-2 font-medium text-stone-950 shadow-sm transition hover:bg-emerald-100 sm:px-4">
              Поддержать
            </Link>
          </div>
        </nav>
      </header>
      <ContactModal isOpen={isContactOpen} onClose={() => setIsContactOpen(false)} user={user} />
    </>
  );
}
