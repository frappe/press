<script setup lang="ts">
import {
	Badge,
	Button,
	createResource,
	Dialog,
	FormControl,
	Switch,
} from 'frappe-ui'
import { computed, ref, watchEffect } from 'vue'
import { toast } from 'vue-sonner'
import AlertBanner from '@/components/AlertBanner.vue'
import { getTeam } from '@/data/team'
import { getToastErrorMessage } from '@/utils/toast'

const team = getTeam()

// ─── Role definition ──────────────────────────────────────────────────
interface Role {
	label: string
	value: string
	name?: string | null
	is_predefined: boolean
	admin_access: boolean
	allow_apps: boolean
	allow_bench_creation: boolean
	allow_billing: boolean
	allow_contribution: boolean
	allow_customer: boolean
	allow_dashboard: boolean
	allow_leads: boolean
	allow_partner: boolean
	allow_server_creation: boolean
	allow_site_creation: boolean
	allow_webhook_configuration: boolean
	all_release_groups: boolean
	all_servers: boolean
	all_sites: boolean
}

// ─── Fetch roles ──────────────────────────────────────────────────────
const rolesResource = createResource({
	url: 'run_doc_method',
	auto: false,
	makeParams: () => ({
		method: 'get_roles',
		dt: 'Team',
		dn: team.doc?.name,
	}),
	transform: (d: any) => d.message as Role[],
})

watchEffect(() => {
	if (team.doc?.name) {
		rolesResource.fetch()
	}
})

const roles = computed(() => rolesResource.data ?? [])

// ─── Permission display helpers ───────────────────────────────────────
interface PermissionDef {
	key: string
	label: string
	color: string
}

const PERMISSION_DEFS: PermissionDef[] = [
	{ key: 'admin_access', label: 'Admin', color: 'red' },
	{ key: 'allow_site_creation', label: 'Create Sites', color: 'green' },
	{
		key: 'allow_bench_creation',
		label: 'Create Release Groups',
		color: 'green',
	},
	{ key: 'allow_server_creation', label: 'Create Servers', color: 'green' },
	{ key: 'allow_billing', label: 'Billing', color: 'blue' },
	{ key: 'allow_apps', label: 'Marketplace', color: 'blue' },
	{ key: 'allow_webhook_configuration', label: 'Webhooks', color: 'orange' },
	{ key: 'allow_partner', label: 'Partner Management', color: 'orange' },
]

const enabledPermissions = (role: Role) =>
	PERMISSION_DEFS.filter((p) => (role as any)[p.key])

// ─── Detail dialog ────────────────────────────────────────────────────
const showDetailDialog = ref(false)
const selectedRole = ref<Role | null>(null)

const openRoleDetail = (role: Role) => {
	selectedRole.value = role
	showDetailDialog.value = true
}

// ─── Permission editing (custom roles only) ───────────────────────────
const setValueResource = createResource({
	url: 'press.api.client.set_value',
})

const updatePermission = (key: string, value: boolean) => {
	if (
		!selectedRole.value ||
		selectedRole.value.is_predefined ||
		!selectedRole.value.name
	)
		return

	setValueResource.submit(
		{
			doctype: 'Press Role',
			name: selectedRole.value.name,
			fieldname: key,
			value: value ? 1 : 0,
		},
		{
			onSuccess: () => {
				;(selectedRole.value as any)[key] = value
				rolesResource.reload()
				const label =
					PERMISSION_DEFS.find((p) => p.key === key)?.label ??
					key.replace(/_/g, ' ')
				toast.success(`${label} updated`)
			},
			onError: (e: any) => toast.error(getToastErrorMessage(e)),
		},
	)
}

// ─── Create Role ──────────────────────────────────────────────────────
const showCreateDialog = ref(false)
const newRoleName = ref('')

const createRoleResource = createResource({
	url: 'press.api.client.insert',
	onSuccess: () => {
		showCreateDialog.value = false
		newRoleName.value = ''
		rolesResource.reload()
		toast.success('Role created successfully')
	},
	onError: (e: any) => toast.error(getToastErrorMessage(e)),
})

const createRole = () => {
	const title = newRoleName.value.trim()
	if (!title) return
	createRoleResource.submit({
		doc: {
			doctype: 'Press Role',
			title,
			team: team.doc?.name,
		},
	})
}

// ─── Delete Role ──────────────────────────────────────────────────────
const deleteRoleResource = createResource({
	url: 'press.api.client.delete',
	onSuccess: () => {
		showDetailDialog.value = false
		selectedRole.value = null
		rolesResource.reload()
		toast.success('Role deleted')
	},
})

const deleteRole = () => {
	if (!selectedRole.value || !selectedRole.value.name) return
	deleteRoleResource.submit({
		doctype: 'Press Role',
		name: selectedRole.value.name,
	})
}
</script>

