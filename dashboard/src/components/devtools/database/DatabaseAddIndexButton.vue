<template>
	<Button v-if="isJobRunning" @click="viewJob" variant="ghost" class="w-full"
		>View Job</Button
	>
	<Button
		v-else
		@click="addIndex"
		:loading="this.$resources.addIndex.loading"
		loadingText="Adding Index"
		iconLeft="plus"
		variant="ghost"
		class="w-full"
		>Add DB Index</Button
	>
</template>
<script>
import { toast } from 'vue-sonner';
export default {
	props: {
		row: { type: Object, required: true },
		site: { type: String, required: true },
	},
	data() {
		return {
			isJobRunning: false,
			jobName: null,
		};
	},
	resources: {
		addIndex() {
			return {
				url: 'press.api.client.run_doc_method',
				initialData: {},
				makeParams: () => {
					return {
						dt: 'Site',
						dn: this.site,
						method: 'add_database_index',
						args: {
							table: this.row['Table'],
							column: this.row['Column'],
						},
					};
				},
				onSuccess: (data) => {
					if (data?.message) {
						if (data?.message?.success) {
							toast.success(data?.message?.message);
							this.isJobRunning = true;
							this.jobName = data?.message?.job_name;
						} else {
							toast.error(data?.message?.message);
						}
					}
				},
				auto: false,
			};
		},
	},
	methods: {
		addIndex() {
			this.$resources.addIndex.submit();
		},
		viewJob() {
			if (this.jobName) {
				window.open(
					this.$router.resolve(
						`/sites/${this.site}/insights/jobs/${this.jobName}`,
					).href,
					'_blank',
				);
			}
		},
	},
};
</script>
