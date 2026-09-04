<template>
	<div class="flex flex-col gap-5 overflow-y-auto px-10 lg:px-80 py-6">
		<div class="flex flex-col">
			<div class="text-ink-gray-5">Welcome back!</div>
			<div class="flex items-center gap-3">
				<h1 class="text-3xl font-semibold">
					{{ partnerDetails.data?.company_name }}
				</h1>
				<Badge
					variant="subtle"
					:label="team.doc.partner_status"
					:theme="team.doc.partner_status == 'Active' ? 'green' : 'gray'"
				/>
			</div>
		</div>

		<div class="rounded-lg text-base text-ink-gray-9 border">
			<div class="flex flex-col gap-4 p-5">
				<div class="flex items-center gap-2">
					<div
						class="flex h-8 w-8 shrink-0 items-center justify-center rounded-full bg-surface-gray-2"
					>
						<FeatherIcon name="award" class="h-4 w-4 text-ink-gray-7" />
					</div>
					<h3 class="text-lg font-semibold">
						{{ partnerDetails.data?.partner_type }}
						Tier
					</h3>
				</div>
				<div>
					<Progress
						size="lg"
						:value="tierProgressValue"
						label="Current Progress"
						:hint="false"
					>
						<template #hint>
							<span class="text-base font-medium text-ink-gray-5">
								{{ formatNumber(nextTierTarget) }}
								to reach {{ nextTier }}
							</span>
						</template>
					</Progress>
				</div>

				<div class="flex flex-col md:flex-row justify-between gap-4">
					<div class="flex-1 rounded-md bg-surface-gray-1 p-4">
						<div class="flex items-center justify-between">
							<div class="text-sm text-ink-gray-6">
								Current Month Contribution
							</div>
							<Button
								variant="ghost"
								label="Details"
								@click="showPartnerContributionDialog = true"
							/>
						</div>
						<div class="text-2xl font-semibold py-2 text-ink-gray-9">
							{{ formatCurrency(currentMonthContribution.data) || '0.0' }}
						</div>
						<div class="text-sm text-ink-gray-6">
							<span
								>Previous Month:
								{{ formatCurrency(prevMonthContribution.data) || '0.0' }}</span
							>
						</div>
					</div>
					<div class="flex-1 rounded-md bg-surface-gray-1 p-4">
						<div class="flex items-center justify-between">
							<div class="text-sm text-ink-gray-6">Certified Members</div>
							<Button
								variant="ghost"
								label="View"
								@click="routeToCertification()"
							/>
						</div>
						<div class="text-2xl font-semibold py-2 text-ink-gray-9">
							{{ partnerDetails.data?.custom_number_of_certified_members || 0 }}
						</div>
					</div>
				</div>
			</div>
		</div>

		<div class="rounded-lg text-base text-ink-gray-9 border p-4">
			<div
				class="flex flex-col sm:flex-row sm:items-center justify-between gap-4"
			>
				<div class="flex flex-col gap-1">
					<h3 class="font-medium text-normal">Partner Referral Code</h3>
					<span class="text-sm text-ink-gray-6"
						>Share code with customers to link with your account.</span
					>
				</div>
				<div class="w-full sm:w-72">
					<ClickToCopyField :textContent="team.doc?.partner_referral_code" />
				</div>
			</div>
		</div>

		<Dialog
			:show="showPartnerContributionDialog"
			v-model="showPartnerContributionDialog"
			:options="{ size: '5xl', title: 'Contributions of this month' }"
		>
			<template #body-content>
				<PartnerContribution :partnerEmail="team.doc.partner_email" />
			</template>
		</Dialog>
	</div>
</template>

<script setup>
import {
	Button,
	createResource,
	Dialog,
	FeatherIcon,
	Progress,
} from 'frappe-ui'
import { inject, ref, watch } from 'vue'
import router from '../../router'
import ClickToCopyField from '../ClickToCopyField.vue'
import PartnerContribution from './PartnerContribution.vue'

const team = inject('team')

const showPartnerContributionDialog = ref(false)

const partnerDetails = createResource({
	url: 'press.api.partner.get_partner_details',
	auto: true,
	cache: 'partnerDetails',
	params: {
		partner_email: team.doc.partner_email,
	},
	onSuccess(data) {
		calculateNextTier(data.partner_type)
	},
})

function routeToCertification() {
	router.push('/partners/certificates')
}

const currentMonthContribution = createResource({
	url: 'press.api.partner.get_current_month_partner_contribution',
	auto: true,
	cache: 'currentMonthContribution',
	params: {
		partner_email: team.doc.partner_email,
	},
})

const prevMonthContribution = createResource({
	url: 'press.api.partner.get_prev_month_partner_contribution',
	auto: true,
	cache: 'prevMonthContribution',
	params: {
		partner_email: team.doc.partner_email,
	},
})

const tierProgressValue = ref(0)
const nextTier = ref('')
const nextTierTarget = ref(0)

function calculateTierProgress(next_tier_value) {
	return Math.ceil((currentMonthContribution.data / next_tier_value) * 100)
}

function calculateNextTier(tier) {
	const target_inr = {
		Gold: 630000,
		Silver: 250000,
		Bronze: 63000,
		Emerging: 30000,
	}
	const target_usd = {
		Gold: 7500,
		Silver: 3150,
		Bronze: 750,
		Emerging: 350,
	}

	const current_tier = partnerDetails.data?.partner_type
	let next_tier = ''
	switch (current_tier) {
		case 'Entry':
			next_tier = 'Emerging'
			nextTierTarget.value =
				team.doc.currency === 'INR' ? target_inr.Emerging : target_usd.Emerging
			break
		case 'Emerging':
			next_tier = 'Bronze'
			nextTierTarget.value =
				team.doc.currency === 'INR' ? target_inr.Bronze : target_usd.Bronze
			break
		case 'Bronze':
			next_tier = 'Silver'
			nextTierTarget.value =
				team.doc.currency === 'INR' ? target_inr.Silver : target_usd.Silver
			break
		case 'Silver':
			next_tier = 'Gold'
			nextTierTarget.value =
				team.doc.currency === 'INR' ? target_inr.Gold : target_usd.Gold
			break
		default:
			next_tier = 'Gold'
			nextTierTarget.value =
				team.doc.currency === 'INR' ? target_inr.Gold : target_usd.Gold
	}
	nextTier.value = next_tier
	tierProgressValue.value = calculateTierProgress(nextTierTarget.value)
	nextTierTarget.value = nextTierTarget.value - currentMonthContribution.data
}

watch(
	() => partnerDetails.data,
	(newData) => {
		if (newData) {
			calculateNextTier(newData.partner_type)
		}
	},
	{ deep: true },
)

const formatCurrency = (amount) => {
	if (!amount) {
		amount = 0
	}
	return new Intl.NumberFormat('en-US', {
		style: 'currency',
		currency: team.doc.currency,
		maximumFractionDigits: 1,
	}).format(amount)
}

const formatNumber = (value) => {
	return new Intl.NumberFormat('en-US', {
		notation: 'compact',
		compactDisplay: 'short',
	}).format(value)
}
</script>
