import { expect, test } from '@playwright/test';

test('booking page is available', async ({ page }) => {
  const response = await page.goto('', { waitUntil: 'domcontentloaded' });
  if (!response?.ok()) {
    throw new Error('Booking page did not load successfully');
  }
  await expect(page.getByRole('button', { name: 'Забронировать' })).toBeVisible();
});
