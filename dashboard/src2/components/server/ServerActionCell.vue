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
import { getCachedDocumentResource, createDocumentResource } from 'frappe-ui';
import { toast } from 'vue-sonner';
import {
	confirmDialog,
	renderDialog,
	renderInDialog,
} from '../../utils/components';
import router from '../../router';
import { getToastErrorMessage } from '../../utils/toast';
import DatabaseConfigurationDialog from './DatabaseConfigurationDialog.vue';
import { h } from 'vue';

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
		'Reboot server': onRebootServer,
		'Rename server': onRenameServer,
		'Drop server': onDropServer,
		'Enable Performance Schema': onEnablePerformanceSchema,
		'Disable Performance Schema': onDisablePerformanceSchema,
		'Update InnoDB Buffer Pool Size': onUpdateInnodbBufferPoolSize,
		'Update Max DB Connections': onUpdateMaxDBConnections,
		'View Database Configuration': onViewDatabaseConfiguration,
	};
	if (actionHandlers[action]) {
		actionHandlers[action].call(this);
	}
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

function onDropServer() {
	const databaseServer = createDocumentResource({
		doctype: 'Database Server',
		name: server.doc.database_server,
	});

	confirmDialog({
		title: 'Drop Server',
		message: `<div class="prose text-base">Are you sure you want to drop your servers?<br><br>Following servers will be dropped<ul><li>${server.doc.title} (<b>${server.doc.name}</b>)</li><li>${databaseServer.doc.title} (<b>${server.doc.database_server}</b>)</li></ul><br>This action cannot be undone.</div>`,
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
