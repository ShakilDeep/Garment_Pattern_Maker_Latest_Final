import AxeBuilder from '@axe-core/playwright';
import {expect,test} from '@playwright/test';

import {openGeneratedDemo} from './demo';
import {REF004_COLOR_THRESHOLD, REF004_MAX_DIFF_PIXELS} from '../src/visualAcceptance';

test('measurements workspace passes automated WCAG checks',async({page,request},info)=>{
 test.setTimeout(90000);
 await openGeneratedDemo(page,request);
 const result=await new AxeBuilder({page}).withTags(['wcag2a','wcag2aa','wcag21aa','wcag22aa']).analyze();
 await info.attach('measurements-axe.json',{body:JSON.stringify(result,null,2),contentType:'application/json'});
 expect(result.violations.map(v=>({id:v.id,nodes:v.nodes.map(n=>({target:n.target,reason:n.failureSummary}))}))).toEqual([]);
});

test('canonical Measurements workspace tracks REF-004',async({page,request})=>{
 test.setTimeout(90000);
 await openGeneratedDemo(page,request);
 // Ask AI is product chrome outside REF-004; remove only for the pixel lock shot.
 await page.locator('[data-ask-ai], .copilot-launch').evaluateAll(nodes=>nodes.forEach(node=>node.remove()));
 await expect(page).toHaveScreenshot('garment-pattern-maker-v5-ui-reference-1536x1024.png',{
  animations:'disabled',caret:'hide',scale:'css',
  threshold: REF004_COLOR_THRESHOLD,
  maxDiffPixels: REF004_MAX_DIFF_PIXELS,
 });
});
