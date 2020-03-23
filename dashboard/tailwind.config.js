module.exports = {
	theme: {
		extend: {
			fontFamily: {
				sans: ['Inter', 'sans-serif']
			},
			width: {
				112: '28rem'
			},
			colors: {
				brand: '#2490EF',
				'brand-100': '#f4f9ff',
				black: '#112B42',
				blue: {
					'50': '#f4f9ff',
					'100': '#E8F4FD',
					'200': '#BDDDFA',
					'300': '#88C3F6',
					'400': '#54A8F2',
					'500': '#2490EF',
					'600': '#107CDB',
					'700': '#0D66B5',
					'800': '#0A518F',
					'900': '#083B69'
				},
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
	plugins: [require('@tailwindcss/ui')]
};
