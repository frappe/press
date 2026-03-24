<template>
	<div v-if="ncSummaryDoc?.doc" class="pl-5 flex-col">
		<div class="text-lg text-gray-600 flex">
			<FeatherIcon name="file-text" class="mr-2 h-5 w-5 text-gray-600" />
			Details
		</div>
		<div class="p-4 my-4 rounded gap-5 bg-gray-50">
			<div class="flex justify-between">
				<div class="flex flex-col gap-5">
					<div>
						<div class="text-base text-gray-600 pb-1">Summary</div>
						<div class="text-base text-gray-800">
							{{ ncSummaryDoc?.doc?.nc_statement }}
						</div>
					</div>
					<div>
						<div class="text-base text-gray-600 pb-1">Audit Conducted By</div>
						<div class="text-base text-gray-800">
							{{ ncSummaryDoc?.doc?.auditor }}
						</div>
					</div>
					<div>
						<div class="text-base text-gray-600 pb-1">Conducted On</div>
						<div class="text-base text-gray-800">
							{{ formatDate(ncSummaryDoc?.doc?.audit_date) }}
						</div>
					</div>
				</div>
				<div class="flex flex-col gap-5 text-right">
					<div>
						<div class="text-base text-gray-600 pb-1">ID</div>
						<div class="text-base text-gray-800">
							{{ ncSummaryDoc?.doc?.name }}
						</div>
					</div>
					<div>
						<div class="text-base text-gray-600 pb-1">Closed By</div>
						<div class="text-base text-gray-800">
							{{ ncSummaryDoc?.doc?.closed_by }}
						</div>
					</div>
					<div>
						<div class="text-base text-gray-600 pb-1">Closed On</div>
						<div class="text-base text-gray-800">
							{{ formatDate(ncSummaryDoc?.doc?.closed_on) }}
						</div>
					</div>
				</div>
			</div>
		</div>
		<div class="p-4 mt-4 gap-5 flex-col rounded border-[1.5px]">
			<div v-if="ncSummaryDoc?.doc?.nc_description" class="flex-1 pb-5">
				<div class="text-base text-gray-600 pb-1">Description</div>
				<div class="text-base text-gray-800 whitespace-pre-line leading-normal">
					{{ ncSummaryDoc?.doc?.nc_description }}
				</div>
			</div>
			<div v-if="ncSummaryDoc?.doc?.measures_to_close_nc" class="flex-1">
				<div class="text-base text-gray-600 pb-1">Measures to be taken</div>
				<div class="text-base text-gray-800 whitespace-pre-line leading-normal">
					{{ ncSummaryDoc?.doc?.measures_to_close_nc }}
				</div>
			</div>
		</div>
	</div>
	<div v-else>
		<div
			class="flex flex-col gap-6 items-center justify-center h-96 border-[1.5px] rounded p-5"
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
	return new Date(dateString).toLocaleDateString('en-US', {
		year: 'numeric',
		month: 'long',
		day: 'numeric',
	});
};
</script>
