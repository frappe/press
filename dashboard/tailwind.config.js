const plugin = require('tailwindcss/plugin');

module.exports = {
	presets: [require('frappe-ui/src/utils/tailwind.config')],
	content: [
		'./public/index.html',
		'./src/**/*.html',
		'./src/**/*.vue',
		'./src/assets/*.css',
		'./node_modules/frappe-ui/src/components/**/*.{vue,js,ts}'
	],
	theme: {
		extend: {
			fontSize: {
				xs: '11px',
				sm: '12px',
				base: '13px',
				lg: '14px',
				xl: '16px',
				'2xl': '18px',
				'3xl': '20px',
				'4xl': '22px',
				'5xl': '24px',
				'6xl': '28px'
			},
			width: {
				112: '28rem',
				wizard: '650px'
			},
			minWidth: {
				40: '10rem'
			},
			maxHeight: {
				52: '13rem'
			}
		},
		container: {
			padding: {
				xl: '5rem'
			},
			margin: {
				3.5: '14px'
			}
		},
		screens: {
			sm: '640px',
			md: '768px',
			lg: '1024px',
			xl: '1280px'
		}
	},
	plugins: [
		plugin(function ({ addUtilities, theme }) {
			// Add your custom styles here
			addUtilities({
				'.bg-gradient-blue': {
					'background-image': `linear-gradient(180deg,#2c9af1 0%, ${theme(
						'colors.blue.500'
					)} 100%)`
				}
			});
			addUtilities({
				'.bg-gradient-none': {
					'background-image': 'none'
				}
			});
		})
	]
};
