<script>
import { DateTime } from 'luxon';

export default {
	name: 'FormatDate',
	props: {
		type: {
			type: String,
			default: 'full'
		}
	},
	render(h) {
		let node = this.$slots.default[0];
		let value = node.text;
		value = value.trim();
		let format = this.formatDate(value, this.type);
		return h(
			'span',
			{
				attrs: {
					title: this.$date(value).toLocaleString(DateTime.DATETIME_FULL)
				}
			},
			format
		);
	}
};
</script>
