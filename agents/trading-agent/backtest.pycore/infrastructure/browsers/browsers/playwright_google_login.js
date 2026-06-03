const { chromium } = require('playwright');
const path   = require('path');
const os     = require('os');

const userDataDir = path.join(os.homedir(), '.browser-profile', 'google');

(async () => {
  console.log(`🚀 Launching Chromium with persistent profile at ${userDataDir}`);

  const context = await chromium.launchPersistentContext(userDataDir, {
    headless: false,                         // show the browser so you can log in
    args: [
      '--disable-blink-features=AutomationControlled',
      '--disable-features=IsolateOrigins,site-per-process'
    ],
    userAgent: 'Mozilla/5.0 (X11; Linux x86_64) AppleWebKit/537.36 ' +
               '(KHTML, like Gecko) Chrome/124.0.0.0 Safari/537.36'
  });

  const page = await context.newPage();
  await page.goto('https://accounts.google.com/signin');

  console.log('\n🔑 Please log in to your Google account in the opened window.');
  console.log('After you have successfully logged in, press ENTER in this terminal to close the browser and save the session.\n');

  // Wait for you to hit Enter
  const stdin = process.stdin;
  stdin.setRawMode(true);
  stdin.resume();
  stdin.on('data', () => {
    console.log('\n👍 Closing browser…');
    context.close().then(() => process.exit(0));
  });
})();