<template>
	<ObjectList :options="listOptions" />
	<DatabaseTableSchemaInfoDialog
		:tableName="selectedTableName"
		:columns="selectedTableColumns"
		v-model="showTableSchemaInfo"
	/>
</template>
<script>
import ObjectList from '../../ObjectList.vue';
import DatabaseTableSchemaInfoDialog from './DatabaseTableSchemaInfoDialog.vue';

export default {
	name: 'DatabaseBrowseSchema',
	inject: ['site'],
	components: {
		ObjectList,
		DatabaseTableSchemaInfoDialog
	},
	data() {
		return {
			selectedTableName: null,
			selectedTableColumns: [],
			showTableSchemaInfo: false
		};
	},
	resources: {
		tableSchemas() {
			return {
				url: 'press.api.client.run_doc_method',
				makeParams: () => {
					return {
						dt: 'Site',
						dn: this.site,
						method: 'fetch_database_table_schemas'
					};
				},
				initialData: {},
				auto: true
			};
		}
	},
	computed: {
		listOptions() {
			return {
				data: () => {
					return Object.keys(
						this.$resources.tableSchemas.data?.message ?? {}
					).map(x => {
						return {
							table_name: x
						};
					});
				},
				columns: [
					{
						label: 'Table Name',
						fieldname: 'table_name',
						width: 0.25
					}
				],
				secondaryAction: () => {
					return {
						label: 'Refresh',
						icon: 'refresh-ccw',
						loading: this.$resources.tableSchemas.loading,
						onClick: () => this.$resources.tableSchemas.reload()
					};
				},
				onRowClick: row => this.showTableSchemaInfoDialog(row.table_name)
			};
		}
	},
	methods: {
		showTableSchemaInfoDialog(tableName) {
			this.selectedTableName = tableName;
			this.selectedTableColumns =
				this.$resources.tableSchemas.data?.message[tableName];
			this.showTableSchemaInfo = true;
		}
	}
};
</script>
