<template>
	<div class="flex items-center justify-between gap-1">
		<div>
			<h3 class="text-base font-medium">{{ props.actionLabel }}</h3>
			<p class="mt-1 text-p-base text-gray-600">{{ props.description }}</p>
		</div>
		<Button
			v-if="server?.doc"
			class="whitespace-nowrap"
			@click="getServerActionHandler(props.actionLabel)"
		>
			<p
				:class="
					group === 'Dangerous Actions' ? 'text-red-600' : 'text-gray-800'
				"
			>
				{{ props.buttonLabel }}
			</p>
		</Button>
	</div>
</template>

<script setup>
import { createDocumentResource, getCachedDocumentResource } from 'frappe-ui';
import { h } from 'vue';
import { toast } from 'vue-sonner';
import router from '../../router';
import { confirmDialog, renderDialog } from '../../utils/components';
import { getToastErrorMessage } from '../../utils/toast';
import CommunicationInfoDialog from '../CommunicationInfoDialog.vue';
import CleanupDialog from './CleanupDialog.vue';
import DatabaseBinlogsDialog from './DatabaseBinlogsDialog.vue';
import DatabaseConfigurationDialog from './DatabaseConfigurationDialog.vue';
import SecondaryServerPlanDialog from './SecondaryServerPlanDialog.vue';

const props = defineProps({
	serverName: { type: String, required: true },
	serverType: { type: String, required: true },
	actionLabel: { type: String, required: true },
	method: { type: String, required: true },
	description: { type: String, required: true },
	buttonLabel: { type: String, required: true },
	group: { type: String, required: false },
});

const server = getCachedDocumentResource(props.serverType, props.serverName);

function getServerActionHandler(action) {
	const actionHandlers = {
		'Notification Settings': onNotificationSettings,
		'Reboot server': onRebootServer,
		'Rename server': onRenameServer,
		'Drop server': onDropServer,
		'Cleanup Server': onCleanupServer,
		'Enable Autoscale': onSetupSecondaryServer,
		'Disable Autoscale': onTeardownSecondaryServer,
		'Enable Performance Schema': onEnablePerformanceSchema,
		'Disable Performance Schema': onDisablePerformanceSchema,
		'Enable Binlog Indexer': onEnableBinlogIndexing,
		'Disable Binlog Indexer': onDisableBinlogIndexing,
		'Update InnoDB Buffer Pool Size': onUpdateInnodbBufferPoolSize,
		'Update Max DB Connections': onUpdateMaxDBConnections,
		'View Database Configuration': onViewDatabaseConfiguration,
		'Update Binlog Retention': onUpdateBinlogRetention,
		'Update Binlog Size Limit': onUpdateBinlogSizeLimit,
		'Manage Database Binlogs': onViewMariaDBBinlogs,
	};
	if (actionHandlers[action]) {
		actionHandlers[action].call(this);
	}
}

function onNotificationSettings() {
	if (!server?.doc) return;
	return renderDialog(
		h(CommunicationInfoDialog, {
			referenceDoctype: 'Server',
			referenceName: server.doc.name,
		}),
	);
}

function onCleanupServer() {
	renderDialog(
		h(CleanupDialog, {
			server: server,
			title: 'Server Cleanup',
		}),
	);
}

function onTeardownSecondaryServer() {
	confirmDialog({
		title: 'Remove Secondary Application Server',
		message: `
		<p>
			You're about to <strong>remove your Secondary Application Server</strong> and 
			<strong>disable auto-scaling</strong>.
			Once this begins, the secondary server will enter a <strong>Installing</strong> state
			while it is being removed.
		</p>

		<div class="mt-3 rounded-md bg-gray-50 border border-gray-200 p-3 text-sm">
			<div class="p-2">
				<p>
					This action <strong>archives the secondary server instance and fully disables auto-scaling</strong> until a new secondary server is set up.
				</p>

				<p class="mt-3">
					After teardown, autoscaling will <strong>not trigger</strong> unless you configure a new secondary server.
				</p>

				<p class="mt-3">
					See the docs to learn more about autoscaling:<br>
					<a href="https://docs.frappe.io/cloud/application-server-horizontal-scaling#opting-out"
					target="_blank" rel="noopener" style="text-decoration: underline;">
					<strong>Secondary Server Teardown Guide</strong>
					</a>
				</p>


		</div>

		</div>
		`,
		primaryAction: {
			label: 'Teardown',
		},
		onSuccess({ hide }) {
			toast.promise(
				server.teardownSecondaryServer.submit(null, {
					onSuccess() {
						this.$router.push({
							path: server,
							path: 'plays',
						});
						hide();
					},
				}),
				{
					loading: 'Tearing down secondary server...',
					success: 'Secondary server teardown started',
					error: (error) =>
						error.messages.length
							? error.messages.join('\n')
							: 'Failed to drop servers',
				},
			);
		},
	});
}

