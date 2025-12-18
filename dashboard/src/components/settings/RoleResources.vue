<template>
	<div class="grid grid-cols-3 gap-4 text-base">
		<div
			v-for="resource in resources"
			class="group flex h-24 rounded shadow hover:shadow-lg transition"
		>
			<div class="size-24 rounded-l">
				<div
					class="size-full bg-gray-200 flex items-center justify-center rounded-l text-gray-500 font-semibold text-2xl"
				>
					<FeatherIcon class="size-6" :name="icons[resource.document_type]" />
				</div>
			</div>
			<div class="px-4 py-3 flex flex-col justify-evenly">
				<div class="font-medium">{{ resource.document_name }}</div>
				<div>{{ resource.document_type }}</div>
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
import { Button, FeatherIcon } from 'frappe-ui';

withDefaults(
	defineProps<{
		resources?: Array<any>;
	}>(),
	{
		resources: () => [],
	},
);

const icons = {
	'Release Group': 'package',
	Server: 'server',
	Site: 'globe',
};
</script>
