<template>
	<Dialog
		v-if="permissionGroup.doc"
		:options="{ title: `${permissionGroup.doc.title}` }"
		v-model="show"
		@after-leave="() => (this.memberEmail = '')"
	>
		<template v-slot:body-content>
			<div class="text-base">
				<div class="mb-4 flex gap-2">
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
						:loading="permissionGroup.addUser?.loading"
						@click="() => addUser(member.value)"
					/>
				</div>

				<div class="mb-1 text-gray-600">Members</div>
				<div
					v-if="groupUsers.length === 0"
					class="rounded border border-dashed p-4 text-center text-gray-500"
				>
					<LoadingText v-if="permissionGroup.getUsers.loading" />
					<span v-else>No members added to this role.</span>
				</div>
				<div v-else class="flex flex-col divide-y">
					<div v-for="user in groupUsers" class="flex justify-between py-2.5">
						<UserWithAvatarCell
							:avatarImage="user.user_image"
							:fullName="user.full_name"
							:email="user.name"
							:key="user.name"
						/>
						<Button @click="() => removeUser(user.name)">
							<template #icon>
								<i-lucide-x class="h-4 w-4 text-gray-600" />
							</template>
						</Button>
					</div>
				</div>
			</div>
		</template>
	</Dialog>
</template>

<script setup>
import { createDocumentResource } from 'frappe-ui';
import { computed, ref } from 'vue';
import { getTeam } from '../../data/team';
import UserWithAvatarCell from '../UserWithAvatarCell.vue';
import { toast } from 'vue-sonner';

const props = defineProps({
	groupId: { type: String, required: true }
});
const member = ref({});
const show = ref(true);

const permissionGroup = createDocumentResource({
	doctype: 'Press Permission Group',
	name: props.groupId,
	auto: true,
	whitelistedMethods: {
		getUsers: 'get_users',
		addUser: 'add_user',
		removeUser: 'remove_user'
	},
	onSuccess() {
		permissionGroup.getUsers.submit();
	}
});
const groupUsers = computed(() => permissionGroup.getUsers.data || []);

const team = getTeam();
const autoCompleteList = computed(() => {
	const isNotGroupMember = u => !groupUsers.value.includes(u);
	const isNotTeamOwner = u => u !== team.doc.user;
	return team.doc.team_members
		?.filter(({ user }) => isNotGroupMember(user) && isNotTeamOwner(user))
		.map(({ user }) => ({ label: user, value: user }));
});

function addUser(user) {
	return toast.promise(permissionGroup.addUser.submit({ user }), {
		loading: `Adding ${user} to ${permissionGroup.doc.title}`,
		success: () => {
			permissionGroup.getUsers.submit();
			member.value = {};
			return `${user} added to ${permissionGroup.doc.title}`;
		},
		error: e => (e.messages.length ? e.messages.join('\n') : e.message)
	});
}

function removeUser(user) {
	return toast.promise(permissionGroup.removeUser.submit({ user }), {
		loading: `Removing ${user} from ${permissionGroup.doc.title}`,
		success: () => {
			permissionGroup.getUsers.submit();
			return `${user} removed from ${permissionGroup.doc.title}`;
		},
		error: e => (e.messages.length ? e.messages.join('\n') : e.message)
	});
}
</script>
