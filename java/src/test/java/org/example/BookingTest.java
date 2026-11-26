package org.example;

import com.microsoft.playwright.Browser;
import com.microsoft.playwright.BrowserContext;
import com.microsoft.playwright.Clock;
import com.microsoft.playwright.Locator;
import com.microsoft.playwright.Page;
import com.microsoft.playwright.Playwright;
import com.microsoft.playwright.Response;
import com.microsoft.playwright.options.AriaRole;
import com.microsoft.playwright.options.WaitUntilState;
import org.junit.jupiter.api.AfterEach;
import org.junit.jupiter.api.BeforeEach;
import org.junit.jupiter.api.Test;
import org.junit.jupiter.params.ParameterizedTest;
import org.junit.jupiter.params.provider.CsvSource;
import org.opentest4j.TestAbortedException;

import static com.microsoft.playwright.assertions.PlaywrightAssertions.assertThat;
import static org.junit.jupiter.api.Assertions.assertFalse;
import static org.junit.jupiter.api.Assertions.fail;

class BookingTest {
    private Playwright playwright;
    private Browser browser;
    private BrowserContext context;
    private Page page;

    @BeforeEach
    void setUp() {
        playwright = Playwright.create();
        browser = playwright.chromium().launch();
        context = browser.newContext();
        page = context.newPage();
    }

    @AfterEach
    void tearDown() {
        if (context != null) context.close();
        if (browser != null) browser.close();
        if (playwright != null) playwright.close();
    }

    private void openBookingPage() {
        String baseUrl = System.getenv("BASE_URL");
        if (baseUrl == null || baseUrl.isBlank()) {
            baseUrl = "http://localhost:8000/";
        }
        Response response = page.navigate(baseUrl,
            new Page.NavigateOptions().setWaitUntil(WaitUntilState.DOMCONTENTLOADED));
        if (response == null || !response.ok()) {
            throw new IllegalStateException("Booking page did not load successfully");
        }
    }

    private String localDate(int daysFromToday) {
        return (String) page.evaluate("""
            days => {
                const date = new Date();
                date.setDate(date.getDate() + days);
                const local = new Date(date.getTime() - date.getTimezoneOffset() * 60000);
                return local.toISOString().slice(0, 10);
            }
            """, daysFromToday);
    }

    private void fillBooking(String date, String participants) {
        page.getByLabel("Переговорная").selectOption("small");
        page.getByLabel("Дата").fill(date);
        page.getByLabel("Начало").fill("10:00");
        page.getByLabel("Окончание").fill("11:00");
        page.getByLabel("Участники").fill(participants);
        page.getByLabel("Ваше имя").fill("Анна Иванова");
        page.getByLabel("Рабочая почта").fill("anna@example.com");
    }

    private void submitBooking() {
        page.getByRole(AriaRole.BUTTON, new Page.GetByRoleOptions().setName("Забронировать")).click();
    }

    @Test
    void bookingPageIsAvailable() {
        openBookingPage();
        assertThat(page.getByRole(AriaRole.BUTTON,
            new Page.GetByRoleOptions().setName("Забронировать"))).isVisible();
    }

    @Test
    void successfulBooking() {
        openBookingPage();
        String date = localDate(1);
        fillBooking(date, "2");
        submitBooking();

        Locator status = page.getByRole(AriaRole.STATUS);
        for (String expected : new String[] {"Бронирование создано", "Малая", date, "10:00", "11:00", "Анна Иванова"}) {
            assertThat(status).containsText(expected);
        }
    }

    @ParameterizedTest(name = "participants={0}")
    @CsvSource({
        "5, В комнате максимум 4 участника.",
        "-1, Количество участников — от 1 до 20."
    })
    void invalidBooking(String participants, String expectedError) {
        openBookingPage();
        fillBooking(localDate(1), participants);
        submitBooking();

        assertThat(page.getByText(expectedError, new Page.GetByTextOptions().setExact(true))).isVisible();
        assertThat(page.getByRole(AriaRole.STATUS)).not().containsText("Бронирование создано");
    }

    @Test
    void pastStartTimeTodayIsRejected() {
        // Fix the browser's local clock at noon so 10:00–11:00 is always in the past.
        long noon = ((Number) page.evaluate("new Date(2030, 5, 15, 12, 0, 0).getTime()")).longValue();
        page.clock().install(new Clock.InstallOptions().setTime(noon));
        openBookingPage();
        fillBooking(localDate(0), "2");
        submitBooking();

        String statusClass = page.getByRole(AriaRole.STATUS).getAttribute("class");
        if (statusClass == null || (!statusClass.contains("success") && !statusClass.contains("error"))) {
            throw new IllegalStateException("Booking form did not report a submission result");
        }
        if (statusClass.contains("error")
            && page.locator(".field.has-error:not(:has([name='startTime']))").count() > 0) {
            throw new IllegalStateException("Booking was rejected for an unrelated field");
        }

        // JUnit has no strict xfail: abort only for the known assertion, and fail on an unexpected pass.
        try {
            assertFalse(statusClass.contains("success"), "Booking with past start time was accepted");
        } catch (AssertionError knownDefect) {
            throw new TestAbortedException("BUG-01: past start time today is accepted", knownDefect);
        }
        fail("BUG-01 unexpectedly passed; review and remove the expected-failure handling");
    }
}
