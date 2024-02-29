<template>
	<div class="flex items-center justify-between gap-1">
		<div>
			<h3 class="text-base font-medium">{{ props.actionLabel }}</h3>
			<p class="mt-1 text-p-base text-gray-600">{{ props.description }}</p>
		</div>
		<RestrictedAction
			v-if="server?.doc"
			:doctype="server.doc.doctype"
			:docname="server.doc.name"
			:method="props.method"
			:label="props.buttonLabel"
			@click="getServerActionHandler(props.actionLabel)"
		/>
	</div>
</template>

<script setup>
import { getCachedDocumentResource } from 'frappe-ui';
import { toast } from 'vue-sonner';
import RestrictedAction from '../../components/RestrictedAction.vue';
import { confirmDialog } from '../../utils/components';
import router from '../../router';

const props = defineProps({
	serverName: { type: String, required: true },
	serverType: { type: String, required: true },
	actionLabel: { type: String, required: true },
	method: { type: String, required: true },
	description: { type: String, required: true },
	buttonLabel: { type: String, required: true }
});

const server = getCachedDocumentResource(props.serverType, props.serverName);

function getServerActionHandler(action) {
	const actionHandlers = {
		'Reboot server': onRebootServer,
		'Rename server': onRenameServer,
		'Drop server': onDropServer
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
				fieldname: 'confirmServerName'
			}
		],
		primaryAction: {
			label: 'Reboot Server'
		},
		onSuccess({ hide, values }) {
			console.log(server, values.confirmServerName);
			if (server.reboot.loading) return;
			if (values.confirmServerName !== server.doc.name) {
				throw new Error('Server name does not match');
			}
			toast.promise(
				server.reboot.submit(null, {
					onSuccess() {
						hide();
					}
				}),
				{
					loading: 'Rebooting...',
					success: 'Server rebooted',
					error: 'Failed to reboot server'
				}
			);
		}
	});
}

function onRenameServer() {
	confirmDialog({
		title: 'Rename Server',
		fields: [
			{
				label: 'Enter new title for the server',
				fieldname: 'title'
			}
		],
		primaryAction: {
			label: 'Rename'
		},
		onSuccess({ hide, values }) {
			if (server.rename.loading) return;
			toast.promise(
				server.rename.submit(
					{
						title: values.title
					},
					{
						onSuccess() {
							hide();
						}
					}
				),
				{
					loading: 'Updating title...',
					success: 'Title updated',
					error: 'Failed to update title'
				}
			);
		}
	});
}

function onDropServer() {
	confirmDialog({
		title: 'Drop Server',
		message: `Are you sure you want to drop your servers?<br>Both the Application server (<b>${server.doc.name}</b>) and Database server (<b>${server.doc.database_server}</b>) will be archived.<br>This action cannot be undone.`,
		fields: [
			{
				label: 'Please type the server name to confirm',
				fieldname: 'confirmServerName'
			}
		],
		primaryAction: {
			label: 'Drop Server',
			theme: 'red'
		},
		onSuccess({ hide, values }) {
			if (server.dropServer.loading) return;
			if (
				values.confirmServerName !== server.doc.name &&
				values.confirmServerName !== server.doc.database_server
			) {
				throw new Error('Server name does not match');
			}
			toast.promise(server.dropServer.submit().then(hide), {
				loading: 'Dropping...',
				success: () => {
					router.push({ name: 'Server List' });
					return 'Server dropped';
				},
				error: 'Failed to drop server'
			});
		}
	});
}
</script>