function onSetupSecondaryServer() {
	confirmDialog({
		title: 'Setup Secondary Application Server',
		message: `
		<p>
			You're about to <strong>provision a Secondary Application Server</strong> for auto-scaling.
			This will put the server into an <strong>Installing</strong> state while the setup runs.
			Your server will become active once all the setup is completed, this might take some time depending on the
			number and size of the benches on the server.
		</p>

		<div class="mt-3 rounded-md bg-gray-50 border border-gray-200 text-sm">
			<div class="p-2">
				<p>
					Select a <strong>secondary server plan</strong> — this is the plan the secondary server will run on.  
					The secondary plan must have <strong>higher compute</strong> than your current plan (CPU / memory).
				</p>

				<p class="mt-3">
					After setup, the secondary server will remain in <em>standby</em> (inactive) until autoscaling or manual activation.
				</p>


				<p class="mt-3">
					See the docs to learn more about autoscaling:<br>
					<a href="https://docs.frappe.io/cloud/application-server-horizontal-scaling#setting-up-a-secondary-server"
					target="_blank" rel="noopener" style="text-decoration: underline;">
					<strong>Secondary Server Setup Guide</strong>
					</a>
				</p>
		</div>

		</div>
  		`,
		primaryAction: {
			label: 'Choose Plan',
		},
		onSuccess({ hide, values }) {
			hide();
			renderDialog(
				h(SecondaryServerPlanDialog, {
					server: server.doc.name,
				}),
			);
		},
	});
}

function onRebootServer() {
	confirmDialog({
		title: 'Reboot Server',
		message: `Are you sure you want to reboot the server <b>${server.doc.name}</b>?`,
		fields: [
			{
				label: 'Please type the server name to confirm',
				fieldname: 'confirmServerName',
			},
		],
		primaryAction: {
			label: 'Reboot Server',
		},
		onSuccess({ hide, values }) {
			if (server.reboot.loading) return;
			if (values.confirmServerName !== server.doc.name) {
				throw new Error('Server name does not match');
			}
			toast.promise(
				server.reboot.submit(null, {
					onSuccess() {
						hide();
					},
				}),
				{
					loading: 'Rebooting...',
					success: 'Server rebooted',
					error: 'Failed to reboot server',
				},
			);
		},
	});
}

function onRenameServer() {
	confirmDialog({
		title: 'Rename Server',
		fields: [
			{
				label: 'Enter new title for the server',
				fieldname: 'title',
			},
		],
		primaryAction: {
			label: 'Rename',
		},
		onSuccess({ hide, values }) {
			if (server.rename.loading) return;
			toast.promise(
				server.rename.submit(
					{
						title: values.title,
					},
					{
						onSuccess() {
							hide();
						},
					},
				),
				{
					loading: 'Updating title...',
					success: 'Title updated',
					error: 'Failed to update title',
				},
			);
		},
	});
}

function onEnableAutoDiskExpansion() {
	confirmDialog({
		title: 'Enable automatic storage disk expansion',
		message: `<div class="prose text-base">Enable auto add on storage?</div>`,
		primaryAction: {
			label: 'Enable',
		},
		onSuccess({ hide, values }) {
			if (server.toggleAutoIncreaseStorage.loading) return;
			toast.promise(
				server.toggleAutoIncreaseStorage.submit(
					{ enable: true },
					{
						onSuccess() {
							hide();
						},
					},
				),
				{
					loading: 'Enabling auto disk expansion...',
					success: 'Enabling',
					error: 'Failed to enable auto disk expansion',
				},
			);
		},
	});
}

