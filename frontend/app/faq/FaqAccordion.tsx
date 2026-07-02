"use client";

import { useState } from "react";

type FaqItem = {
  question: string;
  answer: string[];
};

type FaqAccordionProps = {
  items: FaqItem[];
};

export function FaqAccordion({ items }: FaqAccordionProps) {
  const [openItems, setOpenItems] = useState<Set<number>>(() => new Set([0]));

  const toggleItem = (index: number) => {
    setOpenItems((current) => {
      const next = new Set(current);

      if (next.has(index)) {
        next.delete(index);
      } else {
        next.add(index);
      }

      return next;
    });
  };

  return (
    <div className="space-y-3">
      {items.map((item, index) => {
        const isOpen = openItems.has(index);
        const panelId = `faq-panel-${index}`;
        const buttonId = `faq-button-${index}`;

        return (
          <article key={item.question} className="overflow-hidden rounded-[24px] border border-stone-200 bg-white shadow-sm">
            <button
              id={buttonId}
              type="button"
              aria-expanded={isOpen}
              aria-controls={panelId}
              onClick={() => toggleItem(index)}
              className="flex w-full items-center justify-between gap-4 px-5 py-4 text-left transition hover:bg-stone-50 md:px-6 md:py-5"
            >
              <span className="text-base font-semibold leading-6 text-stone-950 md:text-lg">{item.question}</span>
              <span
                aria-hidden="true"
                className={`flex h-8 w-8 shrink-0 items-center justify-center rounded-full bg-emerald-50 text-xl font-light text-emerald-800 transition duration-300 ${
                  isOpen ? "rotate-45 bg-emerald-100" : ""
                }`}
              >
                +
              </span>
            </button>
            <div
              id={panelId}
              role="region"
              aria-labelledby={buttonId}
              className={`grid transition-[grid-template-rows] duration-300 ease-out ${isOpen ? "grid-rows-[1fr]" : "grid-rows-[0fr]"}`}
            >
              <div className="overflow-hidden">
                <div className="space-y-4 px-5 pb-5 text-sm leading-7 text-stone-700 md:px-6 md:pb-6 md:text-base">
                  {item.answer.map((paragraph) => (
                    <p key={paragraph}>{paragraph}</p>
                  ))}
                </div>
              </div>
            </div>
          </article>
        );
      })}
    </div>
  );
}
