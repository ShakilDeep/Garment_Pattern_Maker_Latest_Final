import {expect,type APIRequestContext,type Page} from '@playwright/test';

export async function openGeneratedDemo(page:Page,request:APIRequestContext){
 const created=await request.post('/api/v1/projects',{data:{name:"Men's Regular Fit Shirt (Demo)",demo:true}});
 expect(created.ok()).toBeTruthy();
 const project=await created.json();
 const base=`/api/v1/projects/${project.id}`;
 for(const [key,value] of [['units','cm'],['profile','shirt_1078375'],['block_reference','accepted'],['review','confirmed'],['placket','workbook']]){
  const response=await request.post(`${base}/requirements/${key}/resolve`,{data:{value}});
  expect(response.ok()).toBeTruthy();
 }
 // The base is L, as on the 1078375 PDS (the accuracy checks compare it with the PDS); M, the page's size, is graded.
 const generated=await request.post(`${base}/patterns/generate`,{data:{size:'L'}});
 expect(generated.ok()).toBeTruthy();
 expect((await request.post(`${base}/grade`,{data:{sizes:['M']}})).ok()).toBeTruthy();
 // Startup always opens the Projects picker (startup.ts); close it and choose this run's project by id.
 await page.goto('/#Measurements');
 await page.getByRole('button',{name:'Close dialog'}).click();
 await page.getByLabel('Project',{exact:true}).selectOption(project.id);
 await expect(page.getByText('Pattern Pieces (7)',{exact:true})).toBeVisible();
 const notification=page.getByRole('button',{name:'Dismiss notification'});
 if(await notification.isVisible())await notification.click();
 await page.evaluate(async()=>{await document.fonts.ready;return true});
}

