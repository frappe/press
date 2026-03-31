<template>
	<div v-if="ncSummaryDoc?.doc" class="p-5 flex-col gap-2.5">
		<div class="p-4 my-4 rounded border-[1.5px]">
			<div class="flex justify-between">
				<div class="flex flex-col gap-2.5">
					<div class="text-2xl font-medium">
						{{ ncSummaryDoc?.doc?.nc_statement }}
					</div>
					<div class="flex items-center gap-2.5 text-base text-gray-500">
						<div>
							{{ ncSummaryDoc?.doc?.name }}
						</div>
						-
						<div>{{ ncSummaryDoc?.doc?.department }}</div>
					</div>
				</div>
				<div>
					<Badge
						size="lg"
						:theme="theme_map[ncSummaryDoc?.doc?.status]"
						:label="ncSummaryDoc?.doc?.status"
					/>
				</div>
			</div>
		</div>
		<div class="p-4 my-4 rounded border-[1.5px]">
			<div class="flex flex-col gap-4">
				<div class="flex font-semibold gap-2.5 text-lg">Audit Information</div>
				<div class="grid grid-cols-2">
					<div class="flex flex-col gap-1">
						<div class="text-base text-gray-600">Conducted By</div>
						<div class="text-base text-gray-800">
							{{ ncSummaryDoc?.doc?.auditor }}
						</div>
					</div>
					<div class="flex flex-col gap-1">
						<div class="text-base text-gray-600">Conducted On</div>
						<div class="text-base text-gray-800">
							{{ formatDate(ncSummaryDoc?.doc?.audit_date) }}
						</div>
					</div>
				</div>
			</div>
		</div>
		<div class="p-4 my-4 rounded border-[1.5px]">
			<div class="flex flex-col gap-4">
				<div class="flex gap-2.5 font-semibold text-lg">
					Closure Information
				</div>
				<div class="grid grid-cols-2">
					<div class="flex flex-col gap-1">
						<div class="text-base text-gray-600">Closed By</div>
						<div class="text-base text-gray-800">
							{{ ncSummaryDoc?.doc?.closed_by }}
						</div>
					</div>
					<div class="flex flex-col gap-1">
						<div class="text-base text-gray-600">Closed On</div>
						<div class="text-base text-gray-800">
							{{ formatDate(ncSummaryDoc?.doc?.closed_on) }}
						</div>
					</div>
				</div>
			</div>
		</div>
		<div
			v-if="ncSummaryDoc?.doc?.nc_description"
			class="p-4 my-4 flex flex-col gap-2.5 rounded border-[1.5px]"
		>
			<div class="text-lg font-semibold pb-1">Description</div>
			<div class="text-base text-gray-800 whitespace-pre-line leading-relaxed">
				{{ ncSummaryDoc?.doc?.nc_description }}
			</div>
		</div>
		<div
			v-if="ncSummaryDoc?.doc?.measures_to_close_nc"
			class="p-4 my-4 flex flex-col gap-2.5 rounded border-[1.5px]"
		>
			<div class="text-lg font-semibold pb-1">Measures to be taken</div>
			<div class="text-base text-gray-800 whitespace-pre-line leading-relaxed">
				{{ ncSummaryDoc?.doc?.measures_to_close_nc }}
			</div>
		</div>
	</div>

	<div v-else>
		<div
			class="flex flex-col gap-6 items-center justify-center h-96 border-[1px] rounded p-5 ml-5"
		>
			<FeatherIcon name="file-text" class="mr-2 h-10 w-10 text-gray-500" />
			<div class="text-lg text-gray-600">
				Select a Non Conformance to view details
			</div>
		</div>
	</div>
</template>
<script setup>
import { defineProps, watch } from 'vue';
import { createDocumentResource } from 'frappe-ui';

const props = defineProps({
	nc: {
		type: String,
		required: true,
	},
});

const theme_map = {
	Open: 'blue',
	Closed: 'green',
	WIP: 'orange',
};

let ncSummaryDoc = {};

watch(
	() => props.nc,
	(newVal) => {
		if (newVal) {
			ncSummaryDoc = createDocumentResource({
				doctype: 'Partner Non Conformance',
				name: props.nc,
			});
		}
	},
	{ immediate: true },
);

const formatDate = (dateString) => {
	if (!dateString) return '-';
	return new Date(dateString).toLocaleDateString('en-US', {
		year: 'numeric',
		month: 'long',
		day: 'numeric',
	});
};
</script>
