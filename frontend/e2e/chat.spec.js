// Chat flows through the real backend and seeded database.
// The scripted LLM always replies "Scripted test reply.", so these tests check
// the data the tools return, not the wording.

import { expect, test } from '@playwright/test';

async function ask(page, question) {
  await page.getByRole('textbox', { name: 'Ask a question' }).fill(question);
  await page.getByRole('button', { name: 'Send' }).click();
}

test.beforeEach(async ({ page }) => {
  await page.goto('/');
  await expect(page.getByRole('heading', { name: 'How can I help?' })).toBeVisible();
});

test('degree audit shows the seed student\'s progress', async ({ page }) => {
  await ask(page, 'What do I still need to graduate?');

  const chat = page.getByRole('region', { name: 'Chat' });
  await expect(chat.getByText('Degree audit')).toBeVisible();
  // Seed: 30 of 36 credits completed (83%).
  await expect(chat.getByRole('progressbar', { name: 'Degree progress' }))
    .toHaveAttribute('aria-valuenow', '83');
  // exact, so "36 credits remaining" (an anonymous audit) can't match.
  await expect(chat.getByText('6 credits remaining', { exact: true })).toBeVisible();

  const stillRequired = chat.locator('section', {
    has: page.getByRole('heading', { name: 'Still required' }),
  });
  await expect(stillRequired.getByText('MSSE 692')).toBeVisible();
  await expect(stillRequired.getByText('MSSE 696')).toBeVisible();
});

test('course question shows the course from the catalog', async ({ page }) => {
  await ask(page, 'Tell me about MSSE 635');

  await expect(
    page.getByRole('region', { name: 'Chat' }).getByText('Software Architecture and Design'),
  ).toBeVisible();
});

test('out-of-scope question is redirected', async ({ page }) => {
  await ask(page, 'Can I get more financial aid?');

  const chat = page.getByRole('region', { name: 'Chat' });
  await expect(chat.getByText('Scripted test reply.')).toBeVisible();
  // The student's question stays on screen above the reply.
  await expect(chat.getByText('Can I get more financial aid?')).toBeVisible();
});