function onDisableAutoDiskExpansion() {
	confirmDialog({
		title: 'Disable automatic storage disk expansion',
		message: `<div class="prose text-base">Disable auto add on storage?<br>This can effect server uptime <a href="https://docs.frappe.io/cloud/storage-addons">Know more</a></br></div>`,
		primaryAction: {
			label: 'Disable',
			theme: 'red',
		},
		onSuccess({ hide, values }) {
			if (server.toggleAutoIncreaseStorage.loading) return;
			toast.promise(
				server.toggleAutoIncreaseStorage.submit(
					{ enable: false },
					{
						onSuccess() {
							hide();
						},
					},
				),
				{
					loading: 'Disabling auto disk expansion...',
					success: 'Disabled',
					error: 'Failed to disable auto disk expansion',
				},
			);
		},
	});
}

function onDropServer() {
	const databaseServer = createDocumentResource({
		doctype: 'Database Server',
		name: server.doc.database_server,
	});

	confirmDialog({
		title: 'Drop Server',
		message: server.doc.is_unified_server
			? `<div class="prose text-base">Are you sure you want to drop your unified server?<br><br>The following server will be dropped<ul><li>${server.doc.title} (<b>${server.doc.name}</b>)</li></ul><br>This action cannot be undone.</div>`
			: `<div class="prose text-base">Are you sure you want to drop your servers?<br><br>Following servers will be dropped<ul><li>${server.doc.title} (<b>${server.doc.name}</b>)</li><li>${databaseServer.doc.title} (<b>${server.doc.database_server}</b>)</li></ul><br>This action cannot be undone.</div>`,
		fields: [
			{
				label: "Please type either server's name or title to confirm",
				fieldname: 'confirmServerName',
			},
		],
		primaryAction: {
			label: 'Drop Server',
			theme: 'red',
		},
		onSuccess({ hide, values }) {
			if (server.dropServer.loading) return;
			if (
				values.confirmServerName !== server.doc.name &&
				values.confirmServerName !== server.doc.database_server &&
				values.confirmServerName.trim() !== server.doc.title.trim() &&
				values.confirmServerName.trim() !== databaseServer.doc.title.trim()
			) {
				throw new Error('Server name does not match');
			}
			toast.promise(server.dropServer.submit().then(hide), {
				loading: 'Dropping...',
				success: () => {
					router.push({ name: 'Server List' });
					return 'Server dropped';
				},
				error: (error) =>
					error.messages.length
						? error.messages.join('\n')
						: 'Failed to drop servers',
			});
		},
	});
}

function onEnableBinlogIndexing() {
	if (!server.enableBinlogIndexing) return;
	confirmDialog({
		title: 'Enable Binlog Indexing',
		message: `Are you sure you want to enable the Binlog Indexing on the database server <b>${server.doc.name}</b> ?<br><br><b>Note:</b> Binlog indexes will consume additional disk space (10% of total binlog size). It can take upto 1 day to index existing binlogs depending on the size of binlogs.`,
		primaryAction: {
			label: 'Enable Binlog Indexing',
		},
		onSuccess({ hide }) {
			if (server.enableBinlogIndexing.loading) return;
			toast.promise(
				server.enableBinlogIndexing.submit(null, {
					onSuccess() {
						hide();
					},
				}),
				{
					loading: 'Enabling Binlog Indexing...',
					success: 'Binlog Indexing enabled',
					error: 'Failed to enable Binlog Indexing',
				},
			);
		},
	});
}

function onDisableBinlogIndexing() {
	if (!server.disableBinlogIndexing) return;
	confirmDialog({
		title: 'Disable Binlog Indexing',
		message: `Are you sure you want to disable the Binlog Indexing on the database server <b>${server.doc.name}</b> ?<br><br><b>Note:</b> Disabling binlog indexing will remove all existing binlog indexes from the server.`,
		primaryAction: {
			label: 'Disable Binlog Indexing',
		},
		onSuccess({ hide }) {
			if (server.disableBinlogIndexing.loading) return;
			toast.promise(
				server.disableBinlogIndexing.submit(null, {
					onSuccess() {
						hide();
					},
				}),
				{
					loading: 'Disabling Binlog Indexing...',
					success: 'Binlog Indexing disabled',
					error: 'Failed to disable Binlog Indexing',
				},
			);
		},
	});
}

