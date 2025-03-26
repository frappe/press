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
					It can take up to 20 seconds to load
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
				transform: (data) => {
					return Object.entries(data?.message ?? {}).map(([key, value]) => ({
						variable_name: key,
						value: value,
					}));
				},
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
				data: () => his.$resources?.mariadbVariables?.data || [],
				columns: [
					{
						label: 'Variable Name',
						fieldname: 'variable_name',
						width: '400px',
					},
					{
						label: 'Value',
						fieldname: 'value',
						width: '300px',
					},
				],
			};
		},
	},
};
</script>
