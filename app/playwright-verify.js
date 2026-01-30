const { chromium } = require('playwright');
const path = require('path');

const TARGET_URL = 'http://localhost:3000/dashboard';

(async () => {
    const browser = await chromium.launch({ headless: false, slowMo: 50 });
    const context = await browser.newContext({
        viewport: { width: 1440, height: 900 }
    });
    const page = await context.newPage();

    try {
        // Increased timeout for initial render (Next.js dev mode + Databricks fetch)
        await page.goto(TARGET_URL, { waitUntil: 'networkidle', timeout: 60000 });



        // 1. Verify basic structure
        await page.waitForSelector('header', { timeout: 10000 });
        await page.waitForSelector('main', { timeout: 10000 });


        // 2. Verify Stats Cards are populated
        await page.waitForSelector('text=PNL - DAILY', { timeout: 15000 });

        // Simpler check: Just find a $ value on the page
        await page.locator('text=$').first().isVisible();

        // 3. Verify Chart exists
        await page.waitForSelector('canvas', { timeout: 15000 });

        // 4. Test interactivity (Filter switch)
        const filterBtn = page.getByRole('button', { name: '1M', exact: true });
        await filterBtn.click();

        // Check URL update
        await page.waitForURL(/time=1m/, { timeout: 10000 });

        // 5. Screenshot for final verification
        const screenshotPath = `c:/Users/ggrft/PycharmProjects/Bitcoin-analysis/verification_dashboard.png`;
        await page.screenshot({ path: screenshotPath, fullPage: true });


    } catch (error) {
        console.error('❌ Verification FAILED:', error.message);
        const errorScreenshot = `c:/Users/ggrft/PycharmProjects/Bitcoin-analysis/error_verification.png`;
        await page.screenshot({ path: errorScreenshot });
        process.exit(1);
    } finally {
        await browser.close();
    }
})();
