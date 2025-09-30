<template>
	<Dialog
		v-model="showDialog"
		:modelValue="true"
		:options="{ title: 'Database Configuration', size: '3xl' }"
	>
		<template v-slot:body-content>
			<div
				class="flex h-[200px] w-full items-center justify-center"
				v-if="this.$resources.mariadbVariables.loading"
			>
				<div class="flex flex-row items-center gap-2 text-gray-700">
					<Spinner class="w-4" />
					Loading database configurations
				</div>
			</div>
			<div v-else>
				<ObjectList :options="listOptions" />
			</div>
		</template>
	</Dialog>
</template>
<script>
import { Spinner } from 'frappe-ui';
import ObjectList from '../ObjectList.vue';
import { toast } from 'vue-sonner';

export default {
	name: 'DatabaseConfigurationDialog',
	props: ['name'],
	components: {
		ObjectList,
		Spinner,
	},
	data() {
		return {
			showDialog: true,
		};
	},
	resources: {
		mariadbVariables() {
			return {
				url: 'press.api.client.run_doc_method',
				params: {
					dt: 'Database Server',
					dn: this.name,
					method: 'get_mariadb_variables',
					args: {},
				},
				initialData: [],
				auto: true,
				onError: () => {
					toast.error(
						'Failed to fetch database configurations. Please try again later.',
					);
					this.showDialog = false;
				},
			};
		},
	},
	computed: {
		listOptions() {
			return {
				data: () => this.$resources?.mariadbVariables?.data?.message || [],
				columns: [
					{
						label: 'Variable Name',
						fieldname: 'Variable_name',
						width: '400px',
					},
					{
						label: 'Value',
						fieldname: 'Value',
						width: '300px',
					},
				],
			};
		},
	},
};
</script>
