import {expect,type APIRequestContext,type Page} from '@playwright/test';

export async function openGeneratedDemo(page:Page,request:APIRequestContext){
 const created=await request.post('/api/v1/projects',{data:{name:"Men's Regular Fit Shirt (Demo)",demo:true}});
 expect(created.ok()).toBeTruthy();
 const project=await created.json();
 const base=`/api/v1/projects/${project.id}`;
 for(const [key,value] of [['units','cm'],['profile','demo_v1'],['review','confirmed'],['placket','workbook']]){
  const response=await request.post(`${base}/requirements/${key}/resolve`,{data:{value}});
  expect(response.ok()).toBeTruthy();
 }
 const generated=await request.post(`${base}/patterns/generate`,{data:{size:'M',allowance:1}});
 expect(generated.ok()).toBeTruthy();
 await page.addInitScript(id=>localStorage.setItem('garment-project',id),project.id);
 await page.goto('/#Measurements');
 await expect(page.getByText('Pattern Pieces (8)',{exact:true})).toBeVisible();
 const notification=page.getByRole('button',{name:'Dismiss notification'});
 if(await notification.isVisible())await notification.click();
 await page.evaluate(async()=>{await document.fonts.ready;return true});
}

