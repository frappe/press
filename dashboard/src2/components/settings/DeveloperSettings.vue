<template>
	<div class="p-5">
		<div class="grid grid-cols-1 gap-5">
			<div class="space-y-6 rounded-md border p-4">
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
								}
							}
						]
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
			<div class="space-y-6 rounded-md border p-4">
				<div class="flex items-center justify-between">
					<div class="text-xl font-semibold">SSH Keys</div>
				</div>
				<ObjectList :options="sshKeyListOptions" />
			</div>
		</div>
	</div>
</template>

<script setup>
import { createResource } from 'frappe-ui';
import { toast } from 'vue-sonner';
import { computed, ref } from 'vue';
import { confirmDialog, icon } from '../../utils/components';
import ObjectList from '../ObjectList.vue';
import { getTeam } from '../../data/team';
import { date } from '../../utils/format';
import ClickToCopyField from '../../../src/components/ClickToCopyField.vue';

const $team = getTeam();
let showCreateSecretDialog = ref(false);

const createSecret = createResource({
	url: 'press.api.account.create_api_secret',
	onSuccess() {
		if ($team.doc.user_info.api_key) {
			toast.success('API Secret regenerated successfully');
		} else {
			toast.success('API Secret created successfully');
		}
	}
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
				: 'SSH Key could not be added'
		);
	}
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
				: 'SSH Key could not be marked as default'
		);
	}
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
				: 'SSH Key could not be deleted'
		);
	}
});

const sshKeyListOptions = computed(() => ({
	doctype: 'User SSH Key',
	filters: {
		user: $team.doc.user_info.name
	},
	fields: ['name', 'ssh_fingerprint', 'creation', 'is_default'],
	orderBy: 'creation desc',
	columns: [
		{
			label: 'SSH Fingerprint',
			fieldname: 'ssh_fingerprint',
			class: 'font-mono',
			format: value => `SHA256:${value}`
		},
		{
			label: 'Added On',
			fieldname: 'creation',
			width: 0.5,
			format: value => date(value, 'lll')
		},
		{
			label: 'Default',
			fieldname: 'is_default',
			type: 'Icon',
			Icon(value) {
				return value ? 'check' : '';
			},
			width: 0.1
		}
	],
	primaryAction({ listResource }) {
		return {
			label: 'Add SSH Key',
			slots: { prefix: icon('plus') },
			onClick: () => renderAddNewKeyDialog(listResource)
		};
	},
	rowActions({ row }) {
		return [
			{
				label: 'Mark as Default',
				icon: 'check',
				condition: () => !row.is_default,
				onClick() {
					makeKeyDefault.submit({
						key_name: row.name
					});
				}
			},
			{
				label: 'Delete',
				icon: 'trash-2',
				onClick() {
					deleteSSHKey.submit({
						doctype: 'User SSH Key',
						name: row.name
					});
				}
			}
		];
	}
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
				required: true
			}
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
							user: $team.doc.user_info.name
						}
					})
					.then(() => {
						listResource.reload();
						hide();
					})
					.catch(error => {
						toast.error(error.message);
					});
			}
		}
	});
}
</script>
