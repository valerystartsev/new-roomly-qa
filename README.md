# Тестовое задание для QA Engineer

Тестируемая страница: <https://rcsi-science.github.io/demo-roomly/>

Каркас для автоматизации находится в корне репозитория.

## Задача

Проверьте одностраничную форму бронирования переговорной комнаты вручную и автоматизированно.

Ориентир — до двух часов на проверку и автоматизацию после настройки окружения. Если не успеваете, сдайте выполненную часть и укажите, что осталось.

Подготовьте:

1. Приоритетный чек-лист.
2. До пяти наиболее значимых дефектов: условия, шаги, ожидаемый и фактический результат, приоритет и его обоснование. Добавьте доказательства, если они помогают воспроизведению.
3. Три теста на Python + Playwright: позитивный, негативный и проверка одного найденного дефекта.
4. Вопросы и допущения по требованиям, проверенные области, риски и ограничения проверки.
5. Инструкцию запуска автотестов, версии ОС и браузера, итог выполнения и затраченное время.

Готовый smoke-тест из каркаса в три теста не входит. Автотест дефекта должен проверять корректное ожидаемое поведение и использовать `xfail(strict=True, reason="BUG-01: ...", raises=AssertionError)`. Не маскируйте ошибки окружения как ожидаемые дефекты и не исправляйте приложение.

## Запуск автотестов

Для запуска нужен Docker с Docker Compose v2. Python и браузер отдельно устанавливать не нужно.

Из корня репозитория выполните:

```bash
docker compose run --build --rm tests
```

Команда соберёт тестовый образ, установит зависимости и запустит smoke-тест вместе с тестами кандидата. Результаты сохраняются в каталоге `artifacts/`:

- `artifacts/junit.xml` — отчёт о выполнении;
- `artifacts/browser/` — скриншоты и trace при падении тестов.

Если Docker недоступен, зависимости можно установить вручную:

```bash
python -m pip install -r requirements.txt
python -m playwright install chromium
python -m pytest
```

## Ожидаемое поведение

- «Малая» — до 4 участников, «Средняя» — до 10, «Большая» — до 20.
- Дата не может быть в прошлом; для текущего дня нельзя выбрать прошедшее время.
- Время окончания позже начала, длительность от 30 минут до 4 часов.
- Участников от 1 до 20 и не больше вместимости выбранной комнаты.
- Переговорная, дата, начало, окончание, количество участников, имя и рабочая почта обязательны.
- Электронная почта имеет корректный формат.
- При корректном заполнении показывается сообщение с комнатой, датой, временем и именем заявителя.
- Данные не отправляются и не сохраняются после перезагрузки.

## Использование ИИ

ИИ разрешён. Укажите, использовали ли вы его, для каких задач и какие части результата подготовили самостоятельно. На встрече потребуется объяснить решения и внести небольшое изменение в тест.

## Что передать

Ссылку на репозиторий с тестами, инструкцией запуска и результатами ручной проверки. Не включайте `.venv`, установленные браузеры и зависимости.

## Подготовленные материалы

- [Чек-лист и результаты проверки](docs/manual_test_plan.md)
- [Отчёты о дефектах](docs/bug_reports.md)
- [Автотесты и результаты их запуска](docs/automated_tests.md)
- [Итог проверки, вопросы и ограничения](docs/qa_report.md)

## TypeScript Playwright suite

The independent TypeScript suite in `tests-ts/` mirrors the Python booking and smoke scenarios. It uses Chromium and reports BUG-01 as an expected failure; an unexpected pass fails the run so the marker can be reviewed. Environment and setup failures are not marked as expected.

Run the TypeScript suite in its own container:

```bash
docker compose -f compose.typescript.yaml run --build --rm tests-ts
```

The default target is the published page. Set `BASE_URL` to test another address reachable from the container. The JUnit report and browser artifacts are written to `artifacts-ts/`, separate from Python reports.

The container runs as UID and GID 1000 by default so it can write reports for a typical Linux user. If your IDs differ, pass them as `TEST_UID=$(id -u) TEST_GID=$(id -g)` before the Docker Compose command.

For a local run, install Node.js dependencies and the browser, then run the tests and type check:

```bash
npm ci
npx playwright install chromium
npm run test:ts
npm run typecheck
```

For example, run `python -m http.server 8000` in another terminal and set `BASE_URL=http://localhost:8000/` when running the tests locally. `localhost` inside a Docker container refers to the container itself.

## Java Playwright suite

The independent Java 21, Maven, JUnit 5 and Playwright suite in `java/` mirrors the Python and TypeScript booking and smoke scenarios. JUnit has no built-in strict xfail: the known BUG-01 assertion aborts the test with its reason (reported as skipped), while an unexpected pass or an unrelated error fails the run.

Run it in a separate container:

```bash
docker compose -f compose.java.yaml run --build --rm tests-java
```

The target defaults to the published page; set `BASE_URL` to use another address reachable from the container. Maven's JUnit XML and text reports are written to `artifacts-java/`. The container uses UID and GID 1000 by default; if needed, set `TEST_UID=$(id -u) TEST_GID=$(id -g)` before the command.

For a local run with Java 21 and Maven, install the matching Chromium once, then run the suite:

```bash
mvn -f java/pom.xml test-compile exec:java -Dexec.mainClass=com.microsoft.playwright.CLI -Dexec.args="install chromium" -Dexec.classpathScope=test
mvn -f java/pom.xml test
```
