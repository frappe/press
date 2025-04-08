// replace.cjs
const { execSync } = require("child_process");

const brand = process.env.BRAND_NAME;
if (!brand) {
  console.error("Missing BRAND_NAME");
  process.exit(1);
}

execSync(
  `find ../press/public/dashboard \\( -name '*.js' -o -name '*.html' -o -name '*.css' \\) -type f -exec sed -i -e "s/Frappe Cloud/${brand}/g" {} +`,
  { stdio: 'inherit', shell: true }
);
