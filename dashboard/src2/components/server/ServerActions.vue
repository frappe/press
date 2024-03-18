<template>
	<div
		class="max-w-3xl divide-y sm:rounded sm:border sm:p-5"
		v-if="$appServer?.doc?.actions && $dbServer?.doc?.actions"
	>
		<div
			class="py-3 first:pt-0 last:pb-0"
			v-for="row in $appServer.doc.actions"
			:key="row.action"
		>
			<ServerActionCell
				:serverName="$appServer.doc.name"
				serverType="Server"
				:actionLabel="row.action"
				:method="row.doc_method"
				:description="row.description"
				:buttonLabel="row.button_label"
			/>
		</div>
		<div
			class="py-3 first:pt-0 last:pb-0"
			v-for="row in $dbServer.doc.actions"
			:key="row.action"
		>
			<ServerActionCell
				:serverName="$dbServer.doc.name"
				serverType="Database Server"
				:actionLabel="row.action"
				:method="row.doc_method"
				:description="row.description"
				:buttonLabel="row.button_label"
			/>
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
		$appServer() {
			return getCachedDocumentResource('Server', this.server);
		},
		$dbServer() {
			return getDocResource({
				doctype: 'Database Server',
				name: this.$appServer.doc.database_server,
				whitelistedMethods: {
					changePlan: 'change_plan',
					reboot: 'reboot',
					rename: 'rename'
				}
			});
		}
	}
};
</script>
