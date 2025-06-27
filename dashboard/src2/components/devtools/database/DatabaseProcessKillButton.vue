<template>
	<p v-if="isKilled">Process Killed</p>
	<Button
		v-else
		@click="killProcess"
		:loading="this.$resources.killProcess.loading"
		loadingText="Killing"
		iconLeft="x"
		variant="ghost"
		class="w-full"
		>Kill</Button
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
			isKilled: false,
		};
	},
	resources: {
		killProcess() {
			return {
				url: 'press.api.client.run_doc_method',
				initialData: {},
				makeParams: () => {
					return {
						dt: 'Site',
						dn: this.site,
						method: 'kill_database_process',
						args: {
							id: this.row.ID,
						},
					};
				},
				onSuccess: (data) => {
					this.isKilled = true;
					toast.success('Database Process Killed');
				},
				auto: false,
			};
		},
	},
	methods: {
		killProcess() {
			this.$resources.killProcess.submit();
		},
	},
};
</script>
