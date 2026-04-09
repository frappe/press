<script setup lang="ts">
import {
	Popover,
	Badge,
	Button,
	Tooltip,
	Tabs,
	frappeRequest,
	createListResource,
} from 'frappe-ui';

import { h, ref, watch } from 'vue';
import { toast } from 'vue-sonner';
import { dayjsLocal } from '@/utils/dayjs';

import {
	unreadNotificationsCount,
	unreadSupportNotificationsCount,
} from '@/data/notifications';

import { renderDialog } from '@/utils/components';
import { useRouter } from 'vue-router';
import { getDocResource } from '@/utils/resource';

import Scrollbar from '@/components/common/Scrollbar.vue';
import SupportAccessDialog from '@/components/SupportAccessDialog.vue';

let props = defineProps({
	item: {
		type: Object,
		required: true,
	},
});

const formatHtml = (str: string) => {
	return str.replace(/<(?!\/?b\b)[^>]*>/g, '').split('\n')[0];
};

const router = useRouter();

const resource = createListResource({
	doctype: 'Press Notification',
	url: 'press.api.notifications.get_notifications',
	auto: true,
	cache: ['Notifications'],
	start: 0,
	pageLength: 10,
});

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

const openSupportAccess = (e, name) => {
	e.stopPropagation();
	renderDialog(
		h(SupportAccessDialog, {
			name,
		}),
	);
};

// tile icons & classes
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

// Reload resource on tab switch
const activeTab = ref(0);

watch(activeTab, (x) => {
	const filters: any = {};
	if (x == 0) {
		//
	} else if (x == 1) {
		filters.type = 'Support Access';
	} else {
		filters.read = 'Unread';
	}

	resource.update({ filters });
	resource.reload();
});

const tabs = [
	{ label: 'All', icon: LucideRows2 },
	{ label: 'Requests', icon: LucideKeySquare },
	{ label: 'Unread', icon: LucideMessageSquareDot },
];
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
					class="text-xs text-ink-gray-6"
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
				class="text-ink-gray-9 bg-white h-screen ml-2 shadow-xl w-[430px] flex flex-col"
			>
				<!-- header -->
				<div class="text-base flex items-center py-2 pl-4 pr-2 border-b">
					<span class="font-medium mr-auto"> Notifications</span>
					<Button variant="ghost" @click="togglePopover">
						<template #icon>
							<LucideX class="size-4" />
						</template>
					</Button>
				</div>

				<Tabs
					v-model="activeTab"
					class="w-full flex-none [&_[role=tablist]]:pr-2 [&_[role=tab]]:justify-center [&_role=tab]]:w-full"
					:tabs
				>
					<template #tab-item="{ tab }">
						<button
							class="flex items-center gap-2 py-2 text-ink-gray-5 aria-selected:text-ink-gray-9"
						>
							<span class="text-sm">{{ tab.label }}</span>
							<Badge v-if="tab.label != 'All'">{{
								tab.label == 'Unread'
									? unreadNotificationsCount.data
									: unreadSupportNotificationsCount.data
							}}</Badge>
						</button>

						<!-- show mark all button at end of tabs-->
						<Button
							@click="markAllAsRead(togglePopover)"
							variant="ghost"
							class="text-sm ml-auto my-auto"
							v-if="tab.label == 'Unread'"
						>
							<template #prefix>
								<LucideCheckCheck class="size-3.5" />
							</template>
							Mark All
						</Button>
					</template>
				</Tabs>

				<!-- body -->
				<Scrollbar v-if="resource.data.length > 0">
					<div
						v-for="x in resource.data"
						class="[&_b]:font-semibold p-4 flex gap-4 items-center relative cursor-pointer border-b last:border-0"
						@click="markAsRead(x, togglePopover)"
					>
						<!-- type icon -->
						<div
							class="size-8 flex-shrink-0 flex items-center p-2 rounded mb-auto mt-1 relative"
							:class="[iconBgColors[x.type] || 'bg-surface-gray-1']"
						>
							<span
								v-if="x.read == 0"
								class="p-0.5 border ring-outline-gray-2 ring-1 bg-surface-gray-7 absolute rounded top-0 left-0"
							/>
							<component
								:is="icons[x.type] || LucideCircleAlert"
								class="size-4"
								:class="iconColors[x.type] || 'text-ink-gray-6'"
							/>
						</div>

						<div
							class="text-base leading-relaxed flex flex-wrap gap-2 w-full min-w-0"
						>
							<div class="flex">
								<p v-html="formatHtml(x.message)" class="w-full" />
								<Button
									v-if="x.type == 'Support Access'"
									tooltip="Support Access actions"
									variant="ghost"
									class="mb-auto"
									@click="(e) => openSupportAccess(e, x.document_name)"
									><template #icon>
										<LucideChevronRight class="size-3.5" /> </template
								></Button>
							</div>

							<Badge class="text-xs mr-auto">
								{{ x.title }}

								<Tooltip
									text="This notification requires your attention"
									:hoverDelay="0"
									v-if="x.is_actionable && !x.is_addressed"
								>
									<LucideCircleAlert class="size-3" />
								</Tooltip>
							</Badge>

							<span class="text-ink-gray-5 text-xs">
								{{ dayjsLocal(x.creation).fromNow() }}
							</span>
						</div>
					</div>
				</Scrollbar>

				<div v-else class="text-center text-ink-gray-6 text-sm py-10">
					No notifications to show
				</div>

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
