type ProgressBarProps = {
  value: number;
  className?: string;
};

export function ProgressBar({ value, className = "h-3" }: ProgressBarProps) {
  const safeValue = Math.max(0, Math.min(100, value));

  return (
    <div className={`${className} overflow-hidden rounded-full bg-stone-100`}>
      <div className="h-full rounded-full bg-[linear-gradient(90deg,#15803d,#84cc16)] transition-all duration-500 ease-out" style={{ width: `${safeValue}%` }} />
    </div>
  );
}
