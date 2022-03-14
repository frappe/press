<script>
import { h } from 'vue';
import feather from 'feather-icons';

const validIcons = Object.keys(feather.icons);

export default {
	props: {
		name: {
			type: String,
			required: true,
			validator(value) {
				const valid = validIcons.includes(value);
				if (!valid) {
					console.warn(
						`name property for feather-icon must be one of `,
						validIcons
					);
				}
				return valid;
			}
		},
		color: {
			type: String,
			default: null
		},
		strokeWidth: {
			type: Number,
			default: 1.5
		}
	},
	compatConfig: {
		MODE: 3
	},
	render() {
		let icon = feather.icons[this.name];

		// Extract every property of $attrs except 'class'
		const attrs = Object.keys(this.$attrs).reduce((acc, key) => {
			if (key !== 'class') {
				acc[key] = this.$attrs[key];
			}
			return acc;
		}, {});

		let options = {
			...icon.attrs,
			fill: 'none',
			stroke: 'currentColor',
			color: this.color,
			class: [icon.attrs.class || '', this.$attrs.class],
			'stroke-linecap': 'round',
			'stroke-linejoin': 'round',
			'stroke-width': this.strokeWidth,
			width: null,
			height: null,
			innerHTML: icon.contents,
			...attrs
		};

		return h('svg', options);
	}
};
</script>
