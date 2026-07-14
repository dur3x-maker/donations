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
  const [isDrawerOpen, setIsDrawerOpen] = useState(false);

  useEffect(() => {
    const openContact = () => setIsContactOpen(true);
    window.addEventListener(OPEN_CONTACT_MODAL_EVENT, openContact);
    return () => window.removeEventListener(OPEN_CONTACT_MODAL_EVENT, openContact);
  }, []);

  useEffect(() => {
    document.body.style.overflow = isDrawerOpen ? "hidden" : "";
    return () => {
      document.body.style.overflow = "";
    };
  }, [isDrawerOpen]);

  const closeDrawer = () => setIsDrawerOpen(false);
  const handleLogout = () => {
    closeDrawer();
    logout();
  };

  const drawerLinks = isAuthenticated
    ? [
        { label: "Главная", href: "/" },
        { label: "Новости", href: "/#activity" },
        { label: "FAQ", href: "/faq" },
        { label: "Мой профиль", href: "/profile" },
        { label: "Мои сборы", href: "/dashboard" },
      ]
    : [
        { label: "Главная", href: "/" },
        { label: "Новости", href: "/#activity" },
        { label: "FAQ", href: "/faq" },
        { label: "Войти", href: "/login" },
        { label: "Регистрация", href: "/register" },
      ];

  return (
    <>
      <header className="sticky top-0 z-40 border-b border-white/10 bg-stone-950 pt-[env(safe-area-inset-top)] text-white">
        <nav className="mx-auto hidden max-w-[1180px] items-center justify-between gap-3 px-8 py-3 text-sm lg:flex">
          <Brand />

          <div className="flex min-w-0 items-center gap-1 sm:gap-2">
            <button onClick={() => setIsContactOpen(true)} className="rounded-full px-2 py-2 font-medium text-stone-300 transition hover:bg-white/10 hover:text-white sm:px-3" type="button">
              Поддержка
            </button>
            <Link href="/faq" className="px-2 py-2 font-medium text-stone-300 transition hover:text-white sm:px-3">
              FAQ
            </Link>
            <Link href="/campaigns/completed" className="hidden px-3 py-2 font-medium text-stone-300 transition hover:text-white lg:inline-flex">
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
                <Link href="/dashboard" className="hidden px-3 py-2 font-medium text-stone-300 transition hover:text-white sm:inline-flex">
                  Мои сборы
                </Link>
                <NotificationsMenu />
                <button onClick={logout} className="hidden px-3 py-2 font-medium text-stone-300 transition hover:text-white sm:inline-flex" type="button">
                  Выйти
                </button>
              </>
            ) : (
              <>
                <Link href="/login" className="px-3 py-2 font-medium text-stone-300 transition hover:text-white sm:px-4">
                  Войти
                </Link>
                <Link href="/register" className="hidden px-3 py-2 font-medium text-stone-300 transition hover:text-white sm:inline-flex">
                  Регистрация
                </Link>
              </>
            )}
            <SupportLink />
          </div>
        </nav>

        <nav className="mx-auto grid max-w-[1180px] grid-cols-[44px_1fr_auto] items-center gap-2 px-3 py-2 lg:hidden">
          <button
            className="flex h-11 w-11 items-center justify-center rounded-full text-2xl leading-none text-white transition hover:bg-white/10"
            type="button"
            aria-label="Открыть меню"
            aria-expanded={isDrawerOpen}
            onClick={() => setIsDrawerOpen(true)}
          >
            ☰
          </button>
          <div className="flex justify-center">
            <Brand compact />
          </div>
          <SupportLink />
        </nav>
      </header>

      {isDrawerOpen ? (
        <div className="fixed inset-0 z-50 lg:hidden">
          <button className="absolute inset-0 bg-stone-950/60" type="button" aria-label="Закрыть меню" onClick={closeDrawer} />
          <aside className="absolute left-0 top-0 flex h-full w-[min(86vw,320px)] flex-col bg-white pb-[calc(1rem+env(safe-area-inset-bottom))] pt-[calc(1rem+env(safe-area-inset-top))] shadow-xl">
            <div className="flex items-center justify-between border-b border-stone-100 px-4 pb-4">
              <Brand dark />
              <button className="flex h-10 w-10 items-center justify-center rounded-full bg-stone-100 text-xl text-stone-700" type="button" aria-label="Закрыть меню" onClick={closeDrawer}>
                ×
              </button>
            </div>
            <div className="flex flex-1 flex-col gap-1 overflow-y-auto px-3 py-4">
              {drawerLinks.map((link) => (
                <Link key={link.href} href={link.href} onClick={closeDrawer} className="rounded-2xl px-4 py-3 text-base font-semibold text-stone-800 transition hover:bg-stone-100">
                  {link.label}
                </Link>
              ))}
              <button
                className="rounded-2xl px-4 py-3 text-left text-base font-semibold text-stone-800 transition hover:bg-stone-100"
                type="button"
                onClick={() => {
                  closeDrawer();
                  setIsContactOpen(true);
                }}
              >
                Поддержка
              </button>
              {isAuthenticated ? (
                <button className="mt-2 rounded-2xl px-4 py-3 text-left text-base font-semibold text-red-700 transition hover:bg-red-50" type="button" onClick={handleLogout}>
                  Выйти
                </button>
              ) : null}
            </div>
          </aside>
        </div>
      ) : null}

      <ContactModal isOpen={isContactOpen} onClose={() => setIsContactOpen(false)} user={user} />
    </>
  );
}

function Brand({ compact = false, dark = false }: { compact?: boolean; dark?: boolean }) {
  return (
    <Link href="/" className={`flex min-w-0 items-center gap-2 font-semibold tracking-tight ${dark ? "text-stone-950" : "text-white"}`}>
      {!compact ? <span className={`flex h-9 w-9 shrink-0 items-center justify-center rounded-full ${dark ? "bg-stone-950 text-white" : "bg-white text-stone-950"}`}>T</span> : null}
      <span className="truncate">TipForTea</span>
    </Link>
  );
}

function SupportLink() {
  return (
    <Link href="/#campaigns" className="rounded-full bg-white px-3 py-2 text-sm font-semibold text-stone-950 shadow-sm transition hover:bg-emerald-100 sm:px-4">
      Поддержать
    </Link>
  );
}
