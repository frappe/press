<template>
	<div class="space-y-4">
		<div
			class="grid grid-cols-3 gap-4 text-base"
			v-if="users && users.length > 0"
		>
			<div
				v-for="user in users"
				class="group flex gap-3 rounded border transition p-2.5 px-3 cursor-pointer items-center"
			>
				<img
					v-if="user.user_image"
					:src="user.user_image"
					class="object-cover object-center size-14 m-auto rounded"
				/>
				<div
					v-else
					class="size-14 bg-gray-200 flex m-auto items-center rounded justify-center text-gray-500 font-semibold text-2xl"
				>
					{{
						user.full_name
							.split(' ')
							.map((s: string) => s.charAt(0))
							.join('')
							.toUpperCase()
					}}
				</div>
				<div class="flex flex-col text-sm flex-1">
					<span class="font-medium mb-1">{{ user.full_name }}</span>
					<span class="text-ink-gray-5 mb-2">{{ user.user }}</span>
					<span class="text-ink-gray-5 text-xs"
						>Added {{ dayjsLocal(user.creation).format('LL') }}</span
					>
				</div>
				<Button
					icon="trash-2"
					theme="red"
					class="opacity-0 group-hover:opacity-100 transition mb-auto"
					@click="$emit('remove', user.user)"
				/>
			</div>
		</div>

		<div
			v-else
			class="text-ink-gray-4 text-sm p-20 rounded flex bg-surface-gray-1 justify-center"
		>
			No members to show
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
