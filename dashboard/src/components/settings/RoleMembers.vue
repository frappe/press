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
					class="size-14 bg-surface-gray-3 flex m-auto items-center rounded justify-center text-ink-gray-5 font-semibold text-2xl"
				>
					{{ user.full_name
							.split(' ')
							.map((s: string) => s.charAt(0))
							.join('')
							.toUpperCase() }}
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
	</div>
</template>

<script setup lang="ts">
import { Button } from 'frappe-ui'
import { dayjsLocal } from '../../utils/dayjs'

withDefaults(
	defineProps<{
		users?: Array<any>
	}>(),
	{
		users: () => [],
	},
)

defineEmits<{
	remove: [id: string]
}>()
</script>
