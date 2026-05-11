<template>
	<div class="space-y-4">
		<div
			class="grid grid-cols-3 gap-4 text-base"
			v-if="resources && resources.length > 0"
		>
			<RouterLink
				v-for="resource in resources"
				:to="toLink(resource)"
				class="text-sm border rounded flex group py-3 px-3.5"
			>
				<div class="flex gap-4 rounded transition min-w-0">
					<div
						class="m-auto size-14 rounded-lg flex items-center justify-center p-3"
						:class="colorClasses[resource.document_type]"
					>
						<FeatherIcon class="size-6" :name="icons[resource.document_type]" />
					</div>

					<div class="flex flex-col min-w-0">
						<span
							v-if="resource.document_type !== 'Site'"
							class="truncate font-medium mb-1"
							:title="resource.document_title"
						>
							{{ resource.document_title }}
						</span>

						<span class="mb-2 text-ink-gray-5">{{
							resource.document_name
						}}</span>
						<span class="text-ink-gray-5 text-xs">{{
							resource.document_type == 'Release Group'
								? 'Bench'
								: resource.document_type
						}}</span>
					</div>
				</div>
				<Button
					icon="trash-2"
					theme="red"
					class="opacity-0 group-hover:opacity-100 transition mb-auto ml-auto"
					@click.prevent.stop="
						$emit('remove', resource.document_type, resource.document_name)
					"
				/>
			</RouterLink>
		</div>

		<div
			v-else
			class="text-ink-gray-4 text-sm p-20 rounded flex bg-surface-gray-1 justify-center"
		>
			No resources to show
		</div>
		<div>
			<Button label="Include" icon-left="globe" @click="open = !open" />
		</div>
		<Dialog
			v-model="open"
			:options="{
				title: 'Include',
				size: 'lg',
				actions: [
					{
						label: 'Submit',
						variant: 'solid',
						onClick: () => {
							$emit('include', resourcesToIncludeModel);
							open = false;
						},
					},
				],
			}"
		>
			<template #body-content>
				<div class="mb-2 text-base">Include a resource in this role.</div>
				<MultiSelect
					:options="resourcesToIncludeOptions"
					:model-value="
						resourcesToIncludeModel.map((item) => item.document_name)
					"
					@update:model-value="
						resourcesToIncludeModel = resourcesToIncludeOptions.filter(
							(option) => $event.includes(option.value),
						)
					"
					placeholder="Select resources"
				>
					<template #option="{ item }">
						<FeatherIcon
							class="size-4 mr-2"
							:name="icons[item.document_type]"
						/>
						{{ item.label }}
					</template>
				</MultiSelect>
			</template>
		</Dialog>
	</div>
</template>

<script setup lang="ts">
import { computed, ref } from 'vue';
import { Button, FeatherIcon, MultiSelect } from 'frappe-ui';
import { teamResources } from './data';

const props = withDefaults(
	defineProps<{
		resources?: Array<any>;
	}>(),
	{
		resources: () => [],
	},
);

const colorClasses = {
	'Release Group': 'bg-surface-blue-2 text-ink-blue-2',
	Server: 'bg-surface-amber-1 text-ink-amber-2',
	Site: 'bg-surface-green-2 text-ink-green-2',
};

const emit = defineEmits<{
	include: [Array<{ document_type: string; document_name: string }>];
	remove: [document_type: string, document_name: string];
}>();

const icons = {
	'Release Group': 'package',
	Server: 'server',
	Site: 'globe',
};

const open = ref(false);

const resourcesToIncludeModel = ref<
	Array<{ document_type: string; document_name: string }>
>([]);
const resourcesToIncludeOptions = computed(() => {
	return teamResources.value.filter(
		(resource) =>
			!props.resources?.some(
				(r) =>
					r.document_type === resource.document_type &&
					r.document_name === resource.document_name,
			),
	);
});

const toLink = (resource: any) => {
	if (resource.document_type === 'Site') {
		return {
			name: 'Site Detail',
			params: {
				name: resource.document_name,
			},
		};
	} else if (resource.document_type === 'Server') {
		return {
			name: 'Server Detail',
			params: {
				name: resource.document_name,
			},
		};
	} else if (resource.document_type === 'Release Group') {
		return {
			name: 'Release Group Detail',
			params: {
				name: resource.document_name,
			},
		};
	}
	return '#';
};
</script>
