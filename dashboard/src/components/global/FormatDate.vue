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
        let datetime = DateTime.fromSQL(value);
		let formatted = datetime.toLocaleString(DateTime.DATETIME_FULL);
		let format;
		if (this.type === 'relative') {
			format = datetime.toRelative();
		} else if (this.type === 'full') {
			format = datetime.toLocaleString(DateTime.DATETIME_FULL);
		}
		return h(
			'span',
			{
				attrs: {
					title: formatted
				}
			},
			format
		);
	}
};
</script>
