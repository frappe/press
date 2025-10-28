import type { Page, Locator } from '@playwright/test';

export class Dashboard {
  private page: Page;

  constructor(page: Page) {
    this.page = page;
  }

  async signup() {
    this.page.goto('http://savetheplanet.earth:8001/dashboard/signup');
  }

  async login(email: string, password: string) {
  }

  async logout() {

  }
}
