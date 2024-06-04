<template>
	<Dialog
		v-if="role.doc"
		:options="{ title: `${role.doc.title}` }"
		v-model="show"
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
				<div v-else-if="tab.value === 'settings'" class="mt-4 text-base">
					<div class="flex flex-col space-y-3">
						<Switch
							v-model="allowBilling"
							label="Allow Billing Access"
							description="Grant users belonging to this role access to billing page"
						/>
						<Switch
							v-model="allowApps"
							label="Allow Apps Access"
							description="Grant users belonging to this role access to apps page"
						/>
						<Switch
							v-model="allowSiteCreation"
							label="Allow Site Creation"
							description="Newly created sites will be given access to users of this role"
						/>
						<Switch
							v-model="allowBenchCreation"
							label="Allow Bench Creation"
							description="Newly created benches will be given access to users of this role"
						/>
						<Switch
							v-model="allowServerCreation"
							label="Allow Server Creation"
							description="Newly created servers will be given access to users of this role"
						/>
					</div>
				</div>
			</Tabs>
		</template>
	</Dialog>
</template>

<script setup>
import { Switch, Tabs } from 'frappe-ui';
import { computed, ref, watch } from 'vue';
import { getTeam } from '../../data/team';
import UserWithAvatarCell from '../UserWithAvatarCell.vue';
import { toast } from 'vue-sonner';
import { getDocResource } from '../../utils/resource';
import session from '../../data/session';

const props = defineProps({
	roleId: { type: String, required: true }
});
const member = ref({});
const show = ref(true);
const tabIndex = ref(0);

const role = getDocResource({
	doctype: 'Press Role',
	name: props.roleId,
	auto: true,
	whitelistedMethods: {
		addUser: 'add_user',
		removeUser: 'remove_user'
	},
	onSuccess: data => {
		allowBilling.value = !!data.allow_billing;
		allowApps.value = !!data.allow_apps;
		allowSiteCreation.value = !!data.allow_site_creation;
		allowBenchCreation.value = !!data.allow_bench_creation;
		allowServerCreation.value = !!data.allow_server_creation;
	}
});
const roleUsers = computed(() => role.doc.users || []);
const allowBilling = ref(!!role.doc?.allow_billing);
const allowApps = ref(!!role.doc?.allow_apps);
const allowSiteCreation = ref(!!role.doc?.allow_site_creation);
const allowBenchCreation = ref(!!role.doc?.allow_bench_creation);
const allowServerCreation = ref(!!role.doc?.allow_server_creation);

// using a watcher instead of event listener to avoid multiple api calls
watch(
	[
		allowBilling,
		allowApps,
		allowSiteCreation,
		allowBenchCreation,
		allowServerCreation
	],
	([
		newallowBilling,
		newallowApps,
		newallowSiteCreation,
		newallowBenchCreation,
		newallowServerCreation
	]) => {
		if (
			newallowBilling === !!role.doc.allow_billing &&
			newallowApps === !!role.doc.allow_apps &&
			newallowSiteCreation === !!role.doc.allow_site_creation &&
			newallowBenchCreation === !!role.doc.allow_bench_creation &&
			newallowServerCreation === !!role.doc.allow_server_creation
		)
			return;

		role.setValue.submit(
			{
				allow_billing: newallowBilling,
				allow_apps: newallowApps,
				allow_site_creation: newallowSiteCreation,
				allow_bench_creation: newallowBenchCreation,
				allow_server_creation: newallowServerCreation
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
