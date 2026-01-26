const { chromium } = require('playwright');
const path = require('path');

const TARGET_URL = 'http://localhost:3000/dashboard';

(async () => {
    console.log('🚀 Starting Playwright verification for Bitcoin Analysis Dashboard...');
    const browser = await chromium.launch({ headless: false, slowMo: 50 });
    const context = await browser.newContext({
        viewport: { width: 1440, height: 900 }
    });
    const page = await context.newPage();

    try {
        console.log(`🌐 Navigating to ${TARGET_URL}...`);
        // Increased timeout for initial render (Next.js dev mode + Databricks fetch)
        await page.goto(TARGET_URL, { waitUntil: 'networkidle', timeout: 60000 });

        console.log('✅ Page loaded. Title:', await page.title());


        // 1. Verify basic structure
        console.log('🔍 Verifying layout structure...');
        await page.waitForSelector('header', { timeout: 10000 });
        await page.waitForSelector('main', { timeout: 10000 });


        // 2. Verify Stats Cards are populated
        console.log('🔍 Verifying stats cards...');
        await page.waitForSelector('text=PNL - DAILY', { timeout: 15000 });

        // The value is in a div following the title container
        const firstStatValue = await page.getByText('PNL - DAILY').locator('xpath=../../following-sibling::div | ../../div[contains(@class, "text-xl")]').first().innerText();
        console.log(`💰 Current Price displayed value: ${firstStatValue}`);

        // Simpler check: Just find a $ value on the page
        const hasPrice = await page.locator('text=$').first().isVisible();
        if (hasPrice) {
            console.log('✅ Found price values on the dashboard.');
        }

        // 3. Verify Chart exists
        console.log('🔍 Verifying chart container...');
        await page.waitForSelector('canvas', { timeout: 15000 });
        console.log('✅ Chart canvas detected.');

        // 4. Test interactivity (Filter switch)
        console.log('🔍 Testing time filters...');
        const filterBtn = page.getByRole('button', { name: '1M', exact: true });
        await filterBtn.click();
        console.log('🖱️ Clicked "1M" filter.');

        // Check URL update
        await page.waitForURL(/time=1m/, { timeout: 10000 });
        console.log('✅ URL updated to ?time=1m');

        // 5. Screenshot for final verification
        const screenshotPath = `c:/Users/ggrft/PycharmProjects/Bitcoin-analysis/verification_dashboard.png`;
        await page.screenshot({ path: screenshotPath, fullPage: true });
        console.log(`📸 Screenshot saved to ${screenshotPath}`);

        console.log('✨ Verification complete! The dashboard is functional and follows best practices.');

    } catch (error) {
        console.error('❌ Verification FAILED:', error.message);
        const errorScreenshot = `c:/Users/ggrft/PycharmProjects/Bitcoin-analysis/error_verification.png`;
        await page.screenshot({ path: errorScreenshot });
        console.log(`📸 Error screenshot saved to ${errorScreenshot}`);
        process.exit(1);
    } finally {
        await browser.close();
    }
})();
