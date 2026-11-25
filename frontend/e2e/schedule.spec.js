// Schedule builder: plan the remaining courses, save the draft, export to calendar.
// Relies on e2e/fixtures/future-terms.sql so there are always future terms to plan into.

import { readFile } from 'node:fs/promises';

import { expect, test } from '@playwright/test';

test('builds a schedule and exports it as a calendar file', async ({ page }) => {
  await page.goto('/');
  await page.getByRole('button', { name: 'Schedule', exact: true }).click();

  const dialog = page.getByRole('dialog', { name: 'Your schedule' });
  await expect(dialog).toBeVisible();
  await dialog.getByRole('button', { name: /^(Build|Rebuild) schedule$/ }).click();

  // MSSE 696 needs MSSE 692 first, so they land in different terms.
  const schedule = dialog.getByRole('region', { name: 'Planned schedule' });
  await expect(schedule.getByText('MSSE 692')).toBeVisible();
  await expect(schedule.getByText('MSSE 696')).toBeVisible();

  const downloadPromise = page.waitForEvent('download');
  await dialog.getByRole('button', { name: 'Export to calendar' }).click();
  const download = await downloadPromise;

  expect(download.suggestedFilename()).toBe('coursecompass-schedule.ics');
  const calendar = await readFile(await download.path(), 'utf8');
  expect(calendar).toContain('BEGIN:VCALENDAR');
  expect(calendar).toContain('MSSE 692');
  expect(calendar).toContain('MSSE 696');
});
