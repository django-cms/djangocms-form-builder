const { defineConfig } = require('@playwright/test');
module.exports = defineConfig({
    testDir: './tests/browser',
    testMatch: '*.spec.cjs',
    use: { headless: true },
    reporter: 'list',
});
