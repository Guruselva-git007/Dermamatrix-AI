async page => {
  await page.setViewportSize({width:1440,height:1000});await page.context().clearCookies();
  const checks=[];const errors=[];page.on('pageerror',error=>errors.push(error.message));
  await page.goto('http://127.0.0.1:8001/');
  await page.waitForSelector('#authGate.show');
  await page.locator('#continueGuestButton').click();
  await page.waitForFunction(()=>!document.querySelector('#authGate').classList.contains('show'));
  if(await page.locator('#welcomeDialog').evaluate(e=>e.open))await page.locator('#closeWelcome').click();
  await page.locator('[data-page-nav=learn]').click();await page.waitForSelector('.learn-row');checks.push('guest education');
  await page.locator('[data-page-nav=home]').click();
  if(!await page.locator('#imageConsent').isVisible())throw Error('Assessment consent missing');
  checks.push('assessment entry');
  for(const width of [390,768,1440]){await page.setViewportSize({width,height:900});if(!await page.evaluate(()=>document.documentElement.scrollWidth<=innerWidth))throw Error('Horizontal overflow');}
  checks.push('responsive shell');
  if(errors.length)throw Error('Uncaught browser exception');
  return{checks,errors};
}
