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
  const [openIndex, setOpenIndex] = useState<number | null>(0);

  const toggleItem = (index: number) => {
    setOpenIndex((current) => (current === index ? null : index));
  };

  return (
    <div className="editorial-plane editorial-plane-white divide-y divide-stone-200 border-y border-stone-200">
      {items.map((item, index) => {
        const isOpen = openIndex === index;
        const panelId = `faq-panel-${index}`;
        const buttonId = `faq-button-${index}`;

        return (
          <article key={item.question}>
            <button
              id={buttonId}
              type="button"
              aria-expanded={isOpen}
              aria-controls={panelId}
              onClick={() => toggleItem(index)}
              className="flex min-h-16 w-full items-center justify-between gap-4 py-5 text-left transition hover:text-emerald-900 md:py-6"
            >
              <span className="text-base font-semibold leading-6 text-stone-950 md:text-lg">{item.question}</span>
              <span
                aria-hidden="true"
                className={`flex h-10 w-10 shrink-0 items-center justify-center text-2xl font-light text-emerald-800 transition duration-300 ${
                  isOpen ? "rotate-45" : ""
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
                <div className="max-w-4xl space-y-4 pb-7 pr-12 text-sm leading-7 text-stone-700 md:pb-8 md:text-base">
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
