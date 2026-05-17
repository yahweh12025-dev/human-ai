const { chromium } = require('playwright');
const path = require('path');
const os = require('os');

const userDataDir = path.join(os.homedir(), '.browser-profile/google');

(async () => {
  console.log(`Launching Chromium with persistent profile at ${userDataDir}`);
  const context = await chromium.launchPersistentContext(userDataDir, {
    headless: false,
  });
  const page = await context.newPage();
  await page.goto('https://accounts.google.com/signin');
  console.log('Please log in to your Google account in the opened window.');
  console.log('After you have successfully logged in, press ENTER in this terminal to close the browser and save the session.');
  // Wait for user to press Enter
  const stdin = process.openStdin();
  stdin.addListener('data', () => {
    console.log('Closing browser...');
    context.close().then(() => process.exit(0));
  });
})();
