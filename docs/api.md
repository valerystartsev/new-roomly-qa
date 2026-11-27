# API Roomly

Документ описывает маршруты, реализованные в [app/main.py](../app/main.py). Базовый путь API — `/api/v1`. При локальном запуске из Compose базовый адрес обычно `http://localhost:8001`. Интерактивная документация OpenAPI доступна по `/docs`, схема — по `/openapi.json`. Интерфейс учётных записей расположен по `/account/` и не является частью API.

Маршруты для бронирований, доступности и ремонта пока **не реализованы**. Их предполагаемое назначение приведено отдельно в [ТЗ](room-booking-specification.md).

## Аутентификация и CSRF

1. Вызовите `POST /api/v1/sessions` с JSON и сохраните cookie `roomly_session`, полученную в `Set-Cookie`.
2. Для запросов, изменяющих данные после входа, передавайте полученный `csrf_token` в заголовке `X-CSRF-Token` вместе с cookie.
3. Чтобы восстановить информацию о сессии после перезагрузки страницы, вызовите `GET /api/v1/sessions/current` с cookie. Этот запрос **создаёт новый CSRF-токен и отменяет прежний** для этой сессии; клиент должен заменить сохранённый токен. Это влияет и на другие вкладки, использующие ту же cookie.

Cookie имеет флаги `HttpOnly`, `SameSite=Strict` и срок восемь часов. Флаг `Secure` включён по умолчанию в коде, а локальная конфигурация Compose по умолчанию отключает его для HTTP. Сессия действительна только для активного пользователя. Права проверяются на сервере. Почтовый сервис не используется.

Объект пользователя в ответах:

```json
{"id": 1, "email": "user@example.test", "display_name": "Example User", "role": "user"}
```

## Маршруты

| Метод и путь | Доступ | Назначение | Успех |
| --- | --- | --- | --- |
| `GET /api/v1/health` | Без входа | Проверяет соединение с БД запросом `SELECT 1`. | `200`, `{"status":"ok"}` |
| `POST /api/v1/sessions` | Без входа | Вход, создание сессии и CSRF-токена. | `200`, объект пользователя и `csrf_token`; cookie сессии |
| `GET /api/v1/sessions/current` | Пользователь | Текущий пользователь и новый CSRF-токен. | `200`, объект пользователя и `csrf_token` |
| `DELETE /api/v1/sessions/current` | Пользователь, CSRF | Выход из текущей сессии. | `200`, `{"ok":true}` |
| `GET /api/v1/users/me` | Пользователь | Данные текущего пользователя. | `200`, объект пользователя |
| `POST /api/v1/users/me/change-password` | Пользователь, CSRF | Смена собственного пароля. | `200`, `{"ok":true}` |
| `GET /api/v1/offices` | Пользователь | Все офисы, включая неактивные. | `200`, массив офисов |
| `GET /api/v1/offices/{office_id}/rooms` | Пользователь | Все комнаты офиса, включая неактивные. | `200`, массив комнат |
| `GET /api/v1/offices/{office_id}/equipment` | Пользователь | Всё оборудование офиса, включая неактивное. | `200`, массив оборудования |
| `POST /api/v1/admin/offices` | Администратор, CSRF | Создание офиса: `name`, `timezone`. | `201`, офис |
| `POST /api/v1/admin/rooms` | Администратор, CSRF | Создание комнаты: `office_id`, `name`, `category`, `capacity`. | `201`, комната |
| `POST /api/v1/admin/equipment` | Администратор, CSRF | Создание устройства: `office_id`, `label`, `type`. | `201`, устройство |
| `PATCH /api/v1/admin/offices/{office_id}` | Администратор, CSRF | Изменение `name`, `timezone`, `active`. | `200`, офис |
| `PATCH /api/v1/admin/rooms/{room_id}` | Администратор, CSRF | Изменение `name`, `category`, `capacity`, `active`. | `200`, комната |
| `PATCH /api/v1/admin/equipment/{equipment_id}` | Администратор, CSRF | Изменение `label`, `active`. | `200`, устройство |
| `GET /api/v1/admin/users` | Администратор | Все пользователи, отсортированные по ID; пагинации пока нет. | `200`, массив объектов пользователей |
| `POST /api/v1/admin/users` | Администратор, CSRF | Создание пользователя или администратора. | `201`, объект созданного пользователя |
| `POST /api/v1/admin/users/{user_id}/reset-password` | Администратор, CSRF | Сброс пароля указанного пользователя. | `200`, `{"ok":true}` |

