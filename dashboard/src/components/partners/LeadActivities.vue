<template>
	<div class="mt-5 px-60">
		<div class="flex justify-between px-10 pb-5">
			<div class="font-semibold text-lg">Activity</div>
			<div>
				<Dropdown :options="commentOptions">
					<template #default="{ comment }">
						<Button variant="subtle" size="md" label="New">
							<template #suffix>
								<FeatherIcon
									:name="comment ? 'chevron-up' : 'chevron-down'"
									class="h-4 w-4"
								/>
							</template>
						</Button>
					</template>
				</Dropdown>
			</div>
		</div>
		<div v-for="activity in activities" :key="activity.id" class="activities">
			<div
				class="activity px-3 sm:px-10 grid grid-cols-[30px_minmax(auto,_1fr)] gap-2 sm:gap-4"
			>
				<div
					class="z-0 relative flex justify-center before:absolute before:left-[50%] before:-z-[1] before:top-0 before:border-l before:border-outline-gray-modals before:h-full"
				>
					<component :is="activity.icon" class="text-ink-gray-4" />
				</div>
				<div
					class="mb-1"
					:id="activity.name"
					v-if="activity.activity_type != 'comment'"
				>
					<div>
						<div
							class="mb-1 flex items-center justify-stretch gap-2 py-1 text-base"
						>
							<div
								class="inline-flex items-center flex-wrap gap-1.5 text-ink-gray-8 font-medium"
							>
								<span class="font-medium">{{ activity.owner }}</span>
								<span class="text-ink-gray-5">{{ activity.type }}</span>
								<span v-if="activity.data?.field_label">{{
									activity.data.field_label
								}}</span>
								<span v-if="activity.value" class="text-ink-gray-5">{{
									activity.value
								}}</span>
								<span
									class="truncate max-w-xs"
									v-if="activity.data?.old_value"
									>{{ activity.data.old_value }}</span
								>
								<span v-else>{{ activity.data?.value }}</span>
								<span v-if="activity?.to" class="text-ink-gray-5">{{
									activity.to
								}}</span>
								<span class="truncate max-w-xs">{{
									activity.data?.new_value
								}}</span>
							</div>
							<div class="ml-auto whitespace-nowrap">
								<Tooltip :text="formatDate(activity.creation)">
									<div class="text-sm text-ink-gray-5">
										{{ timeAgo(activity.creation) }}
									</div>
								</Tooltip>
							</div>
						</div>
						<div class="mb-1 flex flex-col gap-2 py-1.5">
							<div class="flex items-center justify-stretch gap-2 text-base">
								<div
									v-if="activity.other_versions"
									class="inline-flex flex-wrap gap-1.5 text-ink-gray-8 font-normal text-sm"
								>
									<span>{{ activity.show_others ? 'Hide' : 'Show' }}</span>
									<span> +{{ activity.other_versions.length }} </span>
									<span>{{ 'changes from' }}</span>
									<span>{{ activity.owner }}</span>
									<Button
										class="!size-4"
										variant="ghost"
										:icon="SelectIcon"
										@click="activity.show_others = !activity.show_others"
									/>
								</div>
							</div>
							<div
								v-if="activity.other_versions && activity.show_others"
								class="flex flex-col gap-0.5"
							>
								<div
									v-for="activity in [...activity.other_versions]"
									class="flex items-start justify-stretch gap-2 py-1.5 text-base"
								>
									<div class="inline-flex flex-wrap gap-1 text-ink-gray-5">
										<span
											v-if="activity.data?.field_label"
											class="max-w-xs truncate text-ink-gray-5"
										>
											{{ activity.data.field_label }}
										</span>
										<FeatherIcon
											name="arrow-right"
											class="mx-1 h-4 w-4 text-ink-gray-5"
										/>
										<span v-if="activity.activity_type">
											{{ startCase(activity.activity_type) }}
										</span>
										<span
											v-if="activity.data?.old_value"
											class="max-w-xs font-medium text-ink-gray-8"
										>
											<div class="truncate">
												{{ activity.data.old_value }}
											</div>
										</span>
										<span v-if="activity.activity_type === 'changed'">{{
											'to'
										}}</span>
										<span
											v-if="activity.data?.new_value"
											class="max-w-xs font-medium text-ink-gray-8"
										>
											<div class="truncate">
												{{ activity.data.new_value }}
											</div>
										</span>
										<span
											v-if="activity.data?.value"
											class="max-w-xs font-medium text-ink-gray-8"
										>
											<div class="truncate">
												{{ activity.data.value }}
											</div>
										</span>
									</div>

									<div class="ml-auto whitespace-nowrap">
										<Tooltip :text="formatDate(activity.creation)">
											<div class="text-sm text-ink-gray-5">
												{{ timeAgo(activity.creation) }}
											</div>
										</Tooltip>
									</div>
								</div>
							</div>
						</div>
					</div>
				</div>
				<div
					class="mb-4"
					:id="activity.name"
					v-if="activity.activity_type == 'comment'"
				>
					<CommentArea :activity="activity" />
				</div>
			</div>
		</div>
		<NewCommentDialog
			v-if="showNewCommentDialog"
			v-model="showNewCommentDialog"
			@update:show="showNewCommentDialog = $event"
			:content="newComment"
			@save-comment="newComment = $event"
			:members="memberList"
		/>
	</div>
