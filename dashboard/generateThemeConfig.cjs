/**
 * This node script resolves the tailwind config and dumps it as a json in
 * tailwind.theme.json which is later imported into the app.
 */
let fs = require('fs');
let resolveConfig = require('tailwindcss/resolveConfig');
let config = require('./tailwind.config.cjs');
let { theme } = resolveConfig(config);

fs.writeFileSync('./tailwind.theme.json', JSON.stringify(theme, null, 2));
