<template>
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
					class="size-full bg-gray-200 flex items-center justify-center rounded-l text-gray-500 font-semibold text-2xl"
				>
					{{ user.full_name.charAt(0).toUpperCase() }}
				</div>
			</div>
			<div class="px-4 py-3 flex flex-col justify-evenly">
				<div class="font-medium">{{ user.full_name }}</div>
				<div>Joined: {{ dayjsLocal(user.creation).format('LL') }}</div>
			</div>
			<div
				class="opacity-0 group-hover:opacity-100 transition w-14 flex justify-center items-center ml-auto rounded-r"
			>
				<Button icon="trash-2" variant="ghost" class="text-red-600" />
			</div>
		</div>
	</div>
</template>

<script setup lang="ts">
import { Button } from 'frappe-ui';
import { dayjsLocal } from '../../utils/dayjs';

withDefaults(
	defineProps<{
		users?: Array<any>;
	}>(),
	{
		users: () => [],
	},
);
</script>
