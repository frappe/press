<script>
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
		strokeWidth: {
			type: Number,
			default: 1.5
		}
	},
	render(h) {
		let icon = feather.icons[this.name];
		return h('svg', {
			attrs: Object.assign({}, icon.attrs, {
				fill: 'none',
				stroke: 'currentColor',
				'stroke-linecap': 'round',
				'stroke-linejoin': 'round',
				'stroke-width': this.strokeWidth,
				width: null,
				height: null
			}),
			on: this.$listeners,
			class: [icon.attrs.class],
			domProps: {
				innerHTML: icon.contents
			}
		});
	}
};
</script>
