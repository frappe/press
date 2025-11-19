import { test, expect, Page } from '@playwright/test';
import crypto from 'crypto';

function fetchProductTrials(): string[] {
  const raw = process.env.PRODUCT_TRIALS || '';
  const products = raw.split(',').map(s => s.trim()).filter(Boolean);
  if (!products.length) {
    throw new Error('Set PRODUCT_TRIALS (comma separated) to run signup E2E tests.');
  }
  return products;
}

// Per-product timeout (default 5m) and optional inactivity watchdog (env overrides)
const PER_PRODUCT_TIMEOUT_MS = parseInt(process.env.SIGNUP_PER_PRODUCT_TIMEOUT_MS || '300000', 10); // 5 minutes default
const INACTIVITY_LIMIT_MS = parseInt(process.env.SIGNUP_INACTIVITY_MS || '0', 10); // disabled by default

function testEmail(product: string) {
  const rand = crypto.randomBytes(3).toString('hex');
  return `fc-signup-test+${product}_${rand}@frappemail.com`;
  // return `playwright_${product}_${rand}@signup.test`;
}

async function runSignupFlow(page: Page, product: string) {
  const flowStart = Date.now();
  let lastActivity = Date.now();
  function remaining() { return PER_PRODUCT_TIMEOUT_MS - (Date.now() - flowStart); }
  function touch(label: string) { lastActivity = Date.now(); /* lightweight marker */ }
  function ensureTime(label: string) {
    if (remaining() <= 0) {
      throw new Error(`Per-product timeout (${PER_PRODUCT_TIMEOUT_MS}ms) exceeded at phase: ${label}`);
    }
    if (INACTIVITY_LIMIT_MS > 0 && Date.now() - lastActivity > INACTIVITY_LIMIT_MS) {
      throw new Error(`Inactivity > ${INACTIVITY_LIMIT_MS}ms detected at phase: ${label}`);
    }
  }
  async function runStep<T>(label: string, fn: () => Promise<T>, stepCap?: number): Promise<T> {
    ensureTime(label + ':before');
    const budget = remaining();
    const timeoutCap = Math.min(stepCap || budget, budget);
    touch(label + ':start');
    const result = await Promise.race([
      fn(),
      page.waitForTimeout(timeoutCap).then(() => {
        throw new Error(`Step timeout (${label}) after ${timeoutCap}ms (remaining budget exhausted or step slow)`);
      })
    ]);
    touch(label + ':done');
    ensureTime(label + ':after');
    return result;
  }
  // optional simple inactivity watcher (non-fatal; enforce via ensureTime on steps)
  if (INACTIVITY_LIMIT_MS > 0) {
    (async () => {
      while (remaining() > 0) {
        await page.waitForTimeout(Math.min(5000, Math.max(1000, INACTIVITY_LIMIT_MS / 4)));
        if (Date.now() - lastActivity > INACTIVITY_LIMIT_MS) {
          // Force a failure by triggering ensureTime on next step; or throw here if desired
          throw new Error(`Inactivity watcher: no activity for ${INACTIVITY_LIMIT_MS}ms in product ${product}`);
        }
      }
    })().catch(err => console.warn('[signup.spec] inactivity watcher error', err?.message));
  }

  const email = testEmail(product.toLowerCase().replace(/\s+/g, '-'));
  await runStep('goto', () => page.goto(`/dashboard/signup?product=${encodeURIComponent(product)}`));
  await runStep('wait-form', () => page.waitForSelector('form', { timeout: Math.min(30000, remaining()) }));
  await runStep('wait-email-selectors', () => page.waitForSelector([
    'button:has-text("Sign up with email")',
    'input[type="email"]',
    'input[name*="email" i]',
    'input[placeholder*="email" i]'
  ].join(', '), { timeout: Math.min(45_000, remaining()) }));

  // Prefer explicitly labeled input if present; else fall back to broader selector.
  let emailInput = page.getByLabel(/email/i).first();
  if (!(await emailInput.count())) {
    emailInput = page.locator('input[type="email"], input[name*="email" i], input[placeholder*="email" i]').first();
  }
  await runStep('email-visible', () => emailInput.waitFor({ state: 'visible', timeout: Math.min(15_000, remaining()) }));
  await runStep('email-fill', () => emailInput.fill(email));
  let accountRequestId: string | undefined;
  await runStep('signup-submit-and-response', () => Promise.all([
    (async () => {
      const resp = await page.waitForResponse(
        (r) => r.url().includes('press.api.account.signup') && r.status() === 200,
      );
      try {
        const data = await resp.json();
        accountRequestId = data.message as string;
      } catch (e) {
        // ignore
      }
    })(),
    (async () => {
      // slight delay to allow any debounce / validation to finish before submitting signup
      await page.waitForTimeout(400);
      await page.getByRole('button', { name: /sign up with email/i }).click();
    })(),
  ]));

  const otpHelper = process.env.OTP_HELPER_ENDPOINT;
  let code: string | undefined;
  if (!accountRequestId) {
    throw new Error('Signup response did not return account_request id. Cannot fetch OTP.');
  }
  if (otpHelper) {
    try {
      const baseHost = new URL(process.env.BASE_URL || 'http://localhost:8010').hostname;
      const otpRes = await fetch(`${otpHelper}?account_request=${encodeURIComponent(accountRequestId)}`, {
        headers: { 'X-Frappe-Site-Name': baseHost }
      });
      const txt = await otpRes.text();
      if (otpRes.ok) {
        try {
          const json = JSON.parse(txt);
          code = json.message || json.code || json.otp;
        } catch { /* parse error ignored */ }
      }
      if (!code) {
        console.warn(`[signup.spec] OTP helper did not return code (status ${otpRes.status}). Falling back to 111111.`);
      }
    } catch (e) {
      console.warn(`[signup.spec] OTP fetch error ${(e as Error).message}. Falling back to 111111.`);
    }
  } else {
    console.warn('[signup.spec] OTP_HELPER_ENDPOINT not set; using fallback OTP 111111.');
  }
  if (!code) {
    code = '111111';
  }

  await runStep('fill-otp', () => page.getByLabel(/verification code/i).fill(code!));
  await runStep('verify-otp', () => Promise.all([
    page.waitForResponse((r) => r.url().includes('press.api.account.verify_otp') && r.status() === 200),
    page.getByRole('button', { name: /verify/i }).click(),
  ]));

  await runStep('post-verify-redirect', () => page.waitForURL(/.*\/dashboard\/(setup-account|saas|create-site)\//, { timeout: Math.min(60_000, remaining()) }));

  if (page.url().includes('/dashboard/setup-account/')) {
    await Promise.race([
      page.waitForSelector('form button:has-text("Create account")', { timeout: 30000 }).catch(() => null),
      page.waitForSelector('input[name="fname"], label:has-text("First name"), label:has-text("First Name")', { timeout: 30000 }).catch(() => null),
    ]);

    const firstName = page.locator('input[name="fname"]');
    const lastName = page.locator('input[name="lname"]');

    if (await firstName.count()) {
      await firstName.first().waitFor({ state: 'visible', timeout: 10000 }).catch(() => null);
      const val = await firstName.first().inputValue().catch(() => '');
      if (!val) {
        await firstName.first().fill('Playwright').catch(() => null);
      }
    }
    if (await lastName.count()) {
      await lastName.first().waitFor({ state: 'visible', timeout: 10000 }).catch(() => null);
      const val = await lastName.first().inputValue().catch(() => '');
      if (!val) {
        await lastName.first().fill('Tester').catch(() => null);
      }
    }

    const countryLabel = page.getByLabel(/country/i).first();
    if (await countryLabel.count()) {
      try {
        const tag = await countryLabel.evaluate(el => el.tagName.toLowerCase()).catch(() => '');
        if (tag === 'select') {
          const current = await countryLabel.inputValue().catch(() => '');
          if (!current) {
            await countryLabel.selectOption({ label: 'India' }).catch(() => null);
          }
        } else {
          const existing = await countryLabel.inputValue().catch(() => '');
          if (!existing) {
            await countryLabel.click({ timeout: 5000 }).catch(() => null);
            const indiaOption = page.locator('text=/^India$/');
            if (await indiaOption.count()) {
              await indiaOption.first().click({ timeout: 5000 }).catch(() => null);
            }
          }
        }
      } catch { /* ignore */ }
    }
    await runStep('create-account', () => Promise.all([
      page.waitForURL(/.*\/dashboard\/(saas|create-site)\//, { timeout: Math.min(60_000, remaining()) }),
      (async () => { await page.waitForTimeout(400); await page.getByRole('button', { name: /create account/i }).click(); })(),
    ]));
  }

  expect(page.url()).toMatch(/dashboard\/(saas|create-site)\//);

  if (/\/dashboard\/create-site\/[^/]+\/setup/.test(page.url())) {
    const siteInput = page.locator('form input');
  await runStep('site-input-visible', () => siteInput.first().waitFor({ state: 'visible', timeout: Math.min(15000, remaining()) }));
    let currentVal = (await siteInput.first().inputValue().catch(() => ''))?.trim();
    if (!currentVal) {
      const base = product.toLowerCase().replace(/[^a-z0-9]+/g, '-').replace(/^-+|-+$/g, '').slice(0, 15) || 'site';
      currentVal = `${base}-pw${crypto.randomBytes(2).toString('hex')}`.slice(0, 32);
      await siteInput.first().fill(currentVal);
    }
    let siteSubdomain = currentVal; // will re-read just before submission for any frontend normalization
    let domainSuffix = '';
    try {
      const domainEl = page.locator('form .flex.cursor-default').filter({ hasText: /^\.[a-z0-9.-]+$/i }).first();
      if (await domainEl.count()) {
        const raw = (await domainEl.innerText()).trim();
        domainSuffix = raw.replace(/^\./, '');
      }
    } catch { /* ignore */ }
  const createSiteDelay = 500;
    if (createSiteDelay > 0) await page.waitForTimeout(createSiteDelay);
    try {
      const latestVal = (await siteInput.first().inputValue()).trim();
      if (latestVal) siteSubdomain = latestVal;
    } catch { /* ignore */ }
    const originHost = new URL(page.url()).host;
    const context = page.context();
    const popupPromise = context.waitForEvent('page').catch(() => null);
    await runStep('create-site-submit', () => Promise.all([
      page.waitForResponse(r => r.url().includes('press.api.client.run_doc_method') && r.request().method() === 'POST' && (r.request().postData() || '').includes('create_site')),
      (async () => { await page.waitForTimeout(400); await page.getByRole('button', { name: /create site/i }).click(); })(),
    ]));
    let activePage: Page | null = await Promise.race([
      popupPromise,
      (async () => { await page.waitForTimeout(4000); return null; })(),
    ]);
    if (!activePage) activePage = page;
    // Provisioning deadline capped by remaining product budget (max 4m internal cap)
    const provisionCap = Math.min(240_000, Math.max(10_000, remaining()));
    const deadline = Date.now() + provisionCap;
    let success = false;
    while (Date.now() < deadline && !success) {
      ensureTime('provision-loop');
      const url = activePage.url();
      let host = '';
      try { host = new URL(url).host; } catch { /* ignore */ }
      if (host && host !== originHost && /\/app\//.test(url)) {
  if (domainSuffix && siteSubdomain) {
          const hostNoPort = host.split(':')[0].toLowerCase();
            const expectedFull = `${siteSubdomain}.${domainSuffix}`.toLowerCase();
            if (hostNoPort !== expectedFull) {
              const relaxedOk = hostNoPort.includes(siteSubdomain.toLowerCase()) && hostNoPort.endsWith(`.${domainSuffix.toLowerCase()}`);
              if (!relaxedOk) {
                throw new Error(`Provisioned site host mismatch. Expected ${expectedFull} (allowing variations), got ${hostNoPort}. Details: subdomain=${siteSubdomain} domainSuffix=${domainSuffix} finalUrl=${url}`);
              }
            }
        }
        success = true; break;
      }
      try {
        await Promise.race([
          activePage.waitForEvent('framenavigated', { timeout: 3000 }),
          activePage.waitForTimeout(800),
        ]);
      } catch { /* ignore */ }
    }
    if (!success) {
      throw new Error(`Did not observe redirect to provisioned site app. Last URL: ${activePage.url()}`);
    }
    expect(activePage.url()).toMatch(/\/app\//);
  }
}

test.describe.configure({ mode: 'parallel' });

const products = fetchProductTrials();

for (const product of products) {
  test(`signup flow for product: ${product}`, async ({ page }) => {
    test.setTimeout(PER_PRODUCT_TIMEOUT_MS + 30_000);
    await runSignupFlow(page, product);
  });
}
