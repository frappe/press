import path from 'path';
import fs from "fs";
import { fileURLToPath } from 'url';
import { test as setup } from "./coverage.fixture";

const localCloudBaseUrl = process.env.BASE_URL!;
const userEmail = process.env.PRESS_ADMIN_USER_EMAIL!;
const userPassword = process.env.PRESS_ADMIN_USER_PASSWORD!;
const sessionStoragePath = process.env.PLAYWRIGHT_SESSION_STORAGE_PATH || '../../.auth/session.json';

function getSessionStorageStatePath() {
  const __filename = fileURLToPath(import.meta.url);
  const __dirname = path.dirname(__filename);
  const authFile = path.join(__dirname, sessionStoragePath);
  const authDir = path.dirname(authFile);

  if (!fs.existsSync(authDir)) {
    fs.mkdirSync(authDir, { recursive: true });
  }
  
  return authFile;
}

setup('authenticate into press dashboard', async ({ page }) => {
  // Login
  await page.goto(`${localCloudBaseUrl}/dashboard/login`);
  await page.getByRole('textbox', { name: 'Email (required)' }).fill(userEmail);
  await page.getByRole('button', { name: 'Continue with password' }).click();
  await page.getByRole('textbox', { name: 'Password (required)' }).fill(userPassword);
  await page.getByRole('button', { name: 'Log In' }).click();

  // Wait for successful navigation
  await page.waitForURL('**/dashboard/sites');

  // Save storage state
  await page.context().storageState({ path: getSessionStorageStatePath() });
});
