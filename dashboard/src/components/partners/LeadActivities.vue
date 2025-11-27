<template>
	<div class="mt-10 px-60">
		<div v-for="activity in activities" :key="activity.id" class="activities">
			<div
				class="activity px-3 sm:px-10 grid grid-cols-[30px_minmax(auto,_1fr)] gap-2 sm:gap-4"
			>
				<div
					class="z-0 relative flex justify-center before:absolute before:left-[50%] before:-z-[1] before:top-0 before:border-l before:border-outline-gray-modals before:h-full"
				>
					<component :is="activity.icon" class="text-ink-gray-4" />
				</div>
				<div class="mb-1">
					<div>
						<div
							class="mb-1 flex items-center justify-stretch gap-2 py-1 text-base"
						>
							<div
								class="inline-flex items-center flex-wrap gap-1.5 text-ink-gray-8 font-medium"
							>
								<span class="font-medium">{{ activity.owner }}</span>
								<span class="text-ink-gray-5">{{ activity.type }}</span>
								<span v-if="activity.data.field_label">{{
									activity.data.field_label
								}}</span>
								<span v-if="activity.value" class="text-ink-gray-5">{{
									activity.value
								}}</span>
								<span
									class="truncate max-w-xs"
									v-if="activity.data.old_value"
									>{{ activity.data.old_value }}</span
								>
								<span v-else>{{ activity.data.value }}</span>
								<span v-if="activity.to" class="text-ink-gray-5">{{
									activity.to
								}}</span>
								<span class="truncate max-w-xs">{{
									activity.data.new_value
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
			</div>
		</div>
	</div>
</template>
<script setup>
import { createResource, Tooltip } from 'frappe-ui';
import { useRoute } from 'vue-router';
import DotIcon from '../icons/DotIcon.vue';
import SelectIcon from '../icons/SelectIcon.vue';
import { computed } from 'vue';
import { timeAgo, startCase } from '../../utils/format';

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
		activity.icon = DotIcon;
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

function formatDate(date) {
	return new Date(date).toLocaleString();
}

function sortByCreation(list) {
	return list.sort((a, b) => new Date(a.creation) - new Date(b.creation));
}
// function sortByModified(list) {
//   return list.sort((b, a) => new Date(a.modified) - new Date(b.modified))
// }
</script>
