import {test,expect} from '@playwright/test';
import path from 'node:path';

test('customer workflow, persistence, sizes, marker, export and responsive review',async({page})=>{
 test.setTimeout(90000); const errors:string[]=[];page.on('pageerror',e=>errors.push(e.message));
 await page.goto('/');
 await expect(page.getByRole('dialog').or(page.getByRole('button',{name:'Ask AI',exact:true}))).toBeVisible();
 const initialDialog=page.getByRole('button',{name:'Close dialog'});
 if(await initialDialog.isVisible())await initialDialog.click();
 await page.getByRole('button',{name:'New project',exact:true}).click();
 await page.getByLabel('Project name').fill('Browser QA shirt');
 await page.getByRole('button',{name:'Start from source files'}).click();
 await page.getByRole('button',{name:'Upload XLSX',exact:true}).click();
 await page.getByLabel('Browse files').setInputFiles(path.resolve('../references/Book2(4).xlsx'));
 await expect(page.getByText('Document imported.',{exact:false})).toBeVisible();
 await page.getByLabel('Browse files').setInputFiles(path.resolve('../references/1078983(5).pdf'));
 await page.getByRole('button',{name:'Manual Entry',exact:true}).click();
 await expect(page.getByLabel('Chest Circumference')).toHaveValue('112.0');
 await page.locator('.sidebar nav').getByRole('button',{name:/Requirements/}).click();
 for(const name of ['Values are in cm','Use client 1078375 block','Use the block reference values (From block)','I reviewed the measurements','Use workbook (3 cm)']){
  await page.getByRole('button',{name,exact:true}).click();
  await expect(page.getByRole('button',{name:'Confirmed: '+name,exact:true})).toBeDisabled();
 }
 await page.getByRole('button',{name:'Generate M Pattern',exact:true}).click();
 await expect(page.getByText('Pattern Pieces (7)',{exact:true})).toBeVisible();
 await page.getByRole('button',{name:'Dismiss notification'}).click();
 await page.screenshot({path:'../artifacts/qa/measurements-1536x1024.png',fullPage:false});
 await page.setViewportSize({width:1366,height:768});
 await page.screenshot({path:'../artifacts/qa/desktop-1366x768.png',fullPage:true});
 expect(await page.evaluate(()=>document.documentElement.scrollWidth<=window.innerWidth)).toBe(true);
 await page.setViewportSize({width:1536,height:1024});
 await page.getByRole('button',{name:'Go to Pattern Studio',exact:true}).click();
 await page.getByRole('button',{name:'Select FRT',exact:true}).click();
 await expect(page.getByRole('region',{name:'Selected piece inspector'}).getByText('Cut quantity',{exact:true})).toBeVisible();
 const studio=page.getByRole('region',{name:'Project pattern pieces'});
 await expect(studio.locator('[data-layer="cut"]')).toHaveCount(7);
 await expect(studio.locator('[data-layer="notches"]')).toHaveCount(2);
 await expect(studio.getByText('back YK · cut 2, on fold',{exact:true})).toBeVisible();
 await studio.getByLabel('Cut line').uncheck();
 await expect(studio.locator('[data-layer="cut"]')).toHaveCount(0);
 await expect(studio.getByRole('region',{name:'Measure FRT'})).toBeVisible();
 await studio.getByRole('button',{name:'Select Sleeve',exact:true}).click();
 const tool=studio.getByRole('region',{name:'Measure Sleeve'});
 await tool.getByLabel('Measurement').selectOption('path');
 await tool.getByLabel('Edge').selectOption('UA_back:cap_crown');
 await tool.getByRole('button',{name:'Measure'}).click();
 await expect(tool.getByLabel('Measurement result')).toHaveText(/^\d+\.\d\d cm$/);
 await studio.getByRole('button',{name:'Walk sleeve cap'}).click();
 await expect(studio.getByRole('region',{name:'Sleeve cap walk'})).toContainText('Cap ease');
 await expect(page.getByRole('region',{name:'Block viewer (1078375)'})).toHaveCount(0);
 // Generated at M only: the Optitex download grades every size first, then saves the zip (no "Grade every size" error).
 const zip=page.waitForEvent('download');
 await studio.getByRole('button',{name:'Download graded DXF-AAMA + RUL'}).click();
 expect((await zip).suggestedFilename()).toBe('shirt_1078375_graded_aama.zip');
 await expect(page.getByText('All 6 sizes graded; download ready.',{exact:true})).toBeVisible();
 await page.screenshot({path:'../artifacts/qa/pattern-studio.png',fullPage:true});
 await page.getByLabel('Chest Circumference').fill('117');
 await page.getByRole('button',{name:'Save Measurements',exact:true}).click();
 await expect(page.getByText('Measurements changed.',{exact:false})).toBeVisible();
 await page.locator('.sidebar nav').getByRole('button',{name:/Requirements/}).click();
 await page.getByRole('button',{name:'I reviewed the measurements',exact:true}).click();
 await page.getByRole('button',{name:'Generate M Pattern',exact:true}).click();
 await page.getByRole('button',{name:'Grading',exact:false}).first().click();
 await page.getByRole('button',{name:'Generate all sizes',exact:true}).click();
 await expect(page.getByText('6 of 6 sizes generated.',{exact:false})).toBeVisible();
 await page.screenshot({path:'../artifacts/qa/grading.png',fullPage:true});
 await page.getByRole('button',{name:'Marker Nesting',exact:false}).first().click();
 await page.getByRole('button',{name:'Optimize marker',exact:true}).click();
 await expect(page.getByText(/% utilization$/).first()).toBeVisible();
 await page.screenshot({path:'../artifacts/qa/marker.png',fullPage:true});
 await page.getByRole('button',{name:'Export',exact:false}).first().click();
 await page.reload();
 // Startup always opens the Projects picker (startup.ts); the saved project and the #Export page must survive the reload.
 await page.getByRole('button',{name:'Close dialog'}).click();
 await page.getByLabel('Project',{exact:true}).selectOption({label:'Browser QA shirt'});
 await expect(page.getByText('Export Center',{exact:true})).toBeVisible();
 await page.setViewportSize({width:390,height:844});
 await page.screenshot({path:'../artifacts/qa/mobile.png',fullPage:true});
 expect(await page.evaluate(()=>document.documentElement.scrollWidth<=window.innerWidth)).toBe(true);
 expect(errors).toEqual([]);
});


