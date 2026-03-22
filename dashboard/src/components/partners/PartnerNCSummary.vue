<template>
	<div class="py-5 pl-5 flex-col">
		<div class="text-2xl text-gray-800 font-medium">
			Non Conformance Details
		</div>
		<div class="p-4 my-4 rounded border gap-5 bg-gray-50 flex flex-col">
			<div>
				<div class="text-sm text-gray-600">Department</div>
				<div class="text-base text-gray-800">
					{{ ncSummary?.doc?.department }}
				</div>
			</div>
			<div class="flex justify-between">
				<div class="flex flex-col gap-5">
					<div>
						<div class="text-sm text-gray-600">Audit Conducted By</div>
						<div class="text-base text-gray-800">
							{{ ncSummary?.doc?.auditor }}
						</div>
					</div>
					<div>
						<div class="text-sm text-gray-600">Conducted On</div>
						<div class="text-base text-gray-800">
							{{ formatDate(ncSummary?.doc?.audit_date) }}
						</div>
					</div>
				</div>
				<div class="flex flex-col gap-5 text-right">
					<div>
						<div class="text-sm text-gray-600">NC Closed By</div>
						<div class="text-base text-gray-800">
							{{ ncSummary?.doc?.closed_by }}
						</div>
					</div>
					<div>
						<div class="text-sm text-gray-600">NC Closed On</div>
						<div class="text-base text-gray-800">
							{{ formatDate(ncSummary?.doc?.closed_on) }}
						</div>
					</div>
				</div>
			</div>
		</div>
		<div class="p-4 mt-4 gap-5 flex-col border rounded bg-gray-50">
			<div class="flex-1 pb-5">
				<div class="text-sm text-gray-600">Statement</div>
				<div class="text-base text-gray-800">
					{{ ncSummary?.doc?.nc_statement }}
				</div>
			</div>
			<div class="flex-1">
				<div class="text-sm text-gray-600">Description</div>
				<div class="text-base text-gray-800 whitespace-pre-line leading-6">
					<p>
						{{ ncSummary?.doc?.nc_description }}
					</p>
				</div>
			</div>
		</div>
		<div class="p-4 mt-4 flex-col border rounded bg-gray-50">
			<div class="flex-1">
				<div class="text-sm text-gray-600 mb-2">Measures to be taken</div>
				<div class="text-base text-gray-800 whitespace-pre-line leading-6">
					{{ ncSummary?.doc?.measures_to_close_nc }}
				</div>
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

const ncSummary = createDocumentResource({
	doctype: 'Partner Non Conformance',
	name: props.nc,
	auto: true,
});

watch(
	() => props.nc,
	(newVal) => {
		if (newVal) {
			ncSummary.name = newVal;
			ncSummary.reload();
		}
	},
);

const formatDate = (dateString) => {
	return new Date(dateString).toLocaleDateString('en-US', {
		year: 'numeric',
		month: 'long',
		day: 'numeric',
	});
};
</script>
