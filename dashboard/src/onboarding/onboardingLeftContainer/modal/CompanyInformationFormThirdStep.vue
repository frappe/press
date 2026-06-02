<script setup lang="ts">
import { Checkbox, FormControl } from 'frappe-ui'
import { computed, ref } from 'vue'
import type { PartnerOnboardingDoc } from '@/onboarding/usePartnerOnboarding'

const emit = defineEmits(['continue'])
const props = defineProps<{
	form: PartnerOnboardingDoc
}>()
const submitted = ref(false)

const partnershipOptions = [
	{ label: 'ERPNext', value: 'ERPNext' },
	{ label: 'Frappe Framework', value: 'Frappe Framework' },
	{ label: 'Other ERP', value: 'Other ERP' },
]

const implementationOptions = [
	{ label: '1-10', value: '1-10' },
	{ label: '11-50', value: '11-50' },
	{ label: '51-200', value: '51-200' },
	{ label: '201+', value: '201+' },
]

const errors = computed(() => {
	if (!submitted.value) return {}
	return {
		due_diligence: !props.form.agreed_to_due_diligence,
		partnership_agreement: !props.form.agreed_to_partnership_agreement,
	}
})

const PARTNERSHIP_AGREEMENT_LINK = 'https://frappe.io/partners/terms'

function validate() {
	submitted.value = true
	return !Object.values(errors.value).some(Boolean)
}

function tryContinue() {
	if (validate()) emit('continue')
}

defineExpose({ tryContinue })
</script>

<template>
	<form
		id="company-information-form-3"
		class="flex min-h-[360px] flex-col gap-5"
		@submit.prevent="tryContinue"
	>
		<div class="flex flex-col gap-1">
			<div class="flex items-center justify-between gap-2">
				<span class="text-xs text-ink-gray-6">Existing Partnerships</span>
				<span class="text-xs text-ink-gray-5">Optional</span>
			</div>
			<FormControl
				v-model="props.form.existing_partnerships"
				type="select"
				size="sm"
				variant="outline"
				placeholder="Select"
				:options="partnershipOptions"
			/>
		</div>

		<div class="grid grid-cols-1 gap-4 sm:grid-cols-2">
			<div class="flex flex-col gap-1">
				<div class="flex items-center justify-between gap-2">
					<span class="text-xs text-ink-gray-6"
						>No. of ERP implementations</span
					>
					<span class="text-xs text-ink-gray-5">Optional</span>
				</div>
				<FormControl
					v-model="props.form.erp_implementations_range"
					type="select"
					size="sm"
					variant="outline"
					placeholder="Select"
					:options="implementationOptions"
				/>
			</div>

			<div class="flex flex-col gap-1">
				<div class="flex items-center justify-between gap-2">
					<span class="text-xs text-ink-gray-6">Incorporation certificate</span>
					<span class="text-xs text-ink-gray-5">Optional</span>
				</div>
				<FormControl
					v-model="props.form.incorporation_certificate"
					type="text"
					size="sm"
					variant="outline"
					placeholder="Certificate URL"
				/>
			</div>
		</div>

		<div class="mt-1 flex flex-col gap-3">
			<Checkbox
				v-model="props.form.agreed_to_due_diligence"
				label="I shall abide by the due diligence"
			/>
			<p v-if="errors.due_diligence" class="-mt-2 text-sm text-ink-red-4">
				Due diligence confirmation is required.
			</p>

			<div class="flex items-start gap-2">
				<Checkbox
					v-model="props.form.agreed_to_partnership_agreement"
					id="partnership-agreement-checkbox"
				/>
				<label
					for="partnership-agreement-checkbox"
					class="text-base font-medium text-ink-gray-8"
				>
					I accept the
					<a
						:href="PARTNERSHIP_AGREEMENT_LINK"
						target="_blank"
						rel="noopener noreferrer"
						class="underline"
					>
						Partnership agreement
					</a>
				</label>
			</div>
			<p
				v-if="errors.partnership_agreement"
				class="-mt-2 text-sm text-ink-red-4"
			>
				Partnership agreement acceptance is required.
			</p>
		</div>
	</form>
</template>
