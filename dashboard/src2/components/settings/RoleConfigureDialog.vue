<template>
	<Dialog
		v-if="role.doc"
		:options="{ title: `${role.doc.title}` }"
		v-model="show"
		@after-leave="() => (this.memberEmail = '')"
	>
		<template v-slot:body-content>
			<Tabs
				class="[&>div]:pl-0"
				:tabs="[
					{
						label: 'Members',
						value: 'members'
					},
					{
						label: 'Settings',
						value: 'settings'
					}
				]"
				v-model="tabIndex"
				v-slot="{ tab }"
			>
				<div v-if="tab.value === 'members'" class="text-base">
					<div class="my-4 flex gap-2">
						<div class="flex-1">
							<Autocomplete
								:options="autoCompleteList"
								v-model="member"
								placeholder="Select a member to add"
							/>
						</div>
						<Button
							variant="solid"
							label="Add Member"
							:disabled="!member?.value"
							:loading="role.addUser?.loading"
							@click="() => addUser(member.value)"
						/>
					</div>
					<div class="rounded border-2 border-dashed p-3">
						<div class="mb-1 text-gray-600">Members</div>
						<div
							v-if="roleUsers.length === 0"
							class="p-4 text-center text-gray-500"
						>
							<span>No members added to this role.</span>
						</div>
						<div v-else class="flex flex-col divide-y">
							<div
								v-for="user in roleUsers"
								class="flex justify-between py-2.5"
							>
								<UserWithAvatarCell
									:avatarImage="user.user_image"
									:fullName="user.full_name"
									:email="user.user"
									:key="user.user"
								/>
								<Button @click="() => removeUser(user.user)">
									<template #icon>
										<i-lucide-x class="h-4 w-4 text-gray-600" />
									</template>
								</Button>
							</div>
						</div>
					</div>
				</div>
				<div v-else-if="tab.value === 'settings'" class="mt-4 p-2 text-base">
					<div class="flex flex-col space-y-2">
						<FormControl
							type="checkbox"
							v-model="enableBilling"
							label="Allow Access to Billing"
						/>
						<FormControl
							type="checkbox"
							v-model="enableApps"
							label="Allow Access to Apps"
						/>
						<FormControl
							type="checkbox"
							v-model="enableSiteCreation"
							label="Allow Site Creation"
						/>
						<FormControl
							type="checkbox"
							v-model="enableBenchCreation"
							label="Allow Bench Creation"
						/>
						<FormControl
							type="checkbox"
							v-model="enableServerCreation"
							label="Allow Server Creation"
						/>
					</div>
				</div>
			</Tabs>
		</template>
	</Dialog>
</template>

<script setup>
import { createDocumentResource, Tabs } from 'frappe-ui';
import { computed, ref, watch } from 'vue';
import { getTeam } from '../../data/team';
import UserWithAvatarCell from '../UserWithAvatarCell.vue';
import { toast } from 'vue-sonner';
import session from '../../data/session';

const props = defineProps({
	roleId: { type: String, required: true }
});
const member = ref({});
const show = ref(true);
const tabIndex = ref(0);

const role = createDocumentResource({
	doctype: 'Press Role',
	name: props.roleId,
	auto: true,
	whitelistedMethods: {
		addUser: 'add_user',
		removeUser: 'remove_user'
	},
	onSuccess: data => {
		enableBilling.value = !!data.enable_billing;
		enableApps.value = !!data.enable_apps;
	}
});
const roleUsers = computed(() => role.doc.users || []);
const enableBilling = ref(!!role.doc?.enable_billing);
const enableApps = ref(!!role.doc?.enable_apps);
const enableSiteCreation = ref(!!role.doc?.enable_site_creation);
const enableBenchCreation = ref(!!role.doc?.enable_bench_creation);
const enableServerCreation = ref(!!role.doc?.enable_server_creation);

// using a watcher instead of event listener to avoid multiple api calls
watch(
	[
		enableBilling,
		enableApps,
		enableSiteCreation,
		enableBenchCreation,
		enableServerCreation
	],
	([
		newEnableBilling,
		newEnableApps,
		newEnableSiteCreation,
		newEnableBenchCreation,
		newEnableServerCreation
	]) => {
		if (
			newEnableBilling === !!role.doc.enable_billing &&
			newEnableApps === !!role.doc.enable_apps &&
			newEnableSiteCreation === !!role.doc.enable_site_creation &&
			newEnableBenchCreation === !!role.doc.enable_bench_creation &&
			newEnableServerCreation === !!role.doc.enable_server_creation
		)
			return;

		role.setValue.submit(
			{
				enable_billing: newEnableBilling,
				enable_apps: newEnableApps,
				enable_site_creation: newEnableSiteCreation,
				enable_bench_creation: newEnableBenchCreation,
				enable_server_creation: newEnableServerCreation
			},
			{ onSuccess: session.roles.reload }
		);
	}
);

const team = getTeam();
const autoCompleteList = computed(() => {
	const isNotGroupMember = u =>
		!roleUsers.value.map(({ user }) => user).includes(u);
	return team.doc.team_members
		?.filter(({ user }) => isNotGroupMember(user))
		.map(({ user }) => ({ label: user, value: user }));
});

function addUser(user) {
	return toast.promise(role.addUser.submit({ user }), {
		loading: `Adding ${user} to ${role.doc.title}`,
		success: () => {
			member.value = {};
			return `${user} added to ${role.doc.title}`;
		},
		error: e => (e.messages.length ? e.messages.join('\n') : e.message)
	});
}

function removeUser(user) {
	return toast.promise(role.removeUser.submit({ user }), {
		loading: `Removing ${user} from ${role.doc.title}`,
		success: () => {
			return `${user} removed from ${role.doc.title}`;
		},
		error: e => (e.messages.length ? e.messages.join('\n') : e.message)
	});
}
</script>
