<script setup lang="ts">
import { Popover } from 'frappe-ui';
import LucideInbox from '~icons/lucide/inbox';
import { unreadNotificationsCount } from '@/data/notifications';

let props = defineProps({
	item: {
		type: Object,
		required: true,
	},
});
</script>

<template>
	<Popover placement="right-start">
		<template #target="{ togglePopover }">
			<button
				@click="togglePopover"
				class="flex items-center rounded px-2 py-1 text-ink-gray-6 transition gap-2 hover:bg-surface-gray-3 w-full"
				:class="[
					item.disabled ? 'pointer-events-none opacity-50' : '',
					$attrs.class,
				]"
			>
				<LucideInbox class="m-1 h-4 w-4 text-ink-gray-6" />
				<span class="text-sm flex-1 text-left">{{ item.name }}</span>

				<span
					class="px-1.5 py-0.5 text-xs text-gray-600"
					v-if="unreadNotificationsCount.data > 0"
				>
					{{
						unreadNotificationsCount.data > 99
							? '99+'
							: unreadNotificationsCount.data
					}}
				</span>
			</button>
		</template>

		<template #body>
			<div class="text-ink-gray-9 bg-white p-4 h-screen ml-2 shadow-sm">
				Popover content
			</div>
		</template>
	</Popover>
</template>
