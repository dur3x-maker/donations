import Link from "next/link";
import type { UserError } from "@/lib/user-errors";

export function UserErrorAlert({ error }: { error: UserError }) {
  return (
    <div className="rounded-2xl border border-red-100 bg-red-50 p-4 text-sm text-red-900" role="alert">
      <p className="font-semibold">{error.title}</p>
      <p className="mt-1 leading-6 text-red-800">{error.message}</p>
      {error.actions?.length ? (
        <div className="mt-4 flex flex-wrap gap-2">
          {error.actions.map((action) => (
            <Link key={action.href} href={action.href} className="rounded-full bg-white px-4 py-2 text-sm font-semibold text-red-900 shadow-sm ring-1 ring-red-100 transition hover:bg-red-100">
              {action.label}
            </Link>
          ))}
        </div>
      ) : null}
    </div>
  );
}
