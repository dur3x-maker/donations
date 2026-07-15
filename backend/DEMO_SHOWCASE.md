# Демо-витрина `demo_showcase_v1`

CLI создаёт 8 активных и 3 завершённых истории, 8 демо-авторов, подтверждённые пожертвования и платежи, подписки, обновления, итоговые отчёты, активности, уведомления и локальные изображения. Схема БД и API не меняются.

## Защита данных

- По умолчанию выполняется только dry-run. Изменения возможны лишь с `--apply`.
- `APP_ENV` разрешён только для local/development/test/staging. `production`, неизвестное окружение и БД с production-подобным именем блокируются.
- Маркер набора — UUIDv5 от строки `demo_showcase_v1:<entity>:<key>` в фиксированном namespace. Заголовки для определения набора не используются.
- Импорт защищён PostgreSQL advisory lock и выполняется одной транзакцией. При ошибке БД откатывается; изменённые файлы восстанавливаются.
- Повторный обычный `--apply` не создаёт дубли. `--replace-existing` удаляет и создаёт заново только кампании с вычисляемыми UUID `demo_showcase_v1`.
- Демо-пользователи при replace не удаляются: это сохраняет возможные созданные вручную действия этих аккаунтов вне витрины. Их пароль обновляется через штатный Argon2-хешер только из `DEMO_USERS_PASSWORD`.
- Конфликт UUID, email, username или другой незавершённый сбор демо-автора останавливает всю транзакцию.

## Связи, участвующие в очистке

Удаление выбранной кампании охватывает реальные связи схемы:

- `contributions` → `payments`;
- `campaign_updates` → `campaign_update_photos`;
- `campaign_completion_reports` → `campaign_completion_photos`;
- `campaign_subscriptions`;
- `activities`;
- `reports`;
- `suspicious_flags`;
- `telegram_moderation_sessions`;
- `notifications` удаляются CLI явно, потому что их FK использует `ON DELETE SET NULL`.

`user_achievements` и `bank_account_applications` привязаны к пользователю, а не к кампании, поэтому replace их не удаляет. Пользовательские данные, не попавшие в явный список UUID, не затрагиваются.

## Изображения

Исходные JPG шириной до 1200 px лежат в `demo_assets/demo_showcase_v1/images`. Источник, автор, лицензия и SHA-256 каждого файла записаны в `demo_assets/demo_showcase_v1/manifest.json`.

Во время apply файлы с проверкой контрольной суммы атомарно копируются в:

```text
/app/uploads/demo_showcase_v1
```

В Docker Compose это постоянный volume `backend_uploads:/app/uploads`, поэтому файлы сохраняются после пересборки контейнера. В БД записываются публичные URL вида `<DEMO_PUBLIC_BASE_URL>/uploads/demo_showcase_v1/<file>`.

Фотографии Unsplash иллюстративные и не изображают героев вымышленных историй. Это также указано в тексте каждой кампании.

## Локальный запуск

Из каталога `backend`:

```bash
python -m scripts.import_demo_showcase --dry-run
DEMO_USERS_PASSWORD='<temporary-secret>' python -m scripts.import_demo_showcase --apply
DEMO_USERS_PASSWORD='<temporary-secret>' python -m scripts.import_demo_showcase --apply
DEMO_USERS_PASSWORD='<temporary-secret>' python -m scripts.import_demo_showcase --apply --replace-existing
```

Не записывайте реальный пароль в команду или env-файл. Пример выше показывает только интерфейс CLI; для сервера используйте безопасный ввод ниже.

## Test/staging: backup и импорт

Проект использует доступный на стенде `docker-compose`.

1. Создать backup до deploy или любых изменений:

```bash
mkdir -p backups
backup="backups/donations_$(date +%Y%m%d_%H%M%S).dump"
docker-compose exec -T postgres sh -lc 'pg_dump -U "$POSTGRES_USER" -d "$POSTGRES_DB" -Fc' > "$backup"
test -s "$backup" && ls -lh "$backup"
```

