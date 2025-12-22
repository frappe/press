<template>
	<div class="space-y-4">
		<div class="grid grid-cols-3 gap-4 text-base">
			<div
				v-for="user in users"
				class="group flex h-24 rounded shadow hover:shadow-lg transition"
			>
				<div class="size-24 rounded-l">
					<img
						v-if="user.user_image"
						:src="user.user_image"
						class="rounded-l object-cover"
					/>
					<div
						v-else
						class="size-full bg-gray-200 flex items-center justify-center rounded-l text-gray-500 font-semibold text-3xl"
					>
						{{
							user.full_name
								.split(' ')
								.map((s: string) => s.charAt(0))
								.join('')
								.toUpperCase()
						}}
					</div>
				</div>
				<div class="px-4 py-2 flex flex-col justify-evenly">
					<div class="font-medium">{{ user.full_name }}</div>
					<div class="text-gray-800">{{ user.user }}</div>
					<div>Joined: {{ dayjsLocal(user.creation).format('LL') }}</div>
				</div>
				<div
					class="opacity-0 group-hover:opacity-100 transition w-14 flex justify-center items-center ml-auto rounded-r"
				>
					<Button
						icon="trash-2"
						variant="ghost"
						class="text-red-600"
						@click="$emit('remove', user.user)"
					/>
				</div>
			</div>
		</div>
		<div>
			<Button label="Invite" icon-left="user" @click="open = !open" />
		</div>
		<Dialog
			v-model="open"
			:options="{
				title: 'Invite',
				size: 'lg',
				actions: [
					{
						label: 'Submit',
						variant: 'solid',
						onClick: () => {
							$emit('add', userForInvite);
							open = false;
						},
					},
				],
			}"
		>
			<template #body-content>
				<div class="mb-2 text-base">Invite a team member to this role.</div>
				<Select
					:options="usersForInvite"
					v-model="userForInvite"
					placeholder="User"
				/>
			</template>
		</Dialog>
	</div>
</template>

<script setup lang="ts">
import { computed, ref } from 'vue';
import { Button, Dialog, Select } from 'frappe-ui';
import { dayjsLocal } from '../../utils/dayjs';
import { teamMembers } from './data';

const props = withDefaults(
	defineProps<{
		users?: Array<any>;
	}>(),
	{
		users: () => [],
	},
);

defineEmits<{
	add: [id: string];
	remove: [id: string];
}>();

const open = ref(false);
const userForInvite = ref<string>('');
const usersForInvite = computed(() =>
	teamMembers(props.users.map((u) => u.user)),
);
</script>
