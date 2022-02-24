<template>
	<Card title="API Access" subtitle="API key associated with your account">
		<div v-if="$account.user.api_key">
			<p class="font-mono text-sm text-gray-800">
				<ClickToCopyField :textContent="$account.user.api_key" />
			</p>
		</div>
		<template #actions>
			<Button
				v-if="!$account.user.api_key"
				@click="showCreateSecretDialog = true"
			>
				Create New API Key
			</Button>
			<Button
				v-if="$account.user.api_key"
				@click="showCreateSecretDialog = true"
			>
				Regenerate API Secret
			</Button>
		</template>
		<Dialog
			title="API Access"
			v-model="showCreateSecretDialog"
			v-on:close="createSecretdialogClosed"
		>
			<div v-if="!$resources.createSecret.data">
				<p class="text-base">
					API key and API secret pairs can be used to access the
					<a href="/docs/api" class="underline">Frappe Cloud API</a>.
				</p>
			</div>
			<div v-if="$resources.createSecret.data">
				<p class="text-base">
					Please copy the API secret now. You won’t be able to see it again!
				</p>
				<label class="block pt-2">
					<span class="mb-2 block text-sm leading-4 text-gray-700"
						>API Key</span
					>
					<ClickToCopyField
						:textContent="$resources.createSecret.data.api_key"
					/>
				</label>
				<label class="block pt-2">
					<span class="mb-2 block text-sm leading-4 text-gray-700"
						>API Secret</span
					>
					<ClickToCopyField
						:textContent="$resources.createSecret.data.api_secret"
					/>
				</label>
			</div>
			<ErrorMessage class="mt-2" :error="$resources.createSecret.error" />
			<template #actions>
				<Button
					type="primary"
					@click="$resources.createSecret.submit()"
					v-if="!$account.user.api_key && !$resources.createSecret.data"
				>
					Create New API Key
				</Button>
				<Button
					type="primary"
					@click="$resources.createSecret.submit()"
					v-if="$account.user.api_key && !$resources.createSecret.data"
				>
					Regenerate API Secret
				</Button>
			</template>
		</Dialog>
	</Card>
</template>
<script>
import ClickToCopyField from '@/components/ClickToCopyField.vue';
export default {
	name: 'AccountAPI',
	components: {
		ClickToCopyField
	},
	data() {
		return {
			showCreateSecretDialog: false
		};
	},

	resources: {
		createSecret() {
			return {
				method: 'press.api.account.create_api_secret',
				onSuccess() {
					this.$notify({
						title: 'Created new API Secret',
						icon: 'check',
						color: 'green'
					});
				}
			};
		}
	},
	methods: {
		createSecretdialogClosed() {
			this.$account.fetchAccount();
			this.$resources.createSecret.reset();
		}
	}
};
</script>
