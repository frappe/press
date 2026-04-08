<script setup lang="ts">
import { Popover, Badge, Button, Tooltip, createListResource } from 'frappe-ui';
import LucideInbox from '~icons/lucide/inbox';
import { dayjsLocal } from '@/utils/dayjs';
import LucideKey from '~icons/lucide/key';
import { getDocResource } from '@/utils/resource';
import { useRouter } from 'vue-router';
import { toast } from 'vue-sonner';
import { frappeRequest } from 'frappe-ui';
import LucideAlert from '~icons/lucide/circle-alert';

import { unreadNotificationsCount } from '@/data/notifications';

let props = defineProps({
	item: {
		type: Object,
		required: true,
	},
});

const icons = {
	'Site Update': LucideRefreshCw,
	'Site Migrate': LucideArrowUpCircle,
	'Version Upgrade': LucideArrowUpCircle,
	'Bench Deploy': LucideRocket,
	'Site Recovery': LucideShieldCheck,
	'Agent Job Failure': LucideAlertTriangle,
	'Downtime/Performance': LucideActivity,
	'Support Access': LucideKey,
	'Auto Scale': LucideTrendingUp,
};

const iconColors = {
	'Site Update': 'text-ink-green-2',
	'Site Migrate': 'text-ink-green-2',
	'Version Upgrade': 'text-ink-green-2',
	'Bench Deploy': 'text-ink-green-2',
	'Site Recovery': 'text-ink-green-2',
	'Agent Job Failure': 'text-ink-red-4',
	'Downtime/Performance': 'text-ink-red-4',
	'Support Access': 'text-ink-amber-3',
	'Auto Scale': 'text-ink-red-4',
};

const iconBgColors = {
	'Site Update': 'bg-surface-green-1',
	'Site Migrate': 'bg-surface-green-1',
	'Version Upgrade': 'bg-surface-green-1',
	'Bench Deploy': 'bg-surface-green-1',
	'Site Recovery': 'bg-surface-green-1',
	'Agent Job Failure': 'bg-surface-red-1',
	'Downtime/Performance': 'bg-surface-red-1',
	'Support Access': 'bg-surface-amber-1',
	'Auto Scale': 'bg-surface-red-1',
};

const resource = createListResource({
	doctype: 'Press Notification',
	url: 'press.api.notifications.get_notifications',
	auto: true,
	filters: {
		read: 'Unread',
	},
	cache: ['Notifications'],
	start: 0,
	pageLength: 10,
});

const formatHtml = (str: string) => {
	return str.replace(/<(?!\/?b\b)[^>]*>/g, '').split('\n')[0];
};

const router = useRouter();

const markAsRead = (row, togglePopover) => {
	const docres = getDocResource({
		doctype: 'Press Notification',
		name: row.name,
		whitelistedMethods: {
			markNotificationAsRead: 'mark_as_read',
		},
	});

	docres.markNotificationAsRead.submit().then(() => {
		unreadNotificationsCount.setData((data) => data - 1);
		if (row.route) {
			togglePopover();
			router.push('/' + row.route);
		}
	});

	resource.setData((data) => {
		const newData = data.filter((d) => d.name !== row.name);
		resource.originalData = newData;
		return newData;
	});
};

const markAllAsRead = (togglePopover) => {
	toast.promise(
		frappeRequest({
			url: '/api/method/press.api.notifications.mark_all_notifications_as_read',
		}),
		{
			success: () => {
				resource.reload();
				togglePopover();

				return 'All notifications marked as read';
			},
			loading: 'Marking all notifications as read...',
			error: (error) =>
				error.messages?.length ? error.messages.join('\n') : error.message,
		},
	);
};
</script>

<template>
	<Popover placement="right-start">
		<!-- sidebar item -->
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

		<!-- floating drawer  -->
		<template #body="{ togglePopover }">
			<div
				class="text-ink-gray-9 bg-white h-screen ml-2 shadow-xl w-[400px] flex flex-col"
			>
				<div class="text-base flex items-center py-2 px-4 border-b">
					<span class="font-medium mr-auto"> Notifications</span>

					<Button variant="ghost" @click="markAllAsRead(togglePopover)">
						<template #icon>
							<LucideCheckCheck class="size-4" />
						</template>
					</Button>

					<Button variant="ghost" @click="togglePopover">
						<template #icon>
							<LucideX class="size-4" />
						</template>
					</Button>
				</div>

				<!-- notification tiles -->
				<section class="overflow-auto">
					<div
						v-if="resource.data.length > 0"
						v-for="(x, i) in resource.data"
						:key="x.name"
						class="[&_b]:font-semibold p-4 flex gap-4 items-center cursor-pointer"
						:class="{ 'border-b': i !== resource.data.length - 1 }"
						@click="() => markAsRead(x, togglePopover)"
					>
						<div
							class="size-8 flex-shrink-0 flex items-center p-2 rounded mb-auto mt-1"
							:class="[iconBgColors[x.type] || 'bg-surface-gray-1']"
						>
							<component
								:is="icons[x.type] || LucideAlert"
								class="size-4"
								:class="iconColors[x.type] || 'text-ink-gray-6'"
							/>
						</div>

						<div
							class="text-base leading-relaxed flex flex-wrap gap-2 w-full min-w-0"
						>
							<p v-html="formatHtml(x.message)" class="w-full" />

							<Badge class="text-xs mr-auto">
								{{ x.title }}
								<Tooltip
									text="This notification requires your attention"
									:hoverDelay="0"
									v-if="x.is_actionable && !x.is_addressed"
								>
									<LucideAlert class="size-3" />
								</Tooltip>
							</Badge>

							<span class="text-ink-gray-5 text-xs">
								{{ dayjsLocal(x.creation).fromNow() }}
							</span>
						</div>
					</div>

					<div v-else class="text-center text-ink-gray-6 text-sm py-10">
						No notifications to show
					</div>
				</section>

				<Button
					@click="resource.next"
					v-if="resource.hasNextPage"
					label="Load More"
					size="sm"
					class="ml-auto my-3 mr-3"
				/>
			</div>
		</template>
	</Popover>
</template>
