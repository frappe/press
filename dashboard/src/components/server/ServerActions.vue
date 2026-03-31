<template>
	<div
		class="mx-auto max-w-3xl space-y-4"
		v-if="$appServer?.doc?.actions && $dbServer?.doc?.actions"
	>
		<div
			v-for="group in actions"
			:key="group.group"
			class="divide-y rounded border border-gray-200 p-5"
		>
			<div class="pb-3 text-lg font-semibold">{{ group.group }}</div>
			<div
				class="py-3 first:pt-0 last:pb-0"
				v-for="row in group.actions"
				:key="row.action"
			>
				<ServerActionCell
					:group="group.group"
					:serverName="row.server_name"
					:serverType="row.server_doctype"
					:actionLabel="row.action"
					:method="row.doc_method"
					:description="row.description"
					:buttonLabel="row.button_label"
				/>
			</div>
		</div>
	</div>
</template>
<script>
import { getCachedDocumentResource } from 'frappe-ui';
import ServerActionCell from './ServerActionCell.vue';
import { getDocResource } from '../../utils/resource';

export default {
	name: 'ServerActions',
	props: ['server'],
	components: { ServerActionCell },
	computed: {
		actions() {
			const totalActions = [
				...this.$appServer.doc.actions,
				...this.$dbServer.doc.actions,
				...(this.$dbReplicaServer?.doc?.actions || []),
			];

			const groupedActions = totalActions.reduce((acc, action) => {
				const group = action.group || `${action.server_doctype} Actions`;
				if (!acc[group]) {
					acc[group] = [];
				}
				acc[group].push(action);
				return acc;
			}, {});

			let groups = Object.keys(groupedActions).map((group) => {
				return {
					group,
					actions: groupedActions[group],
				};
			});

			// move dangerous actions to the bottom
			const dangerousActions = groups.find(
				(group) => group.group === 'Dangerous Actions',
			);
			if (dangerousActions) {
				groups = groups.filter((group) => group.group !== 'Dangerous Actions');
				groups.push(dangerousActions);
			}

			return groups;
		},
		$appServer() {
			return getCachedDocumentResource('Server', this.server);
		},
		$dbServer() {
			// Should mirror the whitelistedMethods in ServerOverview.vue
			return getDocResource({
				doctype: 'Database Server',
				name: this.$appServer.doc.database_server,
				whitelistedMethods: {
					changePlan: 'change_plan',
					reboot: 'reboot',
					rename: 'rename',
					enablePerformanceSchema: 'enable_performance_schema',
					disablePerformanceSchema: 'disable_performance_schema',
					enableBinlogIndexing: 'enable_binlog_indexing_service',
					disableBinlogIndexing: 'disable_binlog_indexing_service',
					getMariadbVariables: 'get_mariadb_variables',
					updateInnodbBufferPoolSize: 'update_innodb_buffer_pool_size',
					updateMaxDbConnections: 'update_max_db_connections',
					updateBinlogRetention: 'update_binlog_retention',
					updateBinlogSizeLimit: 'update_binlog_size_limit',
					getBinlogsInfo: 'get_binlogs_info',
					purgeBinlogsForcefully: 'purge_binlogs_forcefully',
				},
			});
		},
		$dbReplicaServer() {
			return getDocResource({
				doctype: 'Database Server',
				name: this.$appServer.doc.replication_server,
				whitelistedMethods: {
					changePlan: 'change_plan',
					reboot: 'reboot',
					rename: 'rename',
				},
			});
		},
	},
};
</script>
