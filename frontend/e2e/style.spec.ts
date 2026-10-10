import AxeBuilder from '@axe-core/playwright';
import {expect, test} from '@playwright/test';

// A 1×1 PNG: the offline detector proposes nothing, so the image content does not matter here.
const FLAT = {name: 'flat.png', mimeType: 'image/png', buffer: Buffer.from(
  'iVBORw0KGgoAAAANSUhEUgAAAAEAAAABCAIAAACQd1PeAAAADElEQVR4nGP4//8/AAX+Av4N70a4AAAAAElFTkSuQmCC', 'base64')};

test('an image is read offline, the user picks each option and confirms the style', async ({page}) => {
  await page.goto('/');
  const initialDialog = page.getByRole('button', {name: 'Close dialog'});
  if (await initialDialog.isVisible()) await initialDialog.click();
  await page.getByRole('button', {name: 'New project', exact: true}).click();
  await page.getByLabel('Project name').fill('Style QA');
  await page.getByRole('button', {name: 'Start from source files'}).click();
  await page.getByRole('button', {name: 'Upload XLSX', exact: true}).click();
  const style = page.getByRole('region', {name: 'Garment style'});
  await style.getByLabel('Detect style from image').setInputFiles(FLAT);
  await expect(style.getByText('Proposed by local', {exact: false})).toBeVisible();
  await expect(style.getByRole('button', {name: 'Confirm style'})).toBeDisabled();
  const results = await new AxeBuilder({page}).include('.style-detect')
    .withTags(['wcag2a', 'wcag2aa', 'wcag21a', 'wcag21aa', 'wcag22aa']).analyze();
  expect(results.violations.map((v) => v.id)).toEqual([]);

  await style.getByLabel('Garment type').selectOption('pant');
  await expect(style.getByLabel('Sleeve')).toHaveCount(0);
  await style.getByLabel('Leg').selectOption('wide');
  await expect(style.getByText('Your choice', {exact: true})).toHaveCount(2);
  await style.getByRole('button', {name: 'Confirm style'}).click();
  await expect(style.getByText('Confirmed pant style is stored.')).toBeVisible();
  await page.reload();  // startup opens the Projects picker; the confirmed style must survive the reload
  await page.getByRole('button', {name: 'Close dialog'}).click();
  await page.getByLabel('Project', {exact: true}).selectOption({label: 'Style QA'});
  await page.getByRole('button', {name: 'Upload XLSX', exact: true}).click();
  await expect(page.getByRole('region', {name: 'Garment style'}).getByLabel('Leg')).toHaveValue('wide');
});
