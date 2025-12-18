<template>
	<div class="flex flex-col gap-5 overflow-y-auto px-60 py-6 max-h-screen">
		<div class="rounded-lg text-base text-gray-900 border">
			<div class="flex h-full flex-col justify-between p-4 gap-2">
				<div class="flex justify-between items-center">
					<h3 class="font-semibold text-lg">Website Info</h3>
					<Button label="Edit" @click="showUpdateWebsiteInfo = true" />
				</div>
				<div class="my-1 h-px bg-gray-100" />
				<div class="flex flex-col gap-6">
					<div class="flex">
						<div class="flex-1 flex-col">
							<div class="text-sm text-gray-600">Partner Website</div>
							<div class="text-base font-medium text-gray-700 py-2">
								{{ partnerDetails.data?.partner_website || '' }}
							</div>
						</div>
						<div class="flex-1 flex-col">
							<div class="text-sm text-gray-600">Contact</div>
							<div class="text-base font-medium text-gray-700 py-2">
								{{ partnerDetails.data?.phone_number || '' }}
							</div>
						</div>
						<div class="flex-1 flex-col">
							<div class="text-sm text-gray-600">Journey Blog Link</div>
							<div class="text-base font-medium text-gray-700 py-2">
								{{ partnerDetails.data?.custom_journey_blog_link || '-' }}
							</div>
						</div>
					</div>
					<div class="flex">
						<div class="flex-1 flex-col">
							<div class="text-sm text-gray-600">Foundation Date</div>
							<div class="text-base font-medium text-gray-700 py-2">
								{{
									formatDate(partnerDetails.data?.custom_foundation_date) || '-'
								}}
							</div>
						</div>
						<div class="flex-1 flex-col">
							<div class="text-sm text-gray-600">Team Size</div>
							<div class="text-base font-medium text-gray-700 py-2">
								{{ partnerDetails.data?.custom_team_size || '-' }}
							</div>
						</div>
						<div class="flex-1 flex-col">
							<div class="text-sm text-gray-600">Successfull Projects</div>
							<div class="text-base font-medium text-gray-700 py-2">
								{{
									partnerDetails.data?.custom_successful_projects_count || '-'
								}}
							</div>
						</div>
					</div>
					<div class="flex gap-4 pt-4">
						<div class="flex-1">
							<div class="text-sm text-gray-600 pb-3">Introduction</div>
							<div class="text-base leading-6 text-gray-700 py-1">
								<div v-html="partnerDetails.data?.introduction"></div>
							</div>
						</div>
						<div class="flex-1">
							<div class="text-sm text-gray-600 pb-3">Customers</div>
							<div
								v-for="customer in customerList.slice(0, 10)"
								class="text-base text-gray-700 py-1"
							>
								<li>{{ customer }}</li>
							</div>
							<div
								v-if="customerList.length > 10"
								class="text-sm text-gray-600 py-3"
							>
								... And many more
							</div>
						</div>
						<div class="flex-1 flex-col">
							<div class="text-sm text-gray-600">Address</div>
							<div class="text-base leading-6 text-gray-700 py-2">
								<div v-html="partnerDetails.data?.address"></div>
							</div>
						</div>
					</div>
				</div>
			</div>
		</div>

		<Dialog
			:show="showUpdateWebsiteInfo"
			v-model="showUpdateWebsiteInfo"
			:options="{ title: 'Update Website Info', size: '4xl' }"
		>
			<template #body-content>
				<WebsiteInfoDialog
					v-model="partnerDetails.data"
					@success="
						() => {
							partnerDetails.reload();
							showUpdateWebsiteInfo = false;
						}
					"
				/>
			</template>
		</Dialog>
	</div>
</template>
<script setup>
import { ref, inject, computed } from 'vue';
import { createResource, Button, Dialog } from 'frappe-ui';

const team = inject('team');
const showUpdateWebsiteInfo = ref(false);

const partnerDetails = createResource({
	url: 'press.api.partner.get_partner_details',
	auto: true,
	cache: 'partnerDetails',
	params: {
		partner_email: team.doc.partner_email,
	},
});

const customerList = computed(
	() => partnerDetails?.data?.customers?.split(',') || [],
);

const formatDate = (dateString) => {
	return new Date(dateString).toLocaleDateString('en-US', {
		year: 'numeric',
		month: 'long',
		day: 'numeric',
	});
};
</script>