function onEnablePerformanceSchema() {
	if (!server.enablePerformanceSchema) return;
	confirmDialog({
		title: 'Enable Performance Schema',
		message: `Are you sure you want to enable the Performance Schema on the database server <b>${server.doc.name}</b> ?<br><br><b>Note:</b> Your database server will be restarted to apply the changes. Your sites will face few minutes of downtime.`,
		fields: [
			{
				label: 'Please type the server name to confirm',
				fieldname: 'confirmServerName',
			},
		],
		primaryAction: {
			label: 'Enable Performance Schema',
		},
		onSuccess({ hide, values }) {
			if (server.enablePerformanceSchema.loading) return;
			if (values.confirmServerName !== server.doc.name) {
				throw new Error('Server name does not match');
			}
			toast.promise(
				server.enablePerformanceSchema.submit(null, {
					onSuccess() {
						hide();
					},
				}),
				{
					loading: 'Enabling Performance Schema...',
					success: 'Performance Schema enabled',
					error: 'Failed to enable Performance Schema',
				},
			);
		},
	});
}

function onDisablePerformanceSchema() {
	if (!server.disablePerformanceSchema) return;
	confirmDialog({
		title: 'Disable Performance Schema',
		message: `Are you sure you want to disable the Performance Schema on the database server <b>${server.doc.name}</b> ?<br><br><b>Note:</b> Your database server will be restarted to apply the changes. Your sites will face few minutes of downtime.`,
		fields: [
			{
				label: 'Please type the server name to confirm',
				fieldname: 'confirmServerName',
			},
		],
		primaryAction: {
			label: 'Disable Performance Schema',
		},
		onSuccess({ hide, values }) {
			if (server.disablePerformanceSchema.loading) return;
			if (values.confirmServerName !== server.doc.name) {
				throw new Error('Server name does not match');
			}
			toast.promise(
				server.disablePerformanceSchema.submit(null, {
					onSuccess() {
						hide();
					},
				}),
				{
					loading: 'Disabling Performance Schema...',
					success: 'Performance Schema disabled',
					error: 'Failed to disable Performance Schema',
				},
			);
		},
	});
}

function onUpdateInnodbBufferPoolSize() {
	if (!server.updateInnodbBufferPoolSize) return;
	confirmDialog({
		title: 'Update InnoDB Buffer Pool Size',
		message: `Are you sure you want to change the InnoDB Buffer Pool Size of the database server <b>${server.doc.name}</b> ? <br><br> Recommended Buffer Pool Size is <b>${server.doc.mariadb_variables_recommended_values.innodb_buffer_pool_size} MB</b>`,
		fields: [
			{
				label: 'Enter the new InnoDB Buffer Pool Size (MB)',
				fieldname: 'innodbBufferPoolSize',
				type: 'number',
				default: server.doc.mariadb_variables.innodb_buffer_pool_size,
			},
		],
		primaryAction: {
			label: 'Update InnoDB Buffer Pool Size',
		},
		onSuccess({ hide, values }) {
			if (server.updateInnodbBufferPoolSize.loading) return;
			toast.promise(
				server.updateInnodbBufferPoolSize.submit(
					{
						size_mb: parseInt(values.innodbBufferPoolSize),
					},
					{
						onSuccess() {
							hide();
						},
					},
				),
				{
					loading: 'Updating InnoDB Buffer Pool Size...',
					success: 'InnoDB Buffer Pool Size updated',
					error: () =>
						getToastErrorMessage(
							server.updateInnodbBufferPoolSize.error ||
								'Failed to update InnoDB Buffer Pool Size',
						),
					duration: 5000,
				},
			);
		},
	});
}

