from datetime import datetime, timezone

import pytest
from playwright.sync_api import Page, expect


def open_booking_page(page: Page, base_url: str) -> None:
    response = page.goto(base_url, wait_until="domcontentloaded")
    if response is None or not response.ok:
        raise RuntimeError("Booking page did not load successfully")


def local_date(page: Page, days_from_today: int) -> str:
    return page.evaluate(
        """days => {
            const date = new Date();
            date.setDate(date.getDate() + days);
            const local = new Date(date.getTime() - date.getTimezoneOffset() * 60000);
            return local.toISOString().slice(0, 10);
        }""",
        days_from_today,
    )


def fill_booking(page: Page, date: str, participants: str = "2") -> None:
    page.get_by_label("Переговорная").select_option("small")
    page.get_by_label("Дата").fill(date)
    page.get_by_label("Начало").fill("10:00")
    page.get_by_label("Окончание").fill("11:00")
    page.get_by_label("Участники").fill(participants)
    page.get_by_label("Ваше имя").fill("Анна Иванова")
    page.get_by_label("Рабочая почта").fill("anna@example.com")


def submit_booking(page: Page) -> None:
    page.get_by_role("button", name="Забронировать").click()


def test_successful_booking(page: Page, base_url: str):
    open_booking_page(page, base_url)
    date = local_date(page, 1)
    fill_booking(page, date)
    submit_booking(page)

    status = page.get_by_role("status")
    expect(status).to_contain_text("Бронирование создано")
    for expected in ("Малая", date, "10:00", "11:00", "Анна Иванова"):
        expect(status).to_contain_text(expected)


@pytest.mark.parametrize(
    ("participants", "expected_error"),
    [
        pytest.param(
            "5",
            "В комнате максимум 4 участника.",
            id="exceeds-room-capacity",
        ),
        pytest.param(
            "-1",
            "Количество участников — от 1 до 20.",
            id="negative-participants",
        ),
    ],
)
def test_invalid_booking(
    page: Page, base_url: str, participants: str, expected_error: str
):
    open_booking_page(page, base_url)
    fill_booking(page, local_date(page, 1), participants=participants)
    submit_booking(page)

    expect(page.get_by_text(expected_error, exact=True)).to_be_visible()
    expect(page.get_by_role("status")).not_to_contain_text("Бронирование создано")


@pytest.mark.xfail(
    strict=True,
    reason="BUG-01: принимается прошедшее время сегодня",
    raises=AssertionError,
)
def test_discovered_defect(page: Page, base_url: str):
    # Fix the browser's local clock at noon so 10:00–11:00 is always in the past.
    noon = page.evaluate("new Date(2030, 5, 15, 12, 0, 0).getTime()")
    page.clock.install(time=datetime.fromtimestamp(noon / 1000, tz=timezone.utc))
    open_booking_page(page, base_url)
    fill_booking(page, local_date(page, 0))
    submit_booking(page)

    status = page.get_by_role("status")
    status_class = status.get_attribute("class") or ""
    if "success" not in status_class and "error" not in status_class:
        raise RuntimeError("Booking form did not report a submission result")
    if "error" in status_class:
        unexpected_errors = page.locator(
            '.field.has-error:not(:has([name="startTime"]))'
        ).count()
        if unexpected_errors:
            raise RuntimeError("Booking was rejected for an unrelated field")
    assert "success" not in status_class, "Booking with past start time was accepted"
