import { expect, Page, test } from '@playwright/test';

async function openBookingPage(page: Page): Promise<void> {
  const response = await page.goto('', { waitUntil: 'domcontentloaded' });
  if (!response?.ok()) {
    throw new Error('Booking page did not load successfully');
  }
}

async function localDate(page: Page, daysFromToday: number): Promise<string> {
  return page.evaluate((days) => {
    const date = new Date();
    date.setDate(date.getDate() + days);
    const local = new Date(date.getTime() - date.getTimezoneOffset() * 60_000);
    return local.toISOString().slice(0, 10);
  }, daysFromToday);
}

async function fillBooking(page: Page, date: string, participants = '2'): Promise<void> {
  await page.getByLabel('Переговорная').selectOption('small');
  await page.getByLabel('Дата').fill(date);
  await page.getByLabel('Начало').fill('10:00');
  await page.getByLabel('Окончание').fill('11:00');
  await page.getByLabel('Участники').fill(participants);
  await page.getByLabel('Ваше имя').fill('Анна Иванова');
  await page.getByLabel('Рабочая почта').fill('anna@example.com');
}

async function submitBooking(page: Page): Promise<void> {
  await page.getByRole('button', { name: 'Забронировать' }).click();
}

test('successful booking', async ({ page }) => {
  await openBookingPage(page);
  const date = await localDate(page, 1);
  await fillBooking(page, date);
  await submitBooking(page);

  const status = page.getByRole('status');
  for (const expected of ['Бронирование создано', 'Малая', date, '10:00', '11:00', 'Анна Иванова']) {
    await expect(status).toContainText(expected);
  }
});

for (const { name, participants, expectedError } of [
  { name: 'exceeds room capacity', participants: '5', expectedError: 'В комнате максимум 4 участника.' },
  { name: 'negative participants', participants: '-1', expectedError: 'Количество участников — от 1 до 20.' },
]) {
  test(`invalid booking: ${name}`, async ({ page }) => {
    await openBookingPage(page);
    await fillBooking(page, await localDate(page, 1), participants);
    await submitBooking(page);

    await expect(page.getByText(expectedError, { exact: true })).toBeVisible();
    await expect(page.getByRole('status')).not.toContainText('Бронирование создано');
  });
}

test('BUG-01: booking with a past start time today is rejected', async ({ page }) => {
  // Fix the browser's local clock at noon so 10:00–11:00 is always in the past.
  const noon = await page.evaluate(() => new Date(2030, 5, 15, 12).getTime());
  await page.clock.install({ time: noon });
  await openBookingPage(page);
  await fillBooking(page, await localDate(page, 0));
  await submitBooking(page);

  const statusClass = (await page.getByRole('status').getAttribute('class')) ?? '';
  if (!statusClass.includes('success') && !statusClass.includes('error')) {
    throw new Error('Booking form did not report a submission result');
  }
  if (statusClass.includes('error')) {
    const unexpectedErrors = await page.locator('.field.has-error:not(:has([name="startTime"]))').count();
    if (unexpectedErrors) {
      throw new Error('Booking was rejected for an unrelated field');
    }
  }

  // Mark only the known assertion as an expected failure; setup errors must fail the test.
  test.fail(true, 'BUG-01: past start time today is accepted');
  expect(statusClass).not.toContain('success');
});
