<template>
	<Header class="sticky top-0 z-10 bg-white">
		<div
			class="flex w-full flex-col gap-2 md:flex-row md:items-center md:justify-between"
		>
			<div class="flex flex-row items-center gap-2">
				<!-- Title -->
				<Breadcrumbs
					:items="[
						{ label: 'Dev Tools', route: '/database-analyzer' },
						{ label: 'Database Analyzer', route: '/database-analyzer' }
					]"
				/>
			</div>
			<div class="flex flex-row gap-2">
				<LinkControl
					class="cursor-pointer"
					:options="{ doctype: 'Site', filters: { status: 'Active' } }"
					placeholder="Select a site"
					v-model="site"
				/>
				<Button
					iconLeft="refresh-ccw"
					variant="subtle"
					:loading="site && !isSchemaInformationReceived"
					:disabled="!site"
					@click="
						() =>
							fetchTableSchemas({
								reload: true
							})
					"
				>
					<span class="md:hidden">Schema</span>
					<span class="hidden md:inline">Refresh Schema</span>
				</Button>
			</div>
		</div>
	</Header>
	<div class="m-5">
		<!-- body -->
		<div class="mt-2 flex flex-col" v-if="isSchemaInformationReceived">
			<div>
				<Button @click="optimizeTable"> Optimize Table </Button>
			</div>
			<ObjectList :options="tableAnalysisTableOptions" />
		</div>
		<div
			v-else-if="!site"
			class="flex h-full min-h-[80vh] w-full items-center justify-center gap-2 text-gray-700"
		>
			Select a site to get started
		</div>
		<div
			class="flex h-full min-h-[80vh] w-full items-center justify-center gap-2 text-gray-700"
			v-else
		>
			<Spinner class="w-4" /> Loading Table Schemas
		</div>
	</div>
</template>
<script>
import Header from '../../../components/Header.vue';
import { Tabs, Breadcrumbs } from 'frappe-ui';
import LinkControl from '../../../components/LinkControl.vue';
import ObjectList from '../../../components/ObjectList.vue';
import { h } from 'vue';
import { toast } from 'vue-sonner';

export default {
	name: 'DatabaseAnalyzer',
	components: {
		Header,
		Breadcrumbs,
		FTabs: Tabs,
		LinkControl,
		ObjectList
	},
	data() {
		return {
			site: null,
			errorMessage: null,
			optimize_table_job_name: null
		};
	},
	mounted() {},
	watch: {
		site(site_name) {
			// reset state
			this.data = null;
			this.errorMessage = null;
			this.fetchTableSchemas({
				site_name: site_name
			});
		}
	},
	resources: {
		tableSchemas() {
			return {
				url: 'press.api.client.run_doc_method',
				initialData: {},
				auto: false,
				onSuccess: data => {
					if (data?.message?.loading) {
						setTimeout(this.fetchTableSchemas, 5000);
					}
				}
			};
		},
		optimizeTable() {
			return {
				url: 'press.api.client.run_doc_method',
				initialData: {},
				auto: false,
				onSuccess: data => {
					if (data?.message) {
						if (data?.message?.success) {
							toast.success(data?.message?.message);
						} else {
							toast.error(data?.message?.message);
						}
						this.optimize_table_job_name = data?.message?.job_name;
					}
				}
			};
		}
	},
	computed: {
		isSchemaInformationReceived() {
			if (this.$resources.tableSchemas.loading) return false;
			if (this.$resources.tableSchemas?.data?.message?.loading) return false;
			if (!this.$resources.tableSchemas?.data?.message?.data) return false;
			if (this.$resources.tableSchemas?.data?.message?.data == {}) return false;
			return true;
		},
		tableSchemas() {
			if (!this.isSchemaInformationReceived) return [];
			return this.$resources.tableSchemas?.data?.message?.data;
		},
		tableSizeInfo() {
			if (!this.isSchemaInformationReceived) return [];
			let data = [];
			for (const tableName in this.tableSchemas) {
				const table = this.tableSchemas[tableName];
				data.push({
					table_name: tableName,
					size_mb: (table.size.total_size / (1024 * 1024)).toFixed(3),
					no_of_columns: table.columns.length
				});
			}
			return data;
		},
		tableAnalysisTableOptions() {
			if (!this.isSchemaInformationReceived) return [];
			return {
				data: () => this.tableSizeInfo,
				hideControls: true,
				columns: [
					{
						label: 'Table Name',
						fieldname: 'table_name',
						width: 0.5,
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
									}
								},
								[row.table_name]
							);
						}
					},
					{
						label: 'Size (MB)',
						fieldname: 'size_mb',
						width: 0.5
					},
					{
						label: 'No of Columns',
						fieldname: 'no_of_columns',
						width: 0.5
					}
				]
			};
		}
	},
	methods: {
		fetchTableSchemas({ site_name = null, reload = false } = {}) {
			if (!site_name) site_name = this.site;
			if (!site_name) return;
			this.$resources.tableSchemas.submit({
				dt: 'Site',
				dn: site_name,
				method: 'fetch_database_table_schema',
				args: {
					reload
				}
			});
		},
		optimizeTable() {
			this.$resources.optimizeTable.submit({
				dt: 'Site',
				dn: this.site,
				method: 'optimize_tables'
			});
		}
	}
};
</script>
