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
 await page.getByLabel('Upload source file').setInputFiles(path.resolve('../references/Book2(4).xlsx'));
 await expect(page.getByText('Document imported.',{exact:false})).toBeVisible();
 await page.getByLabel('Upload source file').setInputFiles(path.resolve('../references/1078983(5).pdf'));
 await page.getByRole('button',{name:'Manual Entry',exact:true}).click();
 await expect(page.getByLabel('Chest Circumference')).toHaveValue('116');
 await page.locator('.sidebar nav').getByRole('button',{name:/Requirements/}).click();
 for(const name of ['Values are in cm','Use demo drafting profile','I reviewed the measurements','Use workbook (3 cm)']){
  await page.getByRole('button',{name,exact:true}).click();
  await expect(page.getByRole('button',{name:'Confirmed: '+name,exact:true})).toBeDisabled();
 }
 await page.getByRole('button',{name:'Generate M Pattern',exact:true}).click();
 await expect(page.getByText('Pattern Pieces (8)',{exact:true})).toBeVisible();
 await page.getByRole('button',{name:'Dismiss notification'}).click();
 await page.screenshot({path:'../artifacts/qa/measurements-1536x1024.png',fullPage:false});
 await page.setViewportSize({width:1366,height:768});
 await page.screenshot({path:'../artifacts/qa/desktop-1366x768.png',fullPage:true});
 expect(await page.evaluate(()=>document.documentElement.scrollWidth<=window.innerWidth)).toBe(true);
 await page.setViewportSize({width:1536,height:1024});
 await page.getByRole('button',{name:'Go to Pattern Studio',exact:true}).click();
 await page.getByRole('button',{name:'Select Front',exact:true}).click();
 await expect(page.getByText('Cut quantity',{exact:true})).toBeVisible();
 await page.getByRole('button',{name:'Zoom in',exact:true}).click();
 await expect(page.getByRole('button',{name:'110%',exact:false})).toBeVisible();
 await page.getByRole('button',{name:'Fit all',exact:true}).click();
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
 for(const kind of ['SVG','PDF','JSON']){
  const pending=page.waitForEvent('download');
  await page.getByRole('button',{name:'Download '+kind,exact:true}).click();
  const download=await pending;await download.saveAs(path.resolve('../artifacts/qa/demo.'+kind.toLowerCase()));
 }
 await page.reload();
 await expect(page.getByText('Export Center',{exact:true})).toBeVisible();
 await page.setViewportSize({width:390,height:844});
 await page.screenshot({path:'../artifacts/qa/mobile.png',fullPage:true});
 expect(await page.evaluate(()=>document.documentElement.scrollWidth<=window.innerWidth)).toBe(true);
 expect(errors).toEqual([]);
});


