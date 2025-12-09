import { test as base, expect } from "@playwright/test";
import v8ToIstanbul from "v8-to-istanbul";
import crypto from "crypto";
import path from "path";
import fs from "fs";

const test = base.extend({
  page: async ({ page }, use) => {
    await page.coverage.startJSCoverage();
    
    await use(page);
    
    const coverage = await page.coverage.stopJSCoverage();

    const pathToSource = path.join(
      process.cwd(),
      "../../../sites/assets/press/dashboard/assets/index-",
    );

    for (const entry of coverage) {
      const converter = v8ToIstanbul(
        pathToSource,
        0,
        { source: entry.source as string }
      );

      await converter.load();
      converter.applyCoverage(entry.functions);

      const istanbul = converter.toIstanbul();
      for (const [key, _] of Object.entries(istanbul)) {
        istanbul[key].path = istanbul[key].path.replaceAll("sites", "apps/press");
      }
      const outputDir = "./.nyc_output";

      if (!fs.existsSync(outputDir)) {
        fs.mkdirSync(outputDir, { recursive: true });
      }

      const filename = path.join(outputDir, `${crypto.randomUUID()}.json`);
      fs.writeFileSync(filename, JSON.stringify(istanbul));
    }
  }
});

export { test, expect };