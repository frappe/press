<template>
	<div class="p-5">
		<div class="grid grid-cols-1 gap-5">
			<div
				class="mx-auto min-w-[48rem] max-w-3xl space-y-6 rounded-md border p-4"
			>
				<div class="flex items-center justify-between">
					<div class="text-xl font-semibold">API Access</div>
					<Button @click="showCreateSecretDialog = true">{{
						$team.doc?.user_info?.api_key
							? 'Regenerate API Secret'
							: 'Create New API Key'
					}}</Button>
				</div>
				<div v-if="$team.doc?.user_info?.api_key">
					<ClickToCopyField
						v-if="$team.doc?.user_info?.api_key"
						:textContent="$team.doc.user_info.api_key"
					/>
				</div>
				<div v-else class="pb-2 text-base text-gray-700">
					You don't have an API key yet. Click the button above to create one.
				</div>
				<Dialog
					v-model="showCreateSecretDialog"
					:options="{
						title: 'API Access',
						size: 'xl',
						actions: [
							{
								label: $team.doc.user_info.api_key
									? 'Regenerate API Secret'
									: 'Create New API Key',
								variant: 'solid',
								disabled: createSecret.data,
								loading: createSecret.loading,
								onClick() {
									createSecret.submit();
								},
							},
						],
					}"
				>
					<template #body-content>
						<div v-if="createSecret.data">
							<p class="text-base">
								Please copy the API secret now. You won’t be able to see it
								again!
							</p>
							<label class="block pt-2">
								<span class="mb-2 block text-sm leading-4 text-gray-700"
									>API Key</span
								>
								<ClickToCopyField :textContent="createSecret.data.api_key" />
							</label>
							<label class="block pt-2">
								<span class="mb-2 block text-sm leading-4 text-gray-700"
									>API Secret</span
								>
								<ClickToCopyField :textContent="createSecret.data.api_secret" />
							</label>
						</div>
						<div v-else class="text-base text-gray-700">
							API key and API secret pairs can be used to access the
							<a href="/docs/api" class="underline" target="_blank"
								>Frappe Cloud API</a
							>.
						</div>
					</template>
				</Dialog>
			</div>
			<div
				class="mx-auto min-w-[48rem] max-w-3xl space-y-6 rounded-md border p-4"
			>
				<div class="flex items-center justify-between">
					<div class="text-xl font-semibold">SSH Keys</div>
				</div>
				<ObjectList :options="sshKeyListOptions" />
			</div>
			<div
				v-if="$session.hasWebhookConfigurationAccess"
				class="mx-auto min-w-[48rem] max-w-3xl space-y-6 rounded-md border p-4"
			>
				<div class="flex items-center justify-between">
					<div class="text-xl font-semibold">Webhooks</div>
				</div>
				<ObjectList :options="webhookListOptions" />
				<AddNewWebhookDialog
					v-if="showAddWebhookDialog"
					v-model="showAddWebhookDialog"
					@success="onNewWebhookSuccess"
				/>
				<ActivateWebhookDialog
					v-if="showActivateWebhookDialog"
					v-model="showActivateWebhookDialog"
					@success="onWebHookActivated"
					:webhook="selectedWebhook"
				/>
				<EditWebhookDialog
					v-if="showEditWebhookDialog"
					v-model="showEditWebhookDialog"
					@success="onWebHookUpdated"
					:webhook="selectedWebhook"
				/>
				<WebhookAttemptsDialog
					v-if="showWebhookAttempts"
					v-model="showWebhookAttempts"
					:name="selectedWebhook.name"
				/>
			</div>
		</div>
	</div>
</template>

<script setup>
import { Badge, createResource } from 'frappe-ui';
import { toast } from 'vue-sonner';
import { computed, h, onMounted, ref } from 'vue';
import { confirmDialog, icon } from '../../utils/components';
import ObjectList from '../ObjectList.vue';
import { getTeam } from '../../data/team';
import { date } from '../../utils/format';
import ClickToCopyField from '../ClickToCopyField.vue';
import AddNewWebhookDialog from './AddNewWebhookDialog.vue';
import ActivateWebhookDialog from './ActivateWebhookDialog.vue';
import EditWebhookDialog from './EditWebhookDialog.vue';
import { useRouter } from 'vue-router';
import WebhookAttemptsDialog from './WebhookAttemptsDialog.vue';
import { session } from '../../data/session';

const $team = getTeam();
const router = useRouter();
let showCreateSecretDialog = ref(false);
const showAddWebhookDialog = ref(false);
const showActivateWebhookDialog = ref(false);
const showEditWebhookDialog = ref(false);
const showWebhookAttempts = ref(false);
const selectedWebhook = ref(null);

const createSecret = createResource({
	url: 'press.api.account.create_api_secret',
	onSuccess() {
		if ($team.doc.user_info.api_key) {
			toast.success('API Secret regenerated successfully');
		} else {
			toast.success('API Secret created successfully');
		}
	},
});

const addSSHKey = createResource({
	url: 'press.api.client.insert',
	onSuccess() {
		toast.success('SSH Key added successfully');
	},
	onError(err) {
		toast.error(
			err.messages.length
				? err.messages.join('\n')
				: 'SSH Key could not be added',
		);
	},
});

const makeKeyDefault = createResource({
	url: 'press.api.account.mark_key_as_default',
	onSuccess() {
		toast.success('SSH Key updated successfully');
	},
	onError(err) {
		toast.error(
			err.messages.length
				? err.messages.join('\n')
				: 'SSH Key could not be marked as default',
		);
	},
});

const deleteSSHKey = createResource({
	url: 'press.api.client.delete',
	onSuccess() {
		toast.success('SSH Key deleted successfully');
	},
	onError(err) {
		toast.error(
			err.messages.length
				? err.messages.join('\n')
				: 'SSH Key could not be deleted',
		);
	},
});

const sshKeyListOptions = computed(() => ({
	resource() {
		return {
			url: 'press.api.account.get_user_ssh_keys',
			initialData: [],
			auto: true,
		};
	},
	columns: [
		{
			label: 'SSH Fingerprint',
			fieldname: 'ssh_fingerprint',
			class: 'font-mono',
			format: (value) => `SHA256:${value}`,
			suffix(row) {
				return row.is_default
					? h(Badge, {
							label: 'Default',
							theme: 'green',
							class: 'ml-2',
						})
					: null;
			},
		},
		{
			label: 'Added On',
			fieldname: 'creation',
			width: 0.1,
			format: (value) => date(value, 'll'),
		},
	],
	primaryAction({ listResource }) {
		return {
			label: 'Add SSH Key',
			slots: { prefix: icon('plus') },
			onClick: () => renderAddNewKeyDialog(listResource),
		};
	},
	rowActions({ row }) {
		return [
			{
				label: 'Mark as Default',
				condition: () => !row.is_default,
				onClick() {
					makeKeyDefault.submit({
						key_name: row.name,
					});
				},
			},
			{
				label: 'Delete',
				onClick() {
					deleteSSHKey.submit({
						doctype: 'User SSH Key',
						name: row.name,
					});
				},
			},
		];
	},
}));

function renderAddNewKeyDialog(listResource) {
	confirmDialog({
		title: 'Add New SSH Key',
		message: 'Add a new SSH Key to your account',
		fields: [
			{
				label: 'SSH Key',
				fieldname: 'sshKey',
				type: 'textarea',
				placeholder:
					"Begins with 'ssh-rsa', 'ecdsa-sha2-nistp256', 'ecdsa-sha2-nistp384', 'ecdsa-sha2-nistp521', 'ssh-ed25519', 'sk-ecdsa-sha2-nistp256@openssh.com', or 'sk-ssh-ed25519@openssh.com'",
				required: true,
			},
		],
		primaryAction: {
			label: 'Add SSH Key',
			variant: 'solid',
			onClick({ hide, values }) {
				if (!values.sshKey) throw new Error('SSH Key is required');
				addSSHKey
					.submit({
						doc: {
							doctype: 'User SSH Key',
							ssh_public_key: values.sshKey,
							user: $team.doc.user_info.name,
						},
					})
					.then(() => {
						listResource.reload();
						hide();
					})
					.catch((error) => {
						toast.error(error.message);
					});
			},
		},
	});
}

const webhookListResource = createResource({
	url: 'press.api.client.get_list',
	params: {
		doctype: 'Press Webhook',
		fields: ['name', 'enabled', 'endpoint'],
	},
	initialData: [],
	auto: false,
});

const deleteWebhook = createResource({
	url: 'press.api.client.delete',
	onSuccess() {
		toast.success('Webhook deleted successfully');
		webhookListResource.reload();
	},
	onError(err) {
		toast.error(
			err.messages.length
				? err.messages.join('\n')
				: 'Webhook could not be deleted',
		);
	},
});

const webhookListOptions = computed(() => ({
	data: () => webhookListResource.data,
	columns: [
		{
			label: 'Endpoint',
			fieldname: 'endpoint',
			width: 1,
			format: (value) => value.substring(0, 50),
		},
		{
			label: 'Status',
			fieldname: 'enabled',
			width: 0.1,
			type: 'Component',
			align: 'right',
			component({ row }) {
				return row.enabled
					? h(Badge, {
							label: 'Enabled',
							theme: 'green',
						})
					: h(Badge, {
							label: 'Disabled',
							theme: 'red',
						});
			},
		},
	],
	rowActions({ row }) {
		return [
			{
				label: 'Activate',
				condition: () => !Boolean(row.enabled),
				onClick() {
					selectedWebhook.value = row;
					showActivateWebhookDialog.value = true;
				},
			},
			{
				label: 'Disable',
				condition: () => Boolean(row.enabled),
				onClick: () => {
					confirmDialog({
						title: 'Disable Webhook',
						message: `Endpoint - ${row.endpoint}<br>Are you sure you want to disable the webhook ?<br>`,
						primaryAction: {
							label: 'Disable',
							variant: 'solid',
							theme: 'red',
							onClick({ hide }) {
								disableWebhook
									.submit({
										dt: 'Press Webhook',
										dn: row.name,
										method: 'disable',
									})
									.then(hide);
								return disableWebhook.promise;
							},
						},
					});
				},
			},
			{
				label: 'Attempts',
				onClick: () => {
					selectedWebhook.value = row;
					showWebhookAttempts.value = true;
				},
			},
			{
				label: 'Edit',
				onClick() {
					selectedWebhook.value = row;
					showEditWebhookDialog.value = true;
				},
			},
			{
				label: 'Delete',
				onClick() {
					confirmDialog({
						title: 'Delete Webhook',
						message: `Endpoint - ${row.endpoint}<br>Are you sure you want to delete the webhook ?<br>`,
						primaryAction: {
							label: 'Delete',
							variant: 'solid',
							theme: 'red',
							onClick({ hide }) {
								deleteWebhook
									.submit({
										doctype: 'Press Webhook',
										name: row.name,
									})
									.then(hide);
								return deleteWebhook.promise;
							},
						},
					});
				},
			},
		];
	},
	primaryAction() {
		return {
			label: 'Add Webhook',
			slots: { prefix: icon('plus') },
			onClick: () => (showAddWebhookDialog.value = true),
		};
	},
	secondaryAction() {
		return {
			label: 'Refresh',
			icon: 'refresh-ccw',
			onClick: () => webhookListResource.reload(),
		};
	},
}));

const disableWebhook = createResource({
	url: 'press.api.client.run_doc_method',
	onSuccess() {
		toast.success('Webhook disabled successfully');
		webhookListResource.reload();
	},
	onError(err) {
		toast.error(
			err.messages.length
				? err.messages.join('\n')
				: 'Webhook could not be disabled',
		);
	},
});

const onNewWebhookSuccess = () => {
	webhookListResource.reload();
	showAddWebhookDialog.value = false;
};

const onWebHookActivated = () => {
	webhookListResource.reload();
	showActivateWebhookDialog.value = false;
};

const onWebHookUpdated = (activationRequired) => {
	webhookListResource.reload();
	showEditWebhookDialog.value = false;
	if (activationRequired) {
		showActivateWebhookDialog.value = true;
	}
};

onMounted(() => {
	if (session.hasWebhookConfigurationAccess) {
		webhookListResource.fetch();
	}
});
</script>
