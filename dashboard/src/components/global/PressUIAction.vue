<script>
export default {
	name: 'PressUIAction',
	props: ['name', 'params'],
	render(h) {
		return this.show
			? this.$scopedSlots.default({
					action: this.$resources.action,
					execute: this.$resources.execute
			  })
			: null;
	},
	resources: {
		action() {
			return {
				method: 'press.api.action.get',
				params: { name: this.name },
				auto: true
			};
		},
		execute() {
			return {
				method: 'press.api.action.execute',
				params: {
					name: this.name,
					...(this.params || {})
				}
			};
		}
	},
	computed: {
		show() {
			return this.$resources.action?.data;
		}
	}
};
</script>
