# Telegram DevOps Worker

DevOps Worker remains in the separate **Sophie** project. Donations contains only a
Telegram Gateway and communicates with Sophie through the versioned HTTP contract:

```text
Telegram group
  -> Donations devops-gateway
  -> POST Sophie /api/v1/devops/commands
  -> headless sophie-devops-service
  -> DevOpsWorker
  -> restricted SSH key + forced-command wrapper
  -> /opt/donations
```

No Sophie modules are imported or copied into Donations.

## Security

- use a dedicated Telegram bot token; do not reuse the personal Sophie bot token;
- `DEVOPS_TELEGRAM_ALLOWED_USER_IDS` is the Telegram User ID whitelist in Donations;
- Sophie independently checks the same IDs through
  `DEVOPS_API_ALLOWED_TELEGRAM_USER_IDS`;
- `DEVOPS_TELEGRAM_CHAT_IDS` restricts the entrypoint to explicit groups;
- `SOPHIE_DEVOPS_API_TOKEN_FILE` and Sophie's `DEVOPS_API_TOKEN_FILE` point to the
  same long, random secret of at least 32 characters;
- the headless API binds only to `127.0.0.1:8001`;
- the headless image has no Docker socket and uses Sophie's restricted SSH identity.

The Gateway ignores all ordinary group messages while asleep. It wakes only on `Софи, ...`
or the dedicated bot's real `@username`. After the final bot response, follow-up commands are
accepted for 60 seconds. Long-running API calls keep the session busy and do not start this
timer.

## Telegram setup

Create a dedicated bot and add it to the target group. In BotFather, disable privacy mode for
this bot; otherwise Telegram will not deliver unmentioned follow-up messages during an active
session.

Get the numeric user and group IDs, then configure Donations:

```dotenv
DEVOPS_TELEGRAM_BOT_TOKEN=...
DEVOPS_TELEGRAM_ALLOWED_USER_IDS=123456789
DEVOPS_TELEGRAM_CHAT_IDS=-1001234567890
DEVOPS_SESSION_TIMEOUT_SECONDS=60
SOPHIE_DEVOPS_API_URL=http://127.0.0.1:8001
SOPHIE_DEVOPS_API_TOKEN_FILE=/srv/secrets/sophie-devops-api-token
SOPHIE_DEVOPS_API_TIMEOUT_SECONDS=1250
```

Start the dedicated headless Compose from Sophie first. Then start this isolated Gateway
Compose project:

```bash
docker compose --env-file .env.devops -f docker-compose.devops.yml up -d --build
```

This separate Compose lifecycle prevents a Donations deploy from restarting the Gateway that
is waiting for its result. Host networking lets the Gateway reach the Sophie API bound to
loopback without publishing it. The existing Donations moderation webhook and the personal
Sophie Telegram process are not changed.

The forced-command wrapper and complete server setup are maintained in the Sophie project:
`docs/headless_devops_service.md`.

На постоянном сервере рутинная системная настройка выполняется из Sophie одной командой:

```bash
./install_devops.sh
```

Скрипт не запускает Donations update или production deploy.
