import {expect, test} from '@playwright/test';
import {readFile} from 'node:fs/promises';
import {openGeneratedDemo} from './demo';

test('the Export page downloads the pattern as DXF-AAMA (R12, metric mm) for Optitex', async ({page, request}) => {
  await openGeneratedDemo(page, request);
  await page.locator('.sidebar nav').getByRole('button', {name: /Export/}).click();
  const button = page.getByRole('button', {name: 'Download DXF-AAMA (Optitex)'});
  await expect(button).toBeEnabled();
  const [file] = await Promise.all([page.waitForEvent('download'), button.click()]);
  expect(file.suggestedFilename()).toBe('1078983_M_pattern_demo_aama.dxf');
  const text = await readFile(await file.path(), 'utf-8');
  expect(text).toContain('AC1009');
  expect(text).toContain('UNITS: METRIC');
  expect(text).toContain('Piece Name: ');
});
