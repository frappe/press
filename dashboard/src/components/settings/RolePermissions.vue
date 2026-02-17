<template>
	<div class="space-y-8">
		<div class="space-y-2">
			<div class="font-medium text-lg">Important</div>
			<div class="grid grid-cols-5 gap-2 text-base">
				<div v-for="permission in permissionsImportant">
					<div class="border rounded">
						<Switch
							size="sm"
							:disabled="disabled"
							:label="permission.label"
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
			<div class="grid grid-cols-5 gap-2 text-base">
				<div v-for="permission in permissionsGeneral">
					<div class="border rounded">
						<Switch
							size="sm"
							:disabled="disabled"
							:label="permission.label"
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
			<div class="grid grid-cols-5 gap-2 text-base">
				<div v-for="permission in permissionsPartner">
					<div class="border rounded">
						<Switch
							size="sm"
							:disabled="disabled || !$props.allow_partner"
							:label="permission.label"
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
		label: 'Administrator',
	},
];

const permissionsGeneral = [
	{
		key: 'allow_server_creation',
		label: 'Create Servers',
	},
	{
		key: 'allow_site_creation',
		label: 'Create Sites',
	},
	{
		key: 'allow_bench_creation',
		label: 'Create Release Groups',
	},
	{
		key: 'allow_apps',
		label: 'Marketplace',
	},
	{
		key: 'allow_webhook_configuration',
		label: 'Webhooks',
	},
	{
		key: 'allow_billing',
		label: 'Billing',
	},
	{
		key: 'allow_partner',
		label: 'Partner Management',
	},
];

const permissionsPartner = [
	{
		key: 'allow_dashboard',
		label: 'Dashboard',
	},
	{
		key: 'allow_customer',
		label: 'Customer',
	},
	{
		key: 'allow_leads',
		label: 'Leads',
	},
	{
		key: 'allow_contribution',
		label: 'Contribution',
	},
];
</script>
