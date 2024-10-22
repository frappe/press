<template>
	<Dialog
		:options="{
			title: this.tableName,
			size: '2xl'
		}"
	>
		<template #body-content>
			<ObjectList :options="listOptions" />
		</template>
	</Dialog>
</template>
<script>
import { Badge } from 'frappe-ui';
import ObjectList from '../../ObjectList.vue';
import { h } from 'vue';

export default {
	name: 'DatabaseTableSchemaInfoDialog',
	props: ['tableName', 'columns'],
	components: {
		ObjectList
	},
	computed: {
		listOptions() {
			return {
				data: () => this.columns || [],
				columns: [
					{
						label: 'Column',
						fieldname: 'column',
						width: 0.5
					},
					{
						label: 'Data Type',
						fieldname: 'data_type',
						width: 0.2,
						align: 'center'
					},
					{
						label: 'Nullable',
						fieldname: 'is_nullable',
						width: 0.2,
						format(value) {
							return value ? 'Yes' : 'No';
						},
						align: 'center'
					},
					{
						label: 'Default',
						fieldname: 'default',
						width: 0.3,
						align: 'center'
					}
				]
			};
		}
	}
};
</script>
