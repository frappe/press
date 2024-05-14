<template>
	<Dialog
		v-if="role.doc"
		:options="{ title: `${role.doc.title}` }"
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
						:loading="role.addUser?.loading"
						@click="() => addUser(member.value)"
					/>
				</div>

				<div class="mb-1 text-gray-600">Members</div>
				<div
					v-if="roleUsers.length === 0"
					class="rounded border border-dashed p-4 text-center text-gray-500"
				>
					<span>No members added to this role.</span>
				</div>
				<div v-else class="flex flex-col divide-y">
					<div v-for="user in roleUsers" class="flex justify-between py-2.5">
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
	roleId: { type: String, required: true }
});
const member = ref({});
const show = ref(true);

const role = createDocumentResource({
	doctype: 'Press Role',
	name: props.roleId,
	auto: true,
	whitelistedMethods: {
		addUser: 'add_user',
		removeUser: 'remove_user'
	}
});
const roleUsers = computed(() => role.doc.users || []);

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