2. Доставить код штатным Git/deploy-процессом. После появления кода на сервере пересобрать сервисы без удаления volumes:

```bash
docker-compose up -d --build backend frontend
docker-compose ps
```

3. Убедиться, что `APP_ENV=staging` (или `test`) и публичный origin задан корректно:

```bash
docker-compose exec -T backend sh -lc 'printf "APP_ENV=%s\nDEMO_PUBLIC_BASE_URL=%s\n" "$APP_ENV" "$DEMO_PUBLIC_BASE_URL"'
```

4. Проверить план без пароля и без изменений:

```bash
docker-compose exec -T backend python -m scripts.import_demo_showcase --dry-run
```

5. Ввести пароль без сохранения значения в shell history, выполнить apply и сразу удалить переменную:

```bash
read -rsp 'DEMO_USERS_PASSWORD: ' DEMO_USERS_PASSWORD && echo
export DEMO_USERS_PASSWORD
docker-compose exec -T -e DEMO_USERS_PASSWORD backend python -m scripts.import_demo_showcase --apply
unset DEMO_USERS_PASSWORD
```

6. Повторный apply должен сообщить `existing=11`, `missing=0` и не менять количество записей:

```bash
read -rsp 'DEMO_USERS_PASSWORD: ' DEMO_USERS_PASSWORD && echo
export DEMO_USERS_PASSWORD
docker-compose exec -T -e DEMO_USERS_PASSWORD backend python -m scripts.import_demo_showcase --apply
unset DEMO_USERS_PASSWORD
```

7. Для плановой пересборки только маркированного набора сначала посмотреть replace dry-run, затем отдельно применить:

```bash
docker-compose exec -T backend python -m scripts.import_demo_showcase --dry-run --replace-existing
read -rsp 'DEMO_USERS_PASSWORD: ' DEMO_USERS_PASSWORD && echo
export DEMO_USERS_PASSWORD
docker-compose exec -T -e DEMO_USERS_PASSWORD backend python -m scripts.import_demo_showcase --apply --replace-existing
unset DEMO_USERS_PASSWORD
```

## Старые немаркированные кампании

CLI не определяет старые записи по заголовку. Для локальной БД найденные кандидаты вынесены в `demo_assets/demo_showcase_v1/legacy_cleanup_candidates.local.json`. Файл никогда не читается автоматически.

До подтверждения разрешён только просмотр:

```bash
python -m scripts.import_demo_showcase \
  --dry-run --replace-existing \
  --legacy-campaign-ids-file demo_assets/demo_showcase_v1/legacy_cleanup_candidates.local.json
```

После отдельного подтверждения точного списка удаление требует одновременно всех флагов:

```bash
DEMO_USERS_PASSWORD='<temporary-secret>' python -m scripts.import_demo_showcase \
  --apply --replace-existing \
  --legacy-campaign-ids-file demo_assets/demo_showcase_v1/legacy_cleanup_candidates.local.json \
  --confirm-legacy-cleanup
```

Без `--confirm-legacy-cleanup` транзакция не начинается.

## Проверка результата

```bash
docker-compose exec -T backend alembic check
docker-compose exec -T backend sh -lc 'test "$(find uploads/demo_showcase_v1 -maxdepth 1 -type f | wc -l)" -eq 11'
curl -fsS https://test.digitalgardens.online/api/v1/campaigns >/dev/null
curl -fsS https://test.digitalgardens.online/api/v1/campaigns/completed >/dev/null
```

Дополнительно вручную проверить каталог, публичные профили, загрузку изображений и вход под каждым указанным ниже email. Активная история владельца должна редактироваться, завершённая — возвращать конфликт жизненного цикла.

Полный backend-suite запускается в локальном/CI test-окружении с `requirements-test.txt` и отдельной PostgreSQL `TEST_DATABASE_URL`; production/staging БД для pytest не используется.
