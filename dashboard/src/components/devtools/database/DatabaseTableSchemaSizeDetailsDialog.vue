<template>
	<Dialog
		:options="{
			title: 'Table Size',
			size: '3xl',
		}"
	>
		<template #body-content>
			<ObjectList :options="listOptions" />
		</template>
	</Dialog>
</template>
<script>
import { h } from 'vue';
import ObjectList from '../../ObjectList.vue';
import { toast } from 'vue-sonner';

export default {
	name: 'DatabaseTableSchemaSizeDetails',
	props: {
		site: {
			type: String,
			required: true,
		},
		tableSchemas: {
			type: Object,
			required: true,
		},
		viewSchemaDetails: {
			type: Function,
			required: true,
		},
	},
	components: {
		ObjectList,
	},
	computed: {
		listOptions() {
			if (!this.tableSchemas) return {};
			let data = [];
			for (const tableName in this.tableSchemas) {
				const table = this.tableSchemas[tableName];
				data.push({
					table_name: tableName,
					index_size: this.bytesToMB(table.size.index_length),
					data_size: this.bytesToMB(table.size.data_length),
					total_size: this.bytesToMB(table.size.total_size),
				});
			}
			// sort in the order of total_size
			data.sort((a, b) => b.total_size - a.total_size);
			return {
				data: () => data,
				hideControls: true,
				columns: [
					{
						label: 'Table Name',
						fieldname: 'table_name',
						width: '180px',
						align: 'left',
						type: 'Component',
						component({ row }) {
							return h(
								'div',
								{
									class: 'truncate text-base cursor-copy',
									onClick() {
										if ('clipboard' in navigator) {
											navigator.clipboard.writeText(row.table_name);
											toast.success('Copied to clipboard');
										}
									},
								},
								[row.table_name],
							);
						},
					},
					{
						label: 'Total Size (MB)',
						fieldname: 'total_size',
						align: 'center',
					},
					{
						label: 'Data Size (MB)',
						fieldname: 'data_size',
						align: 'center',
					},
					{
						label: 'Index Size (MB)',
						fieldname: 'index_size',
						align: 'center',
					},
					{
						label: 'View Schema',
						fieldname: 'table_name',
						type: 'Component',
						align: 'center',
						component: ({ row }) => {
							return h(
								'button',
								{
									class:
										'inline-flex items-center justify-center gap-2 transition-colors focus:outline-none text-gray-800 bg-gray-100 hover:bg-gray-200 active:bg-gray-300 focus-visible:ring focus-visible:ring-gray-400 h-7 text-base px-2 rounded',
									onClick: () => {
										this.viewSchemaDetails(row.table_name);
									},
								},
								['View Schema'],
							);
						},
					},
				],
			};
		},
	},
	methods: {
		bytesToMB(bytes) {
			return (bytes / (1024 * 1024)).toFixed(2);
		},
	},
};
</script>
