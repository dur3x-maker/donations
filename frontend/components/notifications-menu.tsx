"use client";

import { useCallback, useEffect, useMemo, useRef, useState } from "react";
import { fetchNotifications, markNotificationsRead } from "@/lib/api";
import type { NotificationItem } from "@/lib/types";
import { subscribeNotificationUpdates } from "@/lib/ws";

export function NotificationsMenu() {
  const menuRef = useRef<HTMLDivElement | null>(null);
  const [isOpen, setIsOpen] = useState(false);
  const [notifications, setNotifications] = useState<NotificationItem[]>([]);

  const refreshNotifications = useCallback(async () => {
    const items = await fetchNotifications();
    setNotifications(items);
    return items;
  }, []);

  useEffect(() => {
    refreshNotifications().catch(() => setNotifications([]));
  }, [refreshNotifications]);

  useEffect(() => subscribeNotificationUpdates((event) => {
    setNotifications((current) => [
      event.notification,
      ...current.filter((item) => item.id !== event.notification.id),
    ].slice(0, 20));
  }), []);

  const unreadCount = useMemo(() => notifications.filter((item) => !item.is_read).length, [notifications]);

  useEffect(() => {
    if (!isOpen) return;

    function handlePointerDown(event: PointerEvent) {
      if (menuRef.current && !menuRef.current.contains(event.target as Node)) {
        setIsOpen(false);
      }
    }

    function handleKeyDown(event: KeyboardEvent) {
      if (event.key === "Escape") {
        setIsOpen(false);
      }
    }

    document.addEventListener("pointerdown", handlePointerDown);
    document.addEventListener("keydown", handleKeyDown);
    return () => {
      document.removeEventListener("pointerdown", handlePointerDown);
      document.removeEventListener("keydown", handleKeyDown);
    };
  }, [isOpen]);

  const markVisibleAsRead = useCallback(async (items: NotificationItem[]) => {
    const unreadIds = items.filter((item) => !item.is_read).map((item) => item.id);
    if (!unreadIds.length) return;

    const unreadSet = new Set(unreadIds);
    setNotifications((current) => current.map((item) => (
      unreadSet.has(item.id) ? { ...item, is_read: true } : item
    )));

    try {
      await markNotificationsRead(unreadIds);
    } catch {
      await refreshNotifications().catch(() => undefined);
    }
  }, [refreshNotifications]);

  useEffect(() => {
    if (isOpen) {
      markVisibleAsRead(notifications);
    }
  }, [isOpen, markVisibleAsRead, notifications]);

  function toggleMenu() {
    if (isOpen) {
      setIsOpen(false);
      return;
    }

    setIsOpen(true);
  }

  return (
    <div ref={menuRef} className="relative">
      <button
        onClick={toggleMenu}
        aria-expanded={isOpen}
        aria-haspopup="dialog"
        className="relative rounded-full px-4 py-2 font-medium text-stone-600 transition hover:bg-white hover:text-stone-950"
        type="button"
      >
        Новости
        {unreadCount ? <span className="absolute -right-1 -top-1 flex h-5 min-w-5 items-center justify-center rounded-full bg-emerald-700 px-1 text-[11px] font-semibold text-white">{unreadCount}</span> : null}
      </button>

      {isOpen ? (
        <div
          role="dialog"
          aria-label="Уведомления"
          className="fixed inset-x-3 top-16 z-50 overflow-hidden rounded-[24px] border border-stone-200 bg-white shadow-[0_24px_90px_rgba(28,25,23,0.16)] sm:absolute sm:inset-x-auto sm:right-0 sm:top-11 sm:w-80"
        >
          <div className="border-b border-stone-100 p-4">
            <p className="font-semibold text-stone-950">Уведомления</p>
          </div>
          <div className="max-h-96 overflow-y-auto p-2">
            {notifications.length ? (
              notifications.map((notification) => {
                const className = `block w-full rounded-2xl p-3 text-left ${notification.is_read ? "text-stone-500" : "bg-emerald-50/70 text-stone-800"}`;
                const content = (
                  <>
                    <p className="font-semibold">{notification.title}</p>
                    <p className="mt-1 text-sm leading-5">{notification.body}</p>
                  </>
                );

                return notification.action_url ? (
                  <button
                    key={notification.id}
                    onClick={() => {
                      setIsOpen(false);
                      window.location.href = notification.action_url!;
                    }}
                    className={`${className} transition hover:bg-stone-50`}
                    type="button"
                  >
                    {content}
                  </button>
                ) : (
                  <div key={notification.id} className={className}>
                    {content}
                  </div>
                );
              })
            ) : (
              <p className="p-4 text-sm leading-6 text-stone-500">Пока нет обновлений. Когда истории, которые вы поддержали, будут развиваться, мы покажем это здесь.</p>
            )}
          </div>
        </div>
      ) : null}
    </div>
  );
}