<template>
	<div class="space-y-5 p-5">
		<AlertBanner
			title="This page is a work in progress. It is visible to beta testers only."
			class="mb-4"
		/>

		<!-- Header -->
		<div class="flex items-center justify-between">
			<div class="space-y-2">
				<h2 class="text-2xl font-semibold text-ink-gray-9">Roles</h2>
				<p class="text-ink-gray-5 mt-1">
					Roles define what actions members of your team can perform. Customize
					permissions for each role.
				</p>
			</div>
			<Button variant="solid" icon-left="plus" @click="showCreateDialog = true">
				Create Role
			</Button>
		</div>

		<!-- Role cards -->
		<div
			v-if="roles.length"
			class="grid grid-cols-1 sm:grid-cols-2 lg:grid-cols-3 gap-4"
		>
			<div
				v-for="role in roles"
				:key="role.value"
				class="rounded-lg border p-4 space-y-3 cursor-pointer hover:shadow-lg transition-shadow bg-surface-white"
				@click="openRoleDetail(role)"
			>
				<div class="flex items-center justify-between gap-2">
					<div class="font-medium text-base truncate">{{ role.label }}</div>
					<Badge :theme="role.is_predefined ? 'blue' : 'green'">
						{{ role.is_predefined ? 'Standard' : 'Custom' }}
					</Badge>
				</div>
				<hr />
				<div class="flex flex-wrap gap-1.5 min-h-[1.5rem]">
					<Badge
						v-for="perm in enabledPermissions(role)"
						:key="perm.key"
						variant="outline"
						:theme="perm.color as any"
						:label="perm.label"
					/>
					<span
						v-if="!enabledPermissions(role).length"
						class="text-sm text-ink-gray-4"
					>
						No permissions enabled
					</span>
				</div>
			</div>
		</div>

		<!-- Empty state -->
		<div
			v-else-if="!rolesResource.loading"
			class="flex flex-col items-center justify-center py-20 text-ink-gray-5"
		>
			<LucideLock class="h-10 w-10 mb-3" />
			<p class="text-lg">No roles found</p>
			<p class="text-sm">Create a role to get started.</p>
		</div>

		<!-- Create Role Dialog -->
		<Dialog
			v-model="showCreateDialog"
			:options="{
				title: 'Create Role',
				message: 'Enter a name for the new role.',
				size: 'sm',
				actions: [
					{
						label: 'Create',
						variant: 'solid',
						onClick: createRole,
					},
				],
			}"
		>
			<template #body-content>
				<FormControl
					v-model="newRoleName"
					type="text"
					placeholder="e.g. Website Manager"
					@keydown.enter="createRole"
				/>
			</template>
		</Dialog>

		<!-- Role Detail Dialog -->
		<Dialog
			v-if="selectedRole"
			v-model="showDetailDialog"
			:options="{
				title: selectedRole!.label,
				size: 'lg',
				actions: selectedRole && !selectedRole.is_predefined
					? [
							{
								label: 'Delete',
								theme: 'red',
								variant: 'subtle',
								onClick: deleteRole,
							},
					  ]
					: [],
			}"
		>
			<template #body-content>
				<div class="space-y-6 text-base">
					<!-- Type indicator -->
					<div
						class="flex items-center gap-2 px-4 py-3 rounded border bg-surface-gray-1 text-ink-gray-7"
					>
						<LucideInfo class="size-5 shrink-0" />
						<p class="leading-5">
							<template v-if="selectedRole.is_predefined">
								This is a standard role. Its permissions are fixed and cannot be
								changed.
							</template>
							<template v-else>
								Customize the permissions for this role by toggling the switches
								below.
							</template>
						</p>
					</div>

					<!-- Important -->
					<div class="space-y-2">
						<div class="font-semibold text-sm uppercase tracking-wider">
							Important
						</div>
						<Switch
							class="px-2 h-10"
							size="sm"
							:label="'Administrator'"
							:model-value="selectedRole.admin_access"
							:disabled="selectedRole.is_predefined"
							@update:model-value="(v: boolean) => updatePermission('admin_access', v)"
						/>
					</div>

					<!-- General -->
					<div class="space-y-2">
						<hr class="mb-8 w-1/3 mx-auto" />
						<div class="font-semibold text-sm uppercase tracking-wider">
							General
						</div>
						<div class="divide-y">
							<div
								v-for="perm in [
									{ key: 'allow_site_creation', label: 'Create Sites' },
									{ key: 'allow_bench_creation', label: 'Create Release Groups' },
									{ key: 'allow_server_creation', label: 'Create Servers' },
									{ key: 'allow_apps', label: 'Marketplace' },
									{ key: 'allow_webhook_configuration', label: 'Webhooks' },
									{ key: 'allow_billing', label: 'Billing' },
									{ key: 'allow_partner', label: 'Partner Management' },
								]"
								:key="perm.key"
							>
								<Switch
									class="px-2 h-10"
									size="sm"
									:label="perm.label"
									:model-value="(selectedRole as any)[perm.key]"
									:disabled="selectedRole.is_predefined"
									@update:model-value="(v: boolean) => updatePermission(perm.key, v)"
								/>
							</div>
						</div>
					</div>

					<!-- Partner permissions (conditional) -->
					<div
						v-if="selectedRole.allow_partner && (team.doc?.erpnext_partner || team.doc?.is_desk_user)"
						class="space-y-2"
					>
						<hr class="mb-8 w-1/3 mx-auto" />
						<div class="font-semibold text-sm uppercase tracking-wider">
							Partner Permissions
						</div>
						<div class="divide-y">
							<div
								v-for="perm in [
									{ key: 'allow_dashboard', label: 'Dashboard' },
									{ key: 'allow_customer', label: 'Customer' },
									{ key: 'allow_leads', label: 'Leads' },
									{ key: 'allow_contribution', label: 'Contribution' },
								]"
								:key="perm.key"
							>
								<Switch
									class="px-2 h-10"
									size="sm"
									:label="perm.label"
									:model-value="(selectedRole as any)[perm.key]"
									:disabled="selectedRole.is_predefined"
									@update:model-value="(v: boolean) => updatePermission(perm.key, v)"
								/>
							</div>
						</div>
					</div>
				</div>
			</template>
		</Dialog>
	</div>
</template>
