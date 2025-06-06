<template>
	<Dialog
		:options="{
			title: title,
			size: '2xl',
		}"
		v-model="show"
	>
		<template #body-content>
			<div
				v-if="this.$resources?.databaseServerStorageBreakdown?.loading"
				class="flex h-80 w-full items-center justify-center gap-2 text-base text-gray-700"
			>
				<Spinner class="w-4" /> Analyzing ...
			</div>
			<div
				v-else-if="this.$resources?.databaseServerStorageBreakdown?.error"
				class="flex h-80 w-full items-center justify-center gap-2 text-base text-gray-700"
			>
				<ErrorMessage
					:message="$resources.databaseServerStorageBreakdown.error"
				/>
			</div>
			<div v-else>
				<StorageBreakupChart
					:colorPalette="colorPalette"
					:data="databaseStorageBreakdown"
					:keyFormatter="keyFormatter"
					:valueFormatter="(key, value) => formatSizeInKB(value)"
					:stickyKeys="['free', 'os']"
					:hiddenKeysInSlider="['free']"
				/>
				<div v-if="serverType === 'Database Server' && noOfDatabases">
					<div
						v-if="noOfDatabases > 1"
						class="my-3 flex flex-row items-center justify-between px-1.5"
					>
						<div class="flex flex-row items-center gap-1">
							<p class="text-base font-semibold text-gray-800">
								Usage of
								{{
									noOfDatabases > topNDatabases && !showAllDatabases
										? `Top ${topNDatabases} Databases`
										: `${noOfDatabases} Databases`
								}}
							</p>
						</div>
						<Button
							variant="outline"
							@click="showAllDatabases = !showAllDatabases"
						>
							{{ showAllDatabases ? 'Show Less' : 'Show All' }}
						</Button>
					</div>
					<StorageBreakupChart
						:showSlider="false"
						:data="dbStorageUsage"
						:keyFormatter="keyFormatter"
						:valueFormatter="(key, value) => formatSizeInKB(value)"
						:showTopN="
							showAllDatabases
								? noOfDatabases
								: Math.min(noOfDatabases, topNDatabases)
						"
					/>
				</div>
			</div>
		</template>
	</Dialog>
</template>
<script>
import { Spinner } from 'frappe-ui';
import StorageBreakupChart from '../StorageBreakupChart.vue';
import { h } from 'vue';

export default {
	name: 'StorageBreakdown',
	components: {
		Spinner,
		StorageBreakupChart,
	},
	props: {
		title: {
			type: String,
			default: 'Storage Breakdown',
		},
		serverType: {
			type: String,
			required: true,
		},
		server: {
			type: String,
			required: true,
		},
	},
	data() {
		return {
			show: true,
			colorPalette: [
				'#2563eb',
				'#10b981',
				'#f59e42',
				'#a21caf',
				'#22d3ee',
				'#ef4444',
				'#fde047',
				'#fbbf24',
				'#6366f1',
				'#14b8a6',
				'#eab308',
				'#f472b6',
				'#64748b',
				'#84cc16',
			],
			topNDatabases: 5, // Default to showing top 10 databases
			showAllDatabases: false,
		};
	},
	mounted() {
		if (this.serverType == 'Database Server') {
			this.$resources.databaseServerStorageBreakdown.submit();
		}
	},
	resources: {
		databaseServerStorageBreakdown() {
			return {
				url: 'press.api.client.run_doc_method',
				makeParams() {
					return {
						dt: 'Database Server',
						dn: this.server,
						method: 'get_storage_usage',
					};
				},
				onSuccess: (_) => {
					this.isDatabaseListVisible = true;
				},
				auto: false,
			};
		},
	},
	computed: {
		databaseStorageBreakdown() {
			if (!this.$resources.databaseServerStorageBreakdown?.data?.message)
				return {};
			let message = this.$resources.databaseServerStorageBreakdown.data.message;
			let data = {
				free: message.disk_free,
				os: message.os_usage,
				bin_log: message.database.bin_log,
				slow_log: message.database.slow_log,
				error_log: message.database.error_log,
				db_other: message.database.other,
				db_core: message.database.core,
				db_data: Object.values(message.database.schema).reduce(
					(partialSum, a) => partialSum + a,
					0,
				),
			};
			return data;
		},
		noOfDatabases() {
			if (this.serverType !== 'Database Server') return 0;
			if (!this.$resources.databaseServerStorageBreakdown?.data?.message)
				return 0;
			let message = this.$resources.databaseServerStorageBreakdown.data.message;
			return Object.keys(message.database.schema || {}).length;
		},
		dbStorageUsage() {
			if (this.serverType !== 'Database Server') return {};
			if (!this.$resources.databaseServerStorageBreakdown?.data?.message)
				return {};
			let message = this.$resources.databaseServerStorageBreakdown.data.message;
			return message.database.schema || {};
		},
		dbNameSiteMapping() {
			if (this.serverType !== 'Database Server') return {};
			if (!this.$resources.databaseServerStorageBreakdown?.data?.message)
				return {};
			return (
				this.$resources.databaseServerStorageBreakdown.data.message
					?.db_name_site_map ?? {}
			);
		},
	},
	methods: {
		keyFormatter(key) {
			if (key in this.dbNameSiteMapping) {
				return h(
					'a',
					{
						href: `/dashboard/database-analyzer?site=${this.dbNameSiteMapping[key]}`,
						target: '_blank',
						rel: 'noopener noreferrer',
					},
					[
						`${this.dbNameSiteMapping[key]} (${key})`,
						h('span', { style: 'margin-left: 0.25em;' }, '↗'),
					],
				);
			}
			return (
				{
					free: 'Free Space',
					os: 'Operating System',
					bin_log: 'MariaDB Binary Log',
					slow_log: 'MariaDB Slow Log',
					error_log: 'MariaDB Error Log',
					db_data: `${this.noOfDatabases} Databases (including mysql, sys, perf_schema)`,
					db_core: 'MariaDB Core',
					db_other: 'MariaDB Owned System Files',
				}[key] || key
			);
		},
		formatSizeInKB(kb) {
			try {
				let floatKB = parseFloat(kb);
				if (floatKB > 1024 * 512) {
					return `${Math.round(floatKB / 1024 / 1024).toFixed(1)} GB`;
				} else if (floatKB > 512) {
					return `${Math.round(floatKB / 1024).toFixed(1)} MB`;
				} else {
					return `${floatKB} KB`;
				}
			} catch (error) {
				return `${kb} KB`;
			}
		},
	},
};
</script>
