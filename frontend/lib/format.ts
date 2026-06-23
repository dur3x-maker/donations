export function formatMoney(value: string | number) {
  return new Intl.NumberFormat("ru-RU", {
    style: "currency",
    currency: "RUB",
    maximumFractionDigits: 0,
  }).format(Number(value));
}

export function progressPercent(current: string | number, target: string | number) {
  const targetValue = Number(target);
  if (!targetValue) return 0;
  return Math.min(100, Math.round((Number(current) / targetValue) * 100));
}

export function amountLeft(current: string | number, target: string | number) {
  return Math.max(0, Number(target) - Number(current));
}

export function formatDate(value: string) {
  return new Intl.DateTimeFormat("ru-RU", {
    day: "numeric",
    month: "long",
    year: "numeric",
  }).format(new Date(value));
}

export function shortText(value: string, limit = 160) {
  return value.length <= limit ? value : `${value.slice(0, limit - 1).trim()}...`;
}
