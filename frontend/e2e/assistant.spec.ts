import AxeBuilder from '@axe-core/playwright';
import {expect,test} from '@playwright/test';
import {openGeneratedDemo} from './demo';

test('assistant explains the selected CAD piece and restores keyboard focus',async({page,request})=>{
  await openGeneratedDemo(page,request);
  await page.getByRole('button',{name:'Select Front',exact:true}).click();
  await page.getByRole('button',{name:'Ask AI',exact:true}).click();
  const panel=page.getByRole('complementary',{name:'AI assistant'});
  await expect(panel.getByRole('textbox',{name:'Ask AI'})).toBeFocused();
  await panel.getByRole('button',{name:'Explain selected piece'}).click();
  await expect(panel.locator('.assistant-answer')).toContainText('Front:');
  await expect(panel.locator('.assistant-answer')).toContainText('cut quantity 2');
  await expect(panel.locator('pre')).toHaveCount(0);
  const result=await new AxeBuilder({page}).include('.copilot').withTags(['wcag2a','wcag2aa','wcag21aa']).analyze();
  expect(result.violations).toEqual([]);
  await page.screenshot({path:'../artifacts/qa/assistant-selected-piece.png'});
  await page.keyboard.press('Escape');
  await expect(page.getByRole('button',{name:'Ask AI',exact:true})).toBeFocused();
});
