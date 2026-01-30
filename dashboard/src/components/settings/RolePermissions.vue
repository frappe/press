<template>
	<div class="space-y-4">
		<div class="space-y-2">
			<div class="font-medium text-lg">Important</div>
			<div class="grid grid-cols-3 gap-4 text-base">
				<div v-for="permission in permissionsImportant">
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
		</div>
		<div class="space-y-2">
			<div class="font-medium text-lg">General</div>
			<div class="grid grid-cols-3 gap-4 text-base">
				<div v-for="permission in permissionsGeneral">
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
		</div>
		<div class="space-y-2">
			<div class="font-medium text-lg">Partner</div>
			<div class="grid grid-cols-3 gap-4 text-base">
				<div v-for="permission in permissionsPartner">
					<div class="px-5 py-4 border rounded">
						<Switch
							size="sm"
							:disabled="disabled || !$props.allow_partner"
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
		</div>
	</div>
</template>

<script setup lang="ts">
import { Switch } from 'frappe-ui';

withDefaults(
	defineProps<{
		admin_access?: number;
		allow_bench_creation?: number;
		allow_apps?: number;
		allow_billing?: number;
		allow_partner?: number;
		allow_server_creation?: number;
		allow_site_creation?: number;
		allow_webhook_configuration?: number;
		allow_dashboard?: number;
		allow_customer?: number;
		allow_leads?: number;
		allow_contribution?: number;
		disabled?: boolean;
	}>(),
	{
		admin_access: 0,
		allow_bench_creation: 0,
		allow_apps: 0,
		allow_billing: 0,
		allow_partner: 0,
		allow_server_creation: 0,
		allow_site_creation: 0,
		allow_webhook_configuration: 0,
		allow_dashboard: 0,
		allow_customer: 0,
		allow_leads: 0,
		allow_contribution: 0,
		disabled: false,
	},
);

defineEmits<{
	update: [key: string, value: boolean];
}>();

const permissionsImportant = [
	{
		key: 'admin_access',
		label: 'Admin',
		description: 'Grants full administrative access',
	},
];

const permissionsGeneral = [
	{
		key: 'allow_site_creation',
		label: 'Site',
		description: 'Enables site creation',
	},
	{
		key: 'allow_apps',
		label: 'Apps',
		description: 'Enables marketplace management',
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

const permissionsPartner = [
	{
		key: 'allow_dashboard',
		label: 'Dashboard',
		description: 'Enables access to dashboard features for Partner',
	},
	{
		key: 'allow_customer',
		label: 'Customer',
		description: 'Enables access to customer features for Partner',
	},
	{
		key: 'allow_leads',
		label: 'Leads',
		description: 'Enables access to leads features for Partner',
	},
	{
		key: 'allow_contribution',
		label: 'Contribution',
		description: 'Enables access to contribution features for Partner',
	},
];
</script>
