<template>
	<div class="grid grid-cols-3 gap-4 text-base">
		<div v-for="permission in permissions">
			<div class="px-5 py-4 border rounded">
				<Switch
					size="sm"
					:disabled="disabled"
					:label="permission.label"
					:description="permission.description"
					:model-value="$props[permission.key]"
					@update:model-value="
						(value: boolean) => $emit('update', permission.key, value)
					"
				/>
			</div>
		</div>
	</div>
</template>

<script setup lang="ts">
import { Switch } from 'frappe-ui';

withDefaults(
	defineProps<{
		allow_bench_creation?: number;
		allow_billing?: number;
		allow_partner?: number;
		allow_server_creation?: number;
		allow_site_creation?: number;
		allow_webhook_configuration?: number;
		disabled?: boolean;
	}>(),
	{
		allow_bench_creation: 0,
		allow_billing: 0,
		allow_partner: 0,
		allow_server_creation: 0,
		allow_site_creation: 0,
		allow_webhook_configuration: 0,
		disabled: false,
	},
);

defineEmits<{
	update: [key: string, value: boolean];
}>();

const permissions = [
	{
		key: 'allow_site_creation',
		label: 'Site',
		description: 'Enables site creation',
	},
	{
		key: 'allow_server_creation',
		label: 'Server',
		description: 'Enables server creation',
	},
	{
		key: 'allow_bench_creation',
		label: 'Release Group',
		description: 'Enables release group creation',
	},
	{
		key: 'allow_webhook_configuration',
		label: 'Webhook',
		description: 'Enables webhook configuration',
	},
	{
		key: 'allow_billing',
		label: 'Billing',
		description: 'Enables access to billing features',
	},
	{
		key: 'allow_partner',
		label: 'Partner',
		description: 'Enables access to partner features',
	},
];
</script>
