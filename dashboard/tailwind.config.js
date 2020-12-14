const plugin = require('tailwindcss/plugin');

module.exports = {
	theme: {
		extend: {
			fontFamily: {
				sans: ['Inter', 'sans-serif']
			},
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
				112: '28rem'
			},
			minWidth: {
				40: '10rem'
			},
			borderColor: theme => ({
				default: theme('colors.gray.200')
			}),
			colors: {
				brand: '#2490EF',
				'brand-100': '#f4f9ff',
				black: '#112B42',
				blue: {
					'50': '#F0F8FE',
					'100': '#D3E9FC',
					'200': '#A7D3F9',
					'300': '#7CBCF5',
					'400': '#50A6F2',
					'500': '#2490EF',
					'600': '#1579D0',
					'700': '#1366AE',
					'800': '#154875',
					'900': '#1A4469'
				},
				gray: {
					'50': '#F9FAFA',
					'100': '#F4F5F6',
					'200': '#EEF0F2',
					'300': '#E2E6E9',
					'400': '#C8CFD5',
					'500': '#A6B1B9',
					'600': '#74808B',
					'700': '#4C5A67',
					'800': '#313B44',
					'900': '#192734'
				}
			}
		},
		customForms: theme => ({
			default: {
				input: {
					borderRadius: theme('borderRadius.md'),
					backgroundColor: theme('colors.gray.100'),
					borderWidth: '0',
					fontSize: theme('fontSize.base'),
					paddingTop: theme('spacing.1'),
					paddingBottom: theme('spacing.1'),
					lineHeight: theme('spacing.5'),
					'&::placeholder': {
						color: theme('colors.gray.700'),
						opacity: '1'
					},
					'&:focus': {
						outline: 'none',
						backgroundColor: theme('colors.gray.200'),
						boxShadow: theme('boxShadow.none')
					}
				},
				textarea: {
					borderRadius: theme('borderRadius.md'),
					backgroundColor: theme('colors.gray.100'),
					borderWidth: '0',
					fontSize: theme('fontSize.base'),
					paddingTop: theme('spacing.1'),
					paddingBottom: theme('spacing.1'),
					lineHeight: theme('spacing.5'),
					'&::placeholder': {
						color: theme('colors.gray.700'),
						opacity: '1'
					},
					'&:focus': {
						outline: 'none',
						backgroundColor: theme('colors.gray.200'),
						boxShadow: theme('boxShadow.none')
					}
				},
				select: {
					borderRadius: theme('borderRadius.md'),
					backgroundColor: theme('colors.gray.100'),
					borderWidth: '0',
					fontSize: theme('fontSize.base'),
					paddingTop: theme('spacing.1'),
					paddingBottom: theme('spacing.1'),
					lineHeight: theme('spacing.5'),
					'&:focus': {
						outline: 'none',
						backgroundColor: theme('colors.gray.200'),
						boxShadow: theme('boxShadow.none')
					}
				}
			}
		}),
		container: {
			padding: {
				xl: '5rem'
			}
		}
	},
	plugins: [
		require('@tailwindcss/ui'),
		require('@tailwindcss/typography'),
		plugin(function({ addUtilities, theme }) {
			// Add your custom styles here
			addUtilities({
				'.bg-gradient-blue': {
					'background-image': `linear-gradient(180deg,#2c9af1 0%, ${theme(
						'colors.blue.500'
					)} 100%)`
				}
			});
			addUtilities(
				{
					'.bg-gradient-none': {
						'background-image': 'none'
					}
				},
				{
					variants: ['focus', 'hover']
				}
			);
		})
	],
	purge: {
		content: ['./public/index.html', './src/**/*.html', './src/**/*.vue'],
		options: {
			whitelistPatternsChildren: [/chart-container$/, /graph-svg-tip$/]
		}
	}
};