## Тела запросов и правила

### Вход

`POST /api/v1/sessions`:

```json
{"email": "user@example.test", "password": "<password>"}
```

Адрес очищается от пробелов по краям и приводится к нижнему регистру. Ответ содержит поля `user` и `csrf_token`. Вход ограничен десятью попытками с одного IP за последние 60 секунд; учитываются и успешные попытки. Ограничитель хранится в памяти отдельного процесса и не подходит для совместного ограничения между несколькими экземплярами приложения.

### Создание пользователя

`POST /api/v1/admin/users`:

```json
{"email": "user@example.test", "display_name": "Example User", "password": "<new-password>", "role": "user"}
```

- `email` — строка до 254 символов; после нормализации должна соответствовать проверке формата и быть уникальной. Существование почтового адреса и владение им не проверяются.
- `display_name` — строка от 1 до 120 символов, после удаления пробелов по краям не должна быть пустой.
- `password` — строка от 12 до 256 символов.
- `role` — `user` или `admin`; при отсутствии используется `user`.

### Смена и сброс пароля

`POST /api/v1/users/me/change-password`:

```json
{"current_password": "<current-password>", "new_password": "<new-password>"}
```

`POST /api/v1/admin/users/{user_id}/reset-password`:

```json
{"password": "<new-password>"}
```

Новый пароль должен содержать от 12 до 256 символов. После успешной смены или сброса удаляются **все сессии** соответствующего пользователя, включая текущую; для дальнейшей работы требуется новый вход. Сброс не отправляет письмо.

## Ошибки

Ошибки, заданные приложением, имеют вид `{"detail":"..."}`. Ошибки проверки входных данных FastAPI могут содержать в `detail` массив объектов с расположением поля и описанием ошибки. Текущая реализация ещё не предоставляет единый структурированный код ошибки, предусмотренный ТЗ.

| Код | Примеры причин |
| --- | --- |
| `400` | Неверный текущий пароль при смене. |
| `401` | Неверные данные входа, отсутствие или истечение сессии, неактивный пользователь. |
| `403` | Неверный или отсутствующий CSRF-токен, недостаточно прав. |
| `404` | Пользователь для сброса пароля не найден. |
| `409` | Адрес почты уже существует при предварительной проверке создания пользователя. |
| `422` | Ошибка схемы запроса или проверок данных пользователя. |
| `429` | Превышено ограничение попыток входа. |
| `500` | Необработанная ошибка сервера, например недоступная БД. |

## Локальная проверка

Для практической проверки можно использовать интерактивную страницу `/docs` либо интерфейс `/account/`. OpenAPI UI не управляет CSRF автоматически, поэтому защищённые изменения требуют вручную передать токен, полученный после входа. Не сохраняйте реальные пароли в истории команд или файлах проекта.

## Resource administration

Names and labels are trimmed and must be nonempty; room capacity must be a positive integer. Office time zones are validated against the server's IANA time zone database. Category is `small`, `medium`, or `large`; equipment type is `projector` or `speakerphone`. An equipment unit's type and office, and a room's office, cannot be changed after creation. Duplicate names or labels within the relevant unique scope return 409.

Deactivation preserves records and is rejected if the resource has a current or future active allocation already present in the database. Creating resources in an inactive office and reactivating its rooms or equipment return 409. Booking creation and its coordination with deactivation will be implemented in stage 6; the current check alone does not protect against a future concurrent booking implementation.
