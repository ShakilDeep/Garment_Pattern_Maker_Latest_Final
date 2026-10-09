import AxeBuilder from '@axe-core/playwright';
import {expect, test} from '@playwright/test';
import path from 'node:path';

const WORKBOOK = path.resolve('../fixtures/import_samples/unmapped_pom.xlsx');

test('unknown POM rows are suggested, confirmed or marked not used on the mapping screen', async ({page}) => {
  await page.goto('/');
  const initialDialog = page.getByRole('button', {name: 'Close dialog'});
  if (await initialDialog.isVisible()) await initialDialog.click();
  await page.getByRole('button', {name: 'New project', exact: true}).click();
  await page.getByLabel('Project name').fill('Mapping QA');
  await page.getByRole('button', {name: 'Start from source files'}).click();
  await page.getByRole('button', {name: 'Upload XLSX', exact: true}).click();
  await page.getByLabel('Browse files').setInputFiles(WORKBOOK);
  const mapping = page.getByRole('region', {name: 'POM mapping'});
  await expect(mapping.getByText('2 rows need a canonical measurement', {exact: false})).toBeVisible();

  await mapping.getByRole('button', {name: 'Suggest mappings'}).click();
  await expect(mapping.getByText('Suggested by local', {exact: false})).toBeVisible();
  await expect(mapping.getByLabel('Canonical key for INSEAM ALONG SEAM')).toHaveValue('inseam');
  const results = await new AxeBuilder({page}).include('.mapping-table')
    .withTags(['wcag2a', 'wcag2aa', 'wcag21a', 'wcag21aa', 'wcag22aa']).analyze();
  expect(results.violations.map((v) => v.id)).toEqual([]);

  await mapping.getByRole('button', {name: 'Confirm INSEAM ALONG SEAM'}).click();
  await expect(mapping.getByText('1 row needs a canonical measurement', {exact: false})).toBeVisible();
  await mapping.getByRole('button', {name: 'Mark MYSTERY POINT not used'}).click();
  await expect(mapping.getByText('Every row is mapped.')).toBeVisible();
  await mapping.getByLabel('Show all 3 rows').check();
  await expect(mapping.getByRole('button', {name: 'Mark MYSTERY POINT not used'})).toBeDisabled();
  await expect(mapping.locator('.mapping-not_used')).toHaveText('Not used');
});
