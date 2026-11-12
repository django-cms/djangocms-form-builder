const { test, expect } = require('@playwright/test');
const fs = require('node:fs');
const path = require('node:path');
const root = path.join(__dirname, '.generated');

test.beforeEach(async ({ page }) => {
    await page.route('http://forms.test/**', async (route) => {
        const file = path.join(root, new URL(route.request().url()).pathname);
        if (!fs.existsSync(file)) return route.fulfill({ status: 404 });
        return route.fulfill({
            contentType: file.endsWith('.js') ? 'application/javascript'
                : file.endsWith('.css') ? 'text/css' : 'text/html',
            body: fs.readFileSync(file),
        });
    });
});

async function openForm(page, fixture = 'basic') {
    await page.goto(`http://forms.test/${fixture}.html`);
    await page.waitForFunction(() => customElements.get('django-formset'));
    await page.locator('input[name="name"]').fill('Test User');
}

for (const fixture of ['basic', 'custom', 'prefix']) {
    test(`${fixture}: Enter submits local JSON field names and replaces the form`, async ({ page }) => {
        let payload;
        await page.route('**/@form-builder/1', async (route) => {
            payload = route.request().postDataJSON();
            await route.fulfill({ json: { content: '<p>Thank you!</p>' } });
        });
        await openForm(page, fixture);
        await page.locator('input[name="name"]').press('Enter');
        await expect(page.getByText('Thank you!')).toBeVisible();
        expect(payload.formset_data).toEqual({ name: 'Test User', email: '' });
    });
}

test('requestSubmit sends exactly one request', async ({ page }) => {
    let requests = 0;
    await page.route('**/@form-builder/1', async (route) => {
        requests++;
        await route.fulfill({ json: { content: '<p>Thank you!</p>' } });
    });
    await openForm(page);
    await page.locator('form').evaluate((form) => form.requestSubmit());
    await expect(page.getByText('Thank you!')).toBeVisible();
    expect(requests).toBe(1);
});

test('browser constraints prevent requests without showing a server error', async ({ page }) => {
    let requests = 0;
    await page.route('**/@form-builder/1', async () => { requests++; });
    await openForm(page);
    await page.locator('input[name="name"]').fill('');
    await page.locator('[data-djangocms-form-builder-submit]').click();
    await expect(page.locator('.dj-field-errors')).toContainText(['This field is required.']);
    await expect(page.locator('[data-djangocms-form-builder-error]')).toBeHidden();
    expect(requests).toBe(0);
});

for (const status of [403, 500]) {
    test(`${status}: visible feedback, focus, and retry`, async ({ page }) => {
        let attempts = 0;
        await page.route('**/@form-builder/1', async (route) => {
            attempts++;
            if (attempts === 1) return route.fulfill({ status, contentType: 'text/html', body: 'Error' });
            return route.fulfill({ json: { content: '<p>Thank you!</p>' } });
        });
        await openForm(page);
        const button = page.locator('[data-djangocms-form-builder-submit]');
        await button.click();
        const error = page.locator('[data-djangocms-form-builder-error]');
        await expect(error).toBeVisible();
        await expect(error).toContainText(status === 403 ? 'Reload this page' : 'Network connection');
        await expect(error).toBeFocused();
        await expect(button).toBeEnabled();
        await button.click();
        await expect(page.getByText('Thank you!')).toBeVisible();
        expect(attempts).toBe(2);
    });
}

test('422 displays field and non-field errors without a generic server error', async ({ page }) => {
    await page.route('**/@form-builder/1', (route) => route.fulfill({
        status: 422, json: { name: ['Name unavailable'], __all__: ['Please login'] },
    }));
    await openForm(page);
    await page.locator('[data-djangocms-form-builder-submit]').click();
    await expect(page.locator('.dj-field-errors')).toContainText(['Name unavailable']);
    await expect(page.locator('.dj-form-errors')).toContainText('Please login');
    await expect(page.locator('[data-djangocms-form-builder-error]')).toBeHidden();
    await expect(page.locator('[data-djangocms-form-builder-submit]')).toBeEnabled();
});

test('network failure is visible and leaves the form ready for retry', async ({ page }) => {
    // django-formset itself alerts on fetch failure; our persistent feedback must also appear.
    page.on('dialog', (dialog) => dialog.dismiss());
    await page.route('**/@form-builder/1', (route) => route.abort());
    await openForm(page);
    await page.locator('[data-djangocms-form-builder-submit]').click();
    await expect(page.locator('[data-djangocms-form-builder-error]')).toBeVisible();
    await expect(page.locator('[data-djangocms-form-builder-submit]')).toBeEnabled();
});

test('malformed success JSON is visible and leaves the form ready for retry', async ({ page }) => {
    await page.route('**/@form-builder/1', (route) => route.fulfill({ body: 'invalid JSON' }));
    await openForm(page);
    await page.locator('[data-djangocms-form-builder-submit]').click();
    await expect(page.locator('[data-djangocms-form-builder-error]')).toBeVisible();
    await expect(page.locator('[data-djangocms-form-builder-submit]')).toBeEnabled();
});

for (const size of ['invisible', 'normal']) {
    test(`reCAPTCHA ${size}: fallback obtains and preserves token until POST`, async ({ page }) => {
        await page.addInitScript(() => {
            let options, response = '';
            window.grecaptcha = {
                render(element, opts) {
                    options = opts;
                    const field = document.createElement('textarea');
                    field.name = 'g-recaptcha-response';
                    field.className = 'g-recaptcha-response';
                    element.append(field);
                    return 0;
                },
                execute() { response = 'verified-token'; options.callback(response); },
                getResponse() { return response; },
                reset() {
                    response = '';
                    document.querySelector('.g-recaptcha-response').value = '';
                },
            };
        });
        await page.route('https://www.google.com/recaptcha/api.js**', (route) => route.fulfill({
            contentType: 'application/javascript', body: 'reCaptchaOnLoadCallback();',
        }));
        let posted;
        await page.route('**/@form-builder/1', async (route) => {
            if (route.request().method() === 'GET') {
                return route.fulfill({ json: { csrf_token: 'fresh-token' } });
            }
            posted = route.request().postData();
            return route.fulfill({ json: { result: 'success', content: '<p>Thank you!</p>' } });
        });
        await page.goto('http://forms.test/captcha.html');
        await expect(page.locator('django-formset')).toHaveCount(0);
        await expect(page.locator('script[src*="recaptcha/api.js"]')).toHaveCount(1);
        const button = page.locator('input[type="submit"]');
        await expect(button).toBeEnabled();
        await page.locator('input[name="name"]').fill('Test User');
        if (size === 'normal') {
            await page.locator('.g-recaptcha').evaluate((element) => { element.dataset.size = 'normal'; });
            await button.click();
            await expect(page.locator('.all-invalid')).toContainText('Please complete the CAPTCHA.');
            expect(posted).toBeUndefined();
            await page.evaluate(() => grecaptcha.execute());
        }
        await button.click();
        await expect(page.getByText('Thank you!')).toBeVisible();
        expect(posted).toContain('verified-token');
    });
}
