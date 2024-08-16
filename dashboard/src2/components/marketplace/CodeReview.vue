<template>
	<Dialog
		v-model="show"
		:options="{
			title: 'Hello meow',
			size: '6xl'
		}"
	>
	</Dialog>
</template>

<script>
export default {
	props: ['row'],
	components: {},
	data() {
		return {
			show: true
		};
	},
	mounted() {
		console.log('Row prop value:', this.row);
	},
	resources: {
		codeScreening() {
			return {
				type: 'list',
				doctype: 'App Release Approval Request',
				fields: [
					'name',
					'marketplace_app',
					'screening_status',
					'app_release',
					'status',
					'result'
				],
				filters: {
					app_release: this.row.name,
					status: 'Open'
				},
				orderBy: 'creation desc',
				start: 0,
				auto: true
			};
		}
	}
};
</script>