function onUpdateBinlogRetention() {
	if (!server.updateBinlogRetention) return;
	confirmDialog({
		title: 'Update Binlog Retention',
		message: `Are you sure you want to change the Binlog Retention of the database server <b>${server.doc.name}</b> ? <br><br> Recommended Binlog Retention is <b>${server.doc.mariadb_variables_recommended_values.expire_logs_days} days</b>`,
		fields: [
			{
				label: 'Enter the new Binlog Retention (days)',
				fieldname: 'days',
				type: 'number',
				default: server.doc.mariadb_variables.expire_logs_days,
			},
		],
		primaryAction: {
			label: 'Update Binlog Retention',
		},
		onSuccess({ hide, values }) {
			if (server.updateBinlogRetention.loading) return;
			toast.promise(
				server.updateBinlogRetention.submit(
					{
						days: parseInt(values.days),
					},
					{
						onSuccess() {
							hide();
						},
					},
				),
				{
					loading: 'Updating Binlog Retention...',
					success: 'Binlog Retention updated',
					error: () =>
						getToastErrorMessage(
							server.updateBinlogRetention.error ||
								'Failed to update Binlog Retention',
						),
					duration: 5000,
				},
			);
		},
	});
}

function onUpdateBinlogSizeLimit() {
	if (!server.updateBinlogSizeLimit) return;
	confirmDialog({
		title: 'Update Binlog Size Limit',
		message: `You can limit the amount of space that binlog can use at max. If the size exceeds the limit, the oldest binlog files will be deleted automatically.`,
		fields: [
			{
				label: 'Enable Binlog Auto Purging',
				fieldname: 'enabled',
				type: 'checkbox',
				default: server.doc.auto_purge_binlog_based_on_size,
			},
			{
				label: 'Percent of disk space can be used by binlog (10-90)',
				fieldname: 'size',
				type: 'number',
				default: server.doc.binlog_max_disk_usage_percent,
				condition: (values) => values.enabled,
			},
		],
		primaryAction: {
			label: 'Update Binlog Size Limit',
		},
		onSuccess({ hide, values }) {
			if (server.updateBinlogSizeLimit.loading) return;
			toast.promise(
				server.updateBinlogSizeLimit.submit(
					{
						enabled: values.enabled,
						percent_of_disk_size: parseInt(values.size),
					},
					{
						onSuccess() {
							hide();
						},
					},
				),
				{
					loading: 'Updating Binlog Size Limit...',
					success: 'Binlog Size Limit updated',
					error: () =>
						getToastErrorMessage(
							server.updateBinlogSizeLimit.error ||
								'Failed to update Binlog Size Limit',
						),
					duration: 5000,
				},
			);
		},
	});
}

function onViewMariaDBBinlogs() {
	if (!server.getBinlogsInfo) return;
	renderDialog(
		h(DatabaseBinlogsDialog, {
			databaseServer: server.doc.name,
		}),
	);
}

function onUpdateMaxDBConnections() {
	if (!server.updateMaxDbConnections) return;
	confirmDialog({
		title: 'Update Max DB Connections',
		message: `Are you sure you want to change the Max DB Connections of the database server <b>${server.doc.name}</b> ?<br><br> Recommended Max DB Connections is <b>${server.doc.mariadb_variables_recommended_values.max_connections}</b>`,
		fields: [
			{
				label: 'Enter the new Max DB Connections',
				fieldname: 'maxDBConnections',
				type: 'number',
				default: server.doc.mariadb_variables.max_connections,
			},
		],
		primaryAction: {
			label: 'Update Max DB Connections',
		},
		onSuccess({ hide, values }) {
			if (server.updateMaxDbConnections.loading) return;
			toast.promise(
				server.updateMaxDbConnections.submit(
					{
						max_connections: parseInt(values.maxDBConnections),
					},
					{
						onSuccess() {
							hide();
						},
					},
				),
				{
					loading: 'Updating Max DB Connections...',
					success: 'Max DB Connections updated',
					error: () =>
						getToastErrorMessage(
							server.updateMaxDbConnections.error ||
								'Failed to update Max DB Connections',
						),
					duration: 5000,
				},
			);
		},
	});
}

function onViewDatabaseConfiguration() {
	renderDialog(
		h(DatabaseConfigurationDialog, {
			name: server.doc.name,
		}),
	);
}
</script>
