import AxeBuilder from '@axe-core/playwright';
import {expect, test} from '@playwright/test';
import {openGeneratedDemo} from './demo';

const PIECES = ['FRT', 'back', 'back YK', 'CLR', 'BND TOP', 'BND IN', 'Sleeve'];

test('the 1078375 block is drafted, its layers toggle, and measure and walk show backend values', async ({page, request}) => {
  test.setTimeout(120000);
  await openGeneratedDemo(page, request);
  await page.goto('/#' + encodeURIComponent('Pattern Studio'));
  const viewer = page.getByRole('region', {name: 'Block viewer (1078375)'});
  await viewer.getByRole('button', {name: 'Draft 1078375 block'}).click();
  for (const name of PIECES) await expect(viewer.getByRole('button', {name: `Select ${name}`, exact: true})).toBeVisible();
  await expect(viewer.locator('[data-layer="cut"]')).toHaveCount(7);

  await viewer.scrollIntoViewIfNeeded();
  await viewer.screenshot({path: '../artifacts/qa/block-viewer-1078375.png'});
  await viewer.getByLabel('Cut line').uncheck();
  await expect(viewer.locator('[data-layer="cut"]')).toHaveCount(0);
  await expect(viewer.locator('[data-layer="notches"]')).toHaveCount(2);

  await viewer.getByRole('button', {name: 'Select Sleeve', exact: true}).click();
  const tool = viewer.getByRole('region', {name: 'Measure Sleeve'});
  await tool.getByLabel('Measurement').selectOption('path');
  await tool.getByLabel('Edge').selectOption('UA_back:cap_crown');
  await tool.getByRole('button', {name: 'Measure'}).click();
  await expect(tool.getByLabel('Measurement result')).toHaveText(/^28\.4\d cm$/);

  const saved = page.waitForEvent('download');
  await viewer.getByRole('button', {name: 'Download graded DXF-AAMA + RUL'}).click();
  expect((await saved).suggestedFilename()).toBe('shirt_1078375_graded_aama.zip');

  await viewer.getByRole('button', {name: 'Walk sleeve cap'}).click();
  await expect(viewer.getByRole('region', {name: 'Sleeve cap walk'})).toContainText('3.95 cm');  // the backend's L cap ease (PDS 3.929)

  const results = await new AxeBuilder({page}).include('[aria-label="Block viewer (1078375)"]')
    .withTags(['wcag2a', 'wcag2aa', 'wcag21a', 'wcag21aa', 'wcag22aa']).analyze();
  expect(results.violations.map((v) => `${v.id}: ${v.help}`)).toEqual([]);
});
