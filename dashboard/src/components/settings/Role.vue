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
	<TabButtons
		class="w-max mb-5"
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
	<RoleMembers v-if="tab === 'members'" :users="role.doc?.users" />
	<RoleResources
		v-else-if="tab === 'resources'"
		:resources="role.doc?.resources"
	/>
	<RolePermissions
		v-else-if="tab === 'permissions'"
		:allow_bench_creation="role.doc?.allow_bench_creation"
		:allow_billing="role.doc?.allow_billing"
		:allow_partner="role.doc?.allow_partner"
		:allow_server_creation="role.doc?.allow_server_creation"
		:allow_site_creation="role.doc?.allow_site_creation"
		:allow_webhook_configuration="role.doc?.allow_webhook_configuration"
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
	// whitelistedMethods: {
	// 	addUser: 'add_user',
	// 	removeUser: 'remove_user',
	// 	bulkDelete: 'delete_permissions',
	// },
});
</script>
