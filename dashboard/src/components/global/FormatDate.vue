<script>
import { DateTime } from 'luxon';
import { h } from 'vue';

export default {
	name: 'FormatDate',
	props: {
		type: {
			type: String,
			default: 'full'
		}
	},
	render() {
		let node = this.$slots.default()[0];
		let value = node.children;
		value = value.trim();

		let formattedDate = this.formatDate(value, this.type);
		return h(
			'span',
			{
				title: this.$date(value).toLocaleString(DateTime.DATETIME_FULL)
			},
			formattedDate
		);
	}
};
</script>
