<template>
	<div class="space-y-4">
		<div class="grid grid-cols-3 gap-4 text-base">
			<RouterLink v-for="resource in resources" :to="toLink(resource)">
				<div class="group flex h-24 rounded shadow hover:shadow-lg transition">
					<div
						class="size-24 rounded-l shrink-0"
						:class="{
							'bg-green-100': resource.document_type === 'Site',
							'bg-blue-100': resource.document_type === 'Release Group',
							'bg-yellow-100': resource.document_type === 'Server',
						}"
					>
						<div
							class="size-full flex items-center justify-center rounded-l text-gray-500 font-semibold text-2xl"
						>
							<FeatherIcon
								class="size-6"
								:name="icons[resource.document_type]"
							/>
						</div>
					</div>
					<div class="px-4 py-3 flex flex-col justify-evenly">
						<div class="font-medium">{{ resource.document_name }}</div>
						<div>{{ resource.document_type }}</div>
					</div>
					<div
						class="opacity-0 group-hover:opacity-100 transition w-14 flex justify-center items-center ml-auto rounded-r"
					>
						<Button
							icon="trash-2"
							variant="ghost"
							class="text-red-600"
							@click.prevent.stop="
								$emit('remove', resource.document_type, resource.document_name)
							"
						/>
					</div>
				</div>
			</RouterLink>
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
