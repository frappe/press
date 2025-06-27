import plugin from 'tailwindcss/plugin';
import frappeUIPreset from 'frappe-ui/src/tailwind/preset';
import containerQueries from '@tailwindcss/container-queries';

export default {
	presets: [frappeUIPreset],
	content: [
		'./public/index.html',
		'./src/**/*.html',
		'./src/**/*.vue',
		'./src2/**/*.vue',
		'./src/assets/*.css',
		'./node_modules/frappe-ui/src/components/**/*.{vue,js,ts}',
	],
	theme: {
		extend: {
			width: {
				112: '28rem',
				wizard: '650px',
			},
			minWidth: {
				40: '10rem',
			},
			maxHeight: {
				52: '13rem',
			},
		},
		container: {
			padding: {
				xl: '5rem',
			},
			margin: {
				3.5: '14px',
			},
		},
		screens: {
			sm: '640px',
			md: '768px',
			lg: '1024px',
			xl: '1280px',
		},
	},
	plugins: [
		containerQueries,
		plugin(function ({ addUtilities, theme }) {
			// Add your custom styles here
			addUtilities({
				'.bg-gradient-blue': {
					'background-image': `linear-gradient(180deg,#2c9af1 0%, ${theme(
						'colors.blue.500',
					)} 100%)`,
				},
			});
			addUtilities({
				'.bg-gradient-none': {
					'background-image': 'none',
				},
			});
		}),
	],
};
