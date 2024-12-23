<template>
	<div class="flex flex-col gap-5 overflow-y-auto px-60 pt-6">
		<div class="rounded-lg text-base text-gray-900 shadow">
			<div class="flex flex-col gap-2.5 p-4">
				<div class="flex items-center justify-between mb-3">
					<h3 class="text-lg font-semibold">Revenue Contribution</h3>
					<Button
						label="View Details"
						@click="showPartnerContributionDialog = true"
					/>
				</div>
				<div class="grid grid-cols-2 gap-7">
					<div>
						<div class="text-sm text-gray-600">Current Month Contribution</div>
						<div class="text-xl font-bold mt-2">
							{{ currency }}
							{{
								partnerDetails.data?.custom_ongoing_period_fc_invoice_contribution.toFixed(
									2
								) || '0.0'
							}}
						</div>
					</div>
					<div>
						<div class="text-sm text-gray-600">Previous Month Contribution</div>
						<div class="text-xl font-bold mt-1">
							{{ currency }}
							{{
								partnerDetails.data?.custom_fc_invoice_contribution.toFixed(
									2
								) || '0.0'
							}}
						</div>
					</div>
				</div>
				<div class="col-span-2">
					<div class="flex items-center space-x-2">
						<p class="text-sm text-gray-600">Month-over-Month Change:</p>
						<div class="flex items-center">
							<FeatherIcon
								:name="revenueChangeIcon"
								class="w-4 h-4"
								:class="revenueChangeColor"
							/>
							<span class="ml-1 font-semibold" :class="revenueChangeColor">
								{{ Math.abs(revenueChange).toFixed(1) }}%
							</span>
						</div>
					</div>
				</div>
			</div>
		</div>
		<div class="rounded-lg text-base text-gray-900 shadow">
			<div class="flex flex-col gap-2.5 p-4">
				<div class="flex items-center mb-3">
					<h3 class="font-semibold text-lg">Partner Details</h3>
				</div>
				<!-- <div class="my-3 h-px bg-gray-100"/> -->
				<div class="grid grid-cols-2 gap-4">
					<div>
						<div class="text-sm text-gray-600">Name</div>
						<div class="text-base font-medium mt-1">
							{{ partner.partnerName }}
						</div>
					</div>
					<div>
						<div class="text-sm text-gray-600">Company Name</div>
						<div class="text-base font-medium mt-1">
							{{ partner.companyName }}
						</div>
					</div>
					<div>
						<div>
							<div class="text-sm text-gray-600">Code</div>
							<div class="text-base font-medium mt-1">
								{{ partner.partnerCode }}
							</div>
						</div>
					</div>
					<div>
						<div>
							<div class="text-sm text-gray-600">Tier</div>
							<div>
								<Badge :theme="getTierVariant(partner.partnerTier)" size="lg">
									{{ partner.partnerTier }}
								</Badge>
							</div>
						</div>
					</div>
				</div>
				<div class="my-2 h-px bg-gray-100" />
				<div class="bg-gray-50 p-3 rounded flex flex-col gap-3">
					<div class="flex gap-2 justify-between">
						<div class="flex gap-1">
							<div>
								<FeatherIcon name="calendar" class="h-4 text-gray-600" />
							</div>
							<div>
								<p class="text-sm text-gray-600">Next Renewal Date</p>
								<p class="text-base font-medium my-2">
									{{ formatDate(partnerDetails.data?.end_date) }}
								</p>
								<p class="text-sm text-gray-500">
									{{ daysUntilRenewal }} days remaining
								</p>
							</div>
						</div>
						<div class="flex gap-1">
							<div>
								<FeatherIcon name="users" class="h-4 text-gray-600" />
							</div>
							<div>
								<p class="text-sm text-gray-600">Certified Members</p>
								<p class="text-base font-medium my-2">5</p>
							</div>
						</div>
						<div class="flex gap-1">
							<div>
								<FeatherIcon name="percent" class="h-4 text-gray-600" />
							</div>
							<div>
								<p class="text-sm text-gray-600">Discount Applied</p>
								<p class="text-base font-medium my-2">8%</p>
							</div>
						</div>
					</div>
					<div v-if="isRenewalPeriod()">
						<div class="my-1 h-px bg-gray-300" />
						<div
							class="flex items-center justify-between rounded py-2 bg-gray-300 px-2"
						>
							<div>
								<p>Click here to pay for Partnership Renewal Fee</p>
							</div>
							<div>
								<Button
									label="Renew Now"
									variant="solid"
									@click="buyPartnershipCreditsDialog = true"
								/>
							</div>
						</div>
					</div>
				</div>
			</div>
		</div>
		<Dialog
			:show="showPartnerContributionDialog"
			v-model="showPartnerContributionDialog"
			:options="{ size: '3xl', title: 'Contributions of this month' }"
		>
			<template #body-content>
				<PartnerContribution :partnerEmail="team.doc.partner_email" />
			</template>
		</Dialog>
	</div>
</template>

<script setup>
import { computed, inject, ref } from 'vue';
import dayjs from '../../utils/dayjs';
import { FeatherIcon, Badge, Button, createResource } from 'frappe-ui';
import PartnerContribution from './PartnerContribution.vue';

const team = inject('team');
const currency = computed(() => (team.doc.currency == 'INR' ? '₹' : '$'));

const showPartnerContributionDialog = ref(false);
const buyPartnershipCreditsDialog = ref(false);

const partnerDetails = createResource({
	url: 'press.api.partner.get_partner_details',
	auto: true,
	cache: 'partnerDetails',
	params: {
		partner_email: team.doc.partner_email
	}
});

const partner = {
	partnerName: partnerDetails.data?.partner_name,
	companyName: partnerDetails.data?.company_name,
	currentMonthRevenue:
		partnerDetails.data?.custom_ongoing_period_fc_invoice_contribution,
	previousMonthRevenue: partnerDetails.data?.custom_fc_invoice_contribution,
	partnerTier: partnerDetails.data?.partner_type,
	partnerCode: team.doc.partner_referral_code,
	renewalDate: partnerDetails.data?.end_date,
	certifiedMembers: partnerDetails.data?.custom_number_of_certified_members,
	discountPercentage: 25
};

const daysUntilRenewal = computed(() => {
	const today = new Date();
	const renewal = new Date(partnerDetails.data?.end_date);
	return Math.ceil((renewal - today) / (1000 * 60 * 60 * 24));
});

function isRenewalPeriod() {
	// 15 days before renewal date
	const renewal = dayjs(partnerDetails.data?.end_date);
	const today = dayjs();
	const daysDifference = renewal.diff(today, 'days');

	return Boolean(daysDifference >= 0 && daysDifference <= 15);
}

const revenueChangeIcon = computed(() => {
	if (revenueChange.value > 0) return 'trending-up';
	if (revenueChange.value < 0) return 'trending-down';
	return 'minus';
});

const revenueChangeColor = computed(() => {
	if (revenueChange.value > 0) return 'text-green-500';
	if (revenueChange.value < 0) return 'text-red-500';
	return 'text-gray-500';
});

const revenueChange = computed(() => {
	return (
		((partner.currentMonthRevenue - partner.previousMonthRevenue) /
			partner.previousMonthRevenue) *
		100
	);
});

const getTierVariant = tier => {
	switch (tier) {
		case 'Gold':
			return 'orange';
		case 'Silver':
			return 'blue';
		case 'Bronze':
			return 'red';
		default:
			return 'gray';
	}
};

const formatDate = dateString => {
	return new Date(dateString).toLocaleDateString('en-US', {
		year: 'numeric',
		month: 'long',
		day: 'numeric'
	});
};
</script>
