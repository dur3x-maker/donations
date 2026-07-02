"use client";

import { openContactModal } from "@/lib/contact-modal-events";

export function FaqContactLink() {
  return (
    <button
      type="button"
      onClick={openContactModal}
      className="cursor-pointer font-semibold text-emerald-200 underline decoration-emerald-200/50 underline-offset-4 transition hover:text-white hover:decoration-white"
    >
      форму обратной связи
    </button>
  );
}
