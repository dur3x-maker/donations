export type UserErrorAction = {
  label: string;
  href: string;
};

export type UserError = {
  title: string;
  message: string;
  actions?: UserErrorAction[];
};

const FALLBACK_ERROR: UserError = {
  title: "Не получилось выполнить действие",
  message: "Попробуйте еще раз. Если ошибка повторится, напишите в поддержку.",
};

const ERROR_RULES: Array<{ test: RegExp; error: UserError }> = [
  {
    test: /email.*(использ|занят|already|exists)|почт.*зарегистр/i,
    error: {
      title: "Почта уже зарегистрирована",
      message: "Такая электронная почта уже зарегистрирована.",
      actions: [
        { label: "Войти", href: "/login" },
        { label: "Восстановить пароль", href: "/forgot-password" },
      ],
    },
  },
  {
    test: /(неверн|invalid).*(парол|email|почт)|user.*not.*found|пользователь.*не.*найден/i,
    error: {
      title: "Не удалось войти",
      message: "Проверьте email и пароль. Если не помните пароль, восстановите доступ.",
      actions: [{ label: "Восстановить пароль", href: "/forgot-password" }],
    },
  },
  {
    test: /(token|токен|ссылка).*(истек|устар|invalid|недейств)/i,
    error: {
      title: "Ссылка недействительна",
      message: "Срок действия ссылки истек или она уже была использована.",
      actions: [{ label: "Запросить новую ссылку", href: "/forgot-password" }],
    },
  },
  {
    test: /verification|подтвержден/i,
    error: {
      title: "Не удалось подтвердить email",
      message: "Ссылка подтверждения недействительна или уже была использована.",
    },
  },
  {
    test: /too many|слишком много/i,
    error: {
      title: "Слишком много попыток",
      message: "Подождите немного и попробуйте еще раз.",
    },
  },
  {
    test: /network|сервер|fetch|соедин/i,
    error: {
      title: "Нет связи с сервером",
      message: "Проверьте интернет-соединение и попробуйте еще раз.",
    },
  },
];

export function toUserError(error: unknown, fallback: Partial<UserError> = {}): UserError {
  const rawMessage = error instanceof Error ? error.message : typeof error === "string" ? error : "";
  const message = stripTechnicalDetails(rawMessage);
  const matched = ERROR_RULES.find((rule) => rule.test.test(message));
  return {
    ...(matched?.error ?? FALLBACK_ERROR),
    ...fallback,
    message: fallback.message ?? matched?.error.message ?? (message || FALLBACK_ERROR.message),
  };
}

export function errorMessage(error: unknown, fallback = FALLBACK_ERROR.message) {
  const normalized = toUserError(error);
  return normalized.message || fallback;
}

function stripTechnicalDetails(value: string) {
  return value
    .replace(/\s*\(request[ _-]?id[^)]*\)/gi, "")
    .replace(/\s*\(запрос[^)]*\)/gi, "")
    .replace(/request_id\s*[:=]\s*[\w-]+/gi, "")
    .replace(/traceback[\s\S]*/gi, "")
    .trim();
}