</template>
<script setup>
import { createResource, Tooltip, Button, FeatherIcon, call } from 'frappe-ui';
import { useRoute } from 'vue-router';
import DotIcon from '../icons/DotIcon.vue';
import SelectIcon from '../icons/SelectIcon.vue';
import { computed, h, ref, watch, onMounted } from 'vue';
import { timeAgo, startCase } from '../../utils/format';
import CommentArea from './CommentArea.vue';
import CommentIcon from '../icons/CommentIcon.vue';
import DropdownItem from '../billing/DropdownItem.vue';
import NewCommentDialog from './NewCommentDialog.vue';
import { session } from '../../data/session';
import { getTeam } from '../../data/team';

const route = useRoute();

const all_activities = createResource({
	url: 'press.api.partner.get_lead_activities',
	makeParams: () => {
		return {
			name: route.params.leadId,
		};
	},
	cache: ['all_activities', route.params.leadId],
	auto: true,
	transform: (versions) => {
		return { versions };
	},
});

function get_activities() {
	if (!all_activities.data?.versions) return [];
	return [...all_activities.data.versions];
}

const activities = computed(() => {
	let _activities = get_activities();
	_activities.forEach((activity) => {
		if (activity.activity_type == 'comment') {
			activity.icon = CommentIcon;
		} else {
			activity.icon = DotIcon;
		}
		update_activities_details(activity);
	});
	return sortByCreation(_activities);
});

function update_activities_details(activity) {
	activity.owner_name = activity.owner;
	activity.type = '';
	activity.value = '';
	activity.to = '';

	if (activity.activity_type == 'creation') {
		activity.type = activity.data;
	} else if (activity.activity_type == 'added') {
		activity.type = 'added';
		activity.value = 'as';
	} else if (activity.activity_type == 'removed') {
		activity.type = 'removed';
		activity.value = 'value';
	} else if (activity.activity_type == 'changed') {
		activity.type = 'changed';
		activity.value = 'from';
		activity.to = 'to';
	}
}

let newComment = ref('');
let showNewCommentDialog = ref(false);
const commentOptions = computed(() => {
	return [
		{
			label: 'New Comment',
			value: 'comment',
			component: () =>
				h(DropdownItem, {
					label: 'New Comment',
					onClick: () => {
						showNewCommentDialog.value = true;
					},
				}),
		},
		// {
		// 	label: 'New Email',
		// 	value: 'email',
		// 	component: () =>
		// 		h(DropdownItem, {
		// 			label: 'New Email',
		// 			onClick: () => {
		// 				console.log('Email Clicked');
		// 			},
		// 		}),
		// },
	];
});

watch(newComment, () => {
	saveComment();
});

async function saveComment() {
	if (!newComment.value) {
		return;
	}
	let comment = await call('frappe.desk.form.utils.add_comment', {
		reference_doctype: 'Partner Lead',
		reference_name: route.params.leadId,
		content: newComment.value,
		comment_email: session.user,
		comment_by: session.userFullName,
	});

	if (comment) {
		newComment.value = '';
		showNewCommentDialog.value = false;
		all_activities.reload();
	}
}

const team = getTeam();
let memberList = ref([]);
const getMembers = async () => {
	let members = await team.getTeamMembers.submit();
	memberList.value = members.map((member) => {
		return { label: member.full_name, value: member.name };
	});
};

onMounted(() => {
	getMembers();
});

function formatDate(date) {
	return new Date(date).toLocaleString();
}

function sortByCreation(list) {
	return list
		.sort((a, b) => new Date(a.creation) - new Date(b.creation))
		.reverse();
}
</script>
