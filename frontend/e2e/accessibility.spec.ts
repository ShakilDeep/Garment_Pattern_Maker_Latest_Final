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

test('canvas selection is announced and has keyboard pan alternatives', async ({page, request}) => {
  await openGeneratedDemo(page, request);
  const front = page.getByRole('button', {name: 'Select Front', exact: true});
  await front.focus();
  await page.keyboard.press('Enter');
  await expect(page.getByRole('status', {name: 'Canvas status'})).toContainText('Front selected');
  await expect(front).toHaveAttribute('aria-pressed', 'true');
  await page.keyboard.press('ArrowRight');
  await expect(page.getByRole('status', {name: 'Canvas status'})).toContainText('Pan 20, 0');
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
