<template>
	<div class="flex flex-col gap-5 overflow-y-auto px-60 py-6">
		<div class="flex flex-col">
			<div class="text-gray-500">Welcome back!</div>
			<div>
				<h1 class="text-3xl font-semibold">
					{{ partnerDetails.data?.company_name }}
				</h1>
			</div>
		</div>
		<div class="rounded-lg text-base text-gray-900 shadow">
			<div class="flex flex-col gap-2.5 p-4">
				<div class="flex items-center justify-between">
					<div class="flex">
						<FeatherIcon name="award" class="h-5 text-gray-700" />
						<h3 class="text-xl font-semibold">
							{{ partnerDetails.data?.partner_type }} Tier
						</h3>
					</div>
				</div>
				<div class="pt-2">
					<Progress
						size="lg"
						:value="tierProgressValue"
						label="Current Progress"
						:hint="false"
					>
						<template #hint>
							<span class="text-base font-medium text-gray-500">
								{{ formatNumber(nextTierTarget) }} to reach {{ nextTier }}
							</span>
						</template>
					</Progress>
				</div>
				<div class="my-1 h-px bg-gray-100" />

				<div class="grid grid-cols-2 gap-4">
					<div>
						<div class="flex items-center justify-between">
							<div class="text-sm text-gray-600">
								Current Month Contribution
							</div>
							<Button
								label="Details"
								@click="showPartnerContributionDialog = true"
							/>
						</div>
						<div class="text-xl font-semibold py-2">
							{{
								formatCurrency(
									partnerDetails.data
										?.custom_ongoing_period_fc_invoice_contribution
								) || '0.0'
							}}
						</div>
						<div class="text-sm text-gray-600">
							<span
								>Previous Month:
								{{
									formatCurrency(
										partnerDetails.data?.custom_fc_invoice_contribution
									) || '0.0'
								}}</span
							>
						</div>
					</div>
					<div>
						<div class="flex items-center justify-between">
							<div class="text-sm text-gray-600">Certified Members</div>
							<Button label="View" />
						</div>
						<div class="flex items-center">
							<div class="text-xl font-semibold py-2">
								{{
									partnerDetails.data?.custom_number_of_certified_members || 5
								}}
							</div>
						</div>
					</div>
				</div>
			</div>
		</div>

		<div class="flex gap-4">
			<div class="rounded-lg text-base w-full text-gray-900 shadow">
				<div class="flex items-center px-4 pt-4">
					<h3 class="font-semibold text-lg">Partner Referral Code</h3>
				</div>
				<div class="flex flex-col p-4 gap-2">
					<ClickToCopyField :textContent="team.doc?.partner_referral_code" />
					<span class="text-sm text-gray-600"
						>Share code with customers to link with your account.</span
					>
				</div>
			</div>
			<div class="rounded-lg text-base w-full text-gray-900 p-4 shadow">
				<div class="flex h-full flex-col justify-between">
					<div class="flex">
						<h3 class="font-semibold text-lg">Renewal Details</h3>
					</div>
					<div class="flex items-center justify-between">
						<div class="flex flex-col gap-2">
							<span class="text-base font-medium text-gray-700">
								{{ formatDate(partnerDetails.data?.end_date) }}
							</span>
						</div>
						<div v-if="isRenewalPeriod()">
							<Button
								label="Renew"
								:disabled="false"
								:variant="'solid'"
								@click="showPartnerCreditsDialog = true"
							/>
						</div>
					</div>
					<span class="text-sm text-gray-600"
						>Renewal in {{ daysUntilRenewal }} days</span
					>
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

		<Dialog
			:show="showPartnerCreditsDialog"
			v-model="showPartnerCreditsDialog"
			:options="{ title: 'Pay Partnership Fee' }"
		>
			<template #body-content>
				<PartnerCreditsForm
					@success="
						() => {
							showPartnerCreditsDialog = false;
						}
					"
				/>
			</template>
		</Dialog>
	</div>
</template>

<script setup>
import { computed, inject, ref } from 'vue';
import dayjs from '../../utils/dayjs';
import { FeatherIcon, Button, createResource, Progress } from 'frappe-ui';
import PartnerContribution from './PartnerContribution.vue';
import ClickToCopyField from '../ClickToCopyField.vue';
import PartnerCreditsForm from './PartnerCreditsForm.vue';

const team = inject('team');

const showPartnerContributionDialog = ref(false);
const showPartnerCreditsDialog = ref(false);

const partnerDetails = createResource({
	url: 'press.api.partner.get_partner_details',
	auto: true,
	cache: 'partnerDetails',
	params: {
		partner_email: team.doc.partner_email
	},
	onSuccess() {
		calculateNextTier(partnerDetails.data.partner_type);
	}
});

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

const tierProgressValue = ref(0);
const nextTier = ref('');
const nextTierTarget = ref(0);

function calculateTierProgress(next_tier_value) {
	console.log(
		partnerDetails.data?.custom_ongoing_period_fc_invoice_contribution,
		next_tier_value
	);
	return Math.ceil(
		(partnerDetails.data?.custom_ongoing_period_fc_invoice_contribution /
			next_tier_value) *
			100
	);
}

function calculateNextTier(tier) {
	const target_inr = {
		Gold: 500000,
		Silver: 200000,
		Bronze: 50000
	};
	const target_usd = {
		Gold: 6000,
		Silver: 2500,
		Bronze: 600
	};

	const current_tier = partnerDetails.data?.partner_type;
	let next_tier = '';
	switch (current_tier) {
		case 'Entry':
			next_tier = 'Bronze';
			nextTierTarget.value =
				team.doc.currency === 'INR' ? target_inr.Bronze : target_usd.Bronze;
			break;
		case 'Bronze':
			next_tier = 'Silver';
			nextTierTarget.value =
				team.doc.currency === 'INR' ? target_inr.Silver : target_usd.Silver;
			break;
		case 'Silver':
			next_tier = 'Gold';
			nextTierTarget.value =
				team.doc.currency === 'INR' ? target_inr.Gold : target_usd.Gold;
			break;
		default:
			next_tier = 'Gold';
			nextTierTarget.value =
				team.doc.currency === 'INR' ? target_inr.Gold : target_usd.Gold;
	}
	nextTier.value = next_tier;
	tierProgressValue.value = calculateTierProgress(nextTierTarget.value);
	nextTierTarget.value =
		nextTierTarget.value -
		partnerDetails.data?.custom_ongoing_period_fc_invoice_contribution;
}

const formatDate = dateString => {
	return new Date(dateString).toLocaleDateString('en-US', {
		year: 'numeric',
		month: 'long',
		day: 'numeric'
	});
};

const formatCurrency = amount => {
	return new Intl.NumberFormat('en-US', {
		style: 'currency',
		currency: team.doc.currency,
		maximumFractionDigits: 2
	}).format(amount);
};

const formatNumber = value => {
	return new Intl.NumberFormat('en-US', {
		notation: 'compact',
		compactDisplay: 'short'
	}).format(value);
};
</script>
