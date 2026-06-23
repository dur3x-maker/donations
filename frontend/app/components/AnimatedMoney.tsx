"use client";

import { animate, motion, useMotionValue, useTransform } from "framer-motion";
import { useEffect } from "react";
import { formatMoney } from "@/lib/format";

export function AnimatedMoney({ value, className }: { value: string | number; className?: string }) {
  const amount = useMotionValue(Number(value));
  const formatted = useTransform(amount, (latest) => formatMoney(latest));

  useEffect(() => {
    const controls = animate(amount, Number(value), {
      duration: 0.75,
      ease: [0.22, 1, 0.36, 1],
    });
    return controls.stop;
  }, [amount, value]);

  return <motion.span className={className}>{formatted}</motion.span>;
}
