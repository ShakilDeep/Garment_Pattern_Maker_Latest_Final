import {expect, test} from '@playwright/test';
import {openGeneratedDemo} from './demo';

test('failed generation recovers without losing measurements', async ({page, request}) => {
  await openGeneratedDemo(page, request);
  await page.route('**/patterns/generate', route => route.fulfill({status:503,
    contentType:'application/json', body:JSON.stringify({code:'UNAVAILABLE',message:'Generation temporarily unavailable'})}));
  await page.getByRole('button', {name:'Regenerate Pattern',exact:true}).click();
  await expect(page.getByRole('alert')).toContainText('Generation temporarily unavailable');
  await expect(page.getByLabel('Chest Circumference')).toHaveValue('116');
  await page.unroute('**/patterns/generate');
  await page.getByRole('button', {name:'Regenerate Pattern',exact:true}).click();
  await expect(page.getByRole('status').filter({hasText:'Demo pattern generated'})).toBeVisible();
});

test('mixed-size marker submits cut order and announces completion', async ({page, request}) => {
  test.setTimeout(90000);
  await openGeneratedDemo(page, request);
  await page.locator('.sidebar nav').getByRole('button', {name:/Grading/}).click();
  await page.getByRole('button', {name:'Generate all sizes',exact:true}).click();
  await expect(page.getByText('6 of 6 sizes generated.', {exact:false})).toBeVisible();
  await page.locator('.sidebar nav').getByRole('button', {name:/Marker Nesting/}).click();
  await page.getByLabel('Combine sizes').check();
  await page.getByLabel('S garment quantity').fill('2');
  await page.getByLabel('L garment quantity',{exact:true}).fill('1');
  const submitted = page.waitForRequest(r => r.url().endsWith('/markers/generate'));
  await page.getByRole('button', {name:'Optimize marker',exact:true}).click();
  expect((await submitted).postDataJSON().quantities).toEqual({S:2,L:1});
  await expect(page.getByRole('status', {name:'Marker status'})).toContainText('Marker complete');
  await expect(page.getByRole('status', {name:'Marker status'})).toContainText('48 pieces');
});
