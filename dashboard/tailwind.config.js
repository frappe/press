module.exports = {
	theme: {
		fontFamily: {
			sans: ['Inter', 'sans-serif'],
			mono: [
				'Consolas',
				'"Andale Mono WT"',
				'"Andale Mono"',
				'"Lucida Console"',
				'"Lucida Sans Typewriter"',
				'"DejaVu Sans Mono"',
				'"Bitstream Vera Sans Mono"',
				'"Liberation Mono"',
				'"Nimbus Mono L"',
				'Monaco',
				'"Courier New"',
				'Courier',
				'monospace'
			]
		},
		extend: {
			width: {
				112: '28rem'
			},
			colors: {
				brand: '#2490EF',
				'brand-100': '#f4f9ff',
				black: '#112B42',
				gray: {
					'50': '#f9fafb',
					'100': '#f4f4f6',
					'200': '#e9ebed',
					'300': '#dfe1e2',
					'400': '#cccfd1',
					'500': '#b7bfc6',
					'600': '#a1abb4',
					'700': '#9fa5a8',
					'800': '#7f878a',
					'900': '#415668'
				}
			}
		}
	},
	plugins: [require('@tailwindcss/custom-forms')]
};
