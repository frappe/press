<template>
	<div class="mb-5 flex items-center gap-2">
		<Tooltip text="All Roles">
			<Button :route="{ name: 'SettingsPermissionRoles' }">
				<template #icon>
					<lucide-arrow-left class="h-4 w-4 text-gray-700" />
				</template>
			</Button>
		</Tooltip>
		<h3 class="text-lg font-medium text-gray-900">
			{{ role.doc?.title }}
		</h3>
		<Tooltip text="Admin Role" v-if="role.doc?.admin_access">
			<FeatherIcon name="shield" class="h-5 w-5 text-gray-700" />
		</Tooltip>
	</div>
	<div class="flex items-center justify-between mb-5">
		<TabButtons
			class="w-max"
			v-model="tab"
			:buttons="[
				{
					label: 'Members',
					value: 'members',
				},
				{
					label: 'Resources',
					value: 'resources',
				},
				{
					label: 'Permissions',
					value: 'permissions',
				},
			]"
		/>
		<Button
			label="Delete"
			icon-left="trash-2"
			theme="red"
			variant="subtle"
			@click="
				confirmDialog({
					title: 'Delete',
					message: 'Are you sure you want to delete this role?',
					primaryAction: {
						label: 'Delete',
						theme: 'red',
						onClick: ({ hide }) => {
							role.delete.submit().then(() => {
								hide();
								$router.push({ name: 'SettingsPermissionRoles' });
							});
						},
					},
				})
			"
		/>
	</div>
	<RoleMembers
		v-if="tab === 'members'"
		:users="role.doc?.users"
		@add="
			(id: string) => {
				role.add_user.submit({
					user: id,
				});
			}
		"
		@remove="
			(id: string) => {
				role.remove_user.submit({
					user: id,
				});
			}
		"
	/>
	<RoleResources
		v-else-if="tab === 'resources'"
		:key="role.doc?.resources"
		:resources="role.doc?.resources"
		@include="role.add_resource.submit($event)"
		@remove="
			(document_type, document_name) => {
				role.remove_resource.submit({
					document_type,
					document_name,
				});
				role.reload();
			}
		"
	/>
	<RolePermissions
		v-else-if="tab === 'permissions'"
		:admin_access="role.doc?.admin_access"
		:all_servers="role.doc?.all_servers"
		:all_sites="role.doc?.all_sites"
		:all_release_groups="role.doc?.all_release_groups"
		:allow_bench_creation="role.doc?.allow_bench_creation"
		:allow_apps="role.doc?.allow_apps"
		:allow_billing="role.doc?.allow_billing"
		:allow_partner="role.doc?.allow_partner"
		:allow_server_creation="role.doc?.allow_server_creation"
		:allow_site_creation="role.doc?.allow_site_creation"
		:allow_webhook_configuration="role.doc?.allow_webhook_configuration"
		:allow_dashboard="role.doc?.allow_dashboard"
		:allow_customer="role.doc?.allow_customer"
		:allow_leads="role.doc?.allow_leads"
		:allow_contribution="role.doc?.allow_contribution"
		:disabled="user != team.doc?.user"
		@update="
			(key: string, value: boolean) => {
				role.setValueDebounced.submit({
					[key]: value,
				});
			}
		"
	/>
</template>

<script setup lang="ts">
import { ref } from 'vue';
import { Button, TabButtons, createDocumentResource } from 'frappe-ui';
import RoleMembers from './RoleMembers.vue';
import RolePermissions from './RolePermissions.vue';
import RoleResources from './RoleResources.vue';
import { getTeam } from '../../data/team';
import { getSessionUser } from '../../data/session';
import { confirmDialog } from '../../utils/components';

const props = defineProps<{
	id: string;
}>();

const team = getTeam();
const user = getSessionUser();
const tab = ref<'members' | 'resources' | 'permissions'>('members');

const role = createDocumentResource({
	doctype: 'Press Role',
	name: props.id,
	auto: true,
	whitelistedMethods: {
		add_user: 'add_user',
		remove_user: 'remove_user',
		add_resource: 'add_resource',
		remove_resource: 'remove_resource',
	},
});
</script>
