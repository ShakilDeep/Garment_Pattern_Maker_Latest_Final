import AxeBuilder from '@axe-core/playwright';
import {expect, test} from '@playwright/test';
import {openGeneratedDemo} from './demo';

test('dialogs are named, trap keyboard focus and return focus', async ({page, request}) => {
  await openGeneratedDemo(page, request);
  const help = page.getByRole('button', {name: 'Help', exact: true});
  await help.click();
  const dialog = page.getByRole('dialog', {name: 'Workspace guide'});
  await expect(dialog).toBeVisible();
  await page.keyboard.press('Tab');
  await expect(dialog.getByRole('button', {name: 'Close dialog'})).toBeFocused();
  await page.keyboard.press('Shift+Tab');
  await expect(dialog.getByRole('button', {name: 'Close dialog'})).toBeFocused();
  await page.keyboard.press('Escape');
  await expect(dialog).not.toBeVisible();
  await expect(help).toBeFocused();
});

test('pattern pieces are keyboard-selectable cards that report their selection', async ({page, request}) => {
  await openGeneratedDemo(page, request);
  await page.goto('/#' + encodeURIComponent('Pattern Studio'));
  const card = page.getByRole('button', {name: 'Select back YK', exact: true});
  await card.focus();
  await page.keyboard.press('Enter');
  await expect(card).toHaveAttribute('aria-pressed', 'true');
  await expect(page.getByRole('region', {name: 'Measure back YK'})).toBeVisible();
});

test('all workflow screens pass automated WCAG A and AA checks', async ({page, request}, info) => {
  test.setTimeout(180000);
  await openGeneratedDemo(page, request);
  for (const destination of ['Measurements', 'Requirements', 'Project Dashboard', 'Validation Center',
    'Pattern Studio', 'Grading', 'Marker Nesting', 'Export']) {
    await page.goto('/#' + encodeURIComponent(destination));
    await expect(page.locator('main')).toBeVisible();
    await expect(page.getByRole('button', {name: 'Ask AI', exact: true})).toBeVisible();
    const results = await new AxeBuilder({page})
      .withTags(['wcag2a', 'wcag2aa', 'wcag21a', 'wcag21aa', 'wcag22aa']).analyze();
    await info.attach(destination + '-axe.json', {body: JSON.stringify(results, null, 2), contentType: 'application/json'});
    expect.soft(results.violations.map(v=>({id:v.id,nodes:v.nodes.map(n=>({target:n.target,reason:n.failureSummary}))})), destination).toEqual([]);
  }
});
