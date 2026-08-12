<script setup lang="ts">
import { Autocomplete, createResource, FormControl, Tooltip } from 'frappe-ui'
import { computed, inject, onMounted, ref, useTemplateRef, watch } from 'vue'
import EmailInput from '@/components/EmailInput.vue'
import PhoneInput from '@/components/PhoneInput.vue'
import PostRegistrationMessage from '@/onboarding/modal/PostRegistrationMessage.vue'
import { usePartnerOnboarding } from '@/onboarding/usePartnerOnboarding'
import { indianStates } from '@/utils/billing.js'
import LucideChevronDown from '~icons/lucide/chevron-down'
import LucideInfo from '~icons/lucide/info'

const emit = defineEmits(['registered', 'updated'])

const props = defineProps<{
	editMode?: boolean
}>()

const registered = ref(false)
const submitted = ref(false)
const submitError = ref('')
const team = inject('team')
const onboarding = usePartnerOnboarding(team as any)

const countryListResource = createResource({
	url: 'press.api.account.get_countries_with_isd_codes',
	cache: 'partnerOnboardingCountries',
	auto: true,
})

const countryOptions = computed(() => {
	return (countryListResource.data || []).map((c) => ({
		label: c.name,
		value: c.name,
	}))
})

const indianStateOptions = indianStates.map((state) => ({
	label: state,
	value: state,
}))

const isIndia = computed(
	() => onboarding.form.registered_country === 'India',
)

type AutocompleteOption = { label: string; value: string }

function optionValue(
	option: AutocompleteOption | string | null | undefined,
) {
	if (!option) return ''
	return typeof option === 'string' ? option : option.value || ''
}

function setRegisteredCountry(
	option: AutocompleteOption | string | null | undefined,
) {
	onboarding.form.registered_country = optionValue(option)
}

function setRegisteredState(
	option: AutocompleteOption | string | null | undefined,
) {
	onboarding.form.registered_state = optionValue(option)
}

const companyNameMinLength = 2
const companyNameMaxLength = 140
const contactMinLength = 7
const contactMaxLength = 20

function getLengthError(
	value: string | undefined,
	label: string,
	min: number,
	max: number,
) {
	const trimmedValue = String(value || '').trim()
	if (!trimmedValue) return `${label} is required.`
	if (trimmedValue.length < min) {
		return `${label} must be at least ${min} characters.`
	}
	if (trimmedValue.length > max) {
		return `${label} must be ${max} characters or less.`
	}
	return ''
}

function getContactError(value: string | undefined) {
	const trimmedValue = String(value || '').trim()
	if (!trimmedValue) return 'Contact number is required.'

	const digits = trimmedValue.replace(/\D/g, '')
	if (digits.length < contactMinLength || digits.length > contactMaxLength) {
		return `Contact number must be ${contactMinLength}-${contactMaxLength} digits.`
	}
	return ''
}

const errors = computed(() => {
	if (!submitted.value) return {}
	return {
		company_name: getLengthError(
			onboarding.form.company_name,
			'Company name',
			companyNameMinLength,
			companyNameMaxLength,
		),
		country: onboarding.form.registered_country
			? ''
			: 'Registered country is required.',
		registered_state:
			isIndia.value && !onboarding.form.registered_state
				? 'Registered state is required.'
				: '',
		contact: getContactError(onboarding.form.contact),
	}
})

const companyNameRef = useTemplateRef('companyNameRef')
const emailInputRef = useTemplateRef('emailInputRef')

// The backend phone error names the rejected number, so clear it the moment
// the user edits the contact — otherwise the stale message lingers.
watch(
	() => onboarding.form.contact,
	() => {
		submitError.value = ''
	},
)

watch(
	() => onboarding.form.registered_country,
	(country) => {
		if (country !== 'India') {
			onboarding.form.registered_state = ''
		}
	},
)

onMounted(() => {
	companyNameRef.value?.$el?.querySelector('input')?.focus()
})

const handleSubmit = async (event?: Event) => {
	// frappe-ui Autocomplete's default trigger is <button> without type="button",
	// so browsers treat it as submit. Only Proceed (form="registration-form")
	// should flip validation into the dirty/error state.
	const submitter =
		event && 'submitter' in event
			? (event as SubmitEvent).submitter
			: null
	if (
		submitter instanceof HTMLElement &&
		submitter.getAttribute('form') !== 'registration-form'
	) {
		return
	}

	submitted.value = true
	submitError.value = ''

	const hasErrors = Object.values(errors.value).some(Boolean)
	if (hasErrors || !emailInputRef.value?.validate()) return

	// Freeze before save — first-time Proceed creates a Draft, which would
	// otherwise flip parent isEditMode mid-submit and emit "updated" instead
	// of the post-registration success → partner-onboarding path.
	const editingExistingDraft = Boolean(props.editMode)

	try {
		await onboarding.save()
		void onboarding.loadMRRStatus()

		if (editingExistingDraft) {
			emit('updated')
			return
		}

		registered.value = true
		emit('registered')
	} catch (error: any) {
		// Backend validation (e.g. the Phone field) wraps values in <strong>
		// tags via frappe.bold(); strip them so they don't render as literal
		// markup in the plain-text error below.
		const message = error.messages?.[0] || error.message || ''
		submitError.value = stripHtmlTags(message)
	}
}

function stripHtmlTags(value: string) {
	return value.replace(/<[^>]*>/g, '')
}
</script>

<template>
	<PostRegistrationMessage v-if="registered" />

	<form
		v-else
		id="registration-form"
		novalidate
		class="flex flex-col gap-4"
		@submit.prevent="handleSubmit"
	>
		<p class="text-p-base text-ink-gray-6">
			{{
				props.editMode
					? 'Update your company registration details'
					: 'Register your company to become a partner'
			}}
		</p>

		<FormControl
			v-model="onboarding.form.company_name"
			ref="companyNameRef"
			label="Company name"
			type="text"
			size="sm"
			variant="outline"
			placeholder="Registered company name"
			:minlength="companyNameMinLength"
			:maxlength="companyNameMaxLength"
			:class="{ 'has-error': errors.company_name }"
		/>
		<p v-if="errors.company_name" class="-mt-2 text-sm text-ink-red-4">
			{{ errors.company_name }}
		</p>

		<div class="flex flex-col gap-1.5">
			<div class="flex items-end gap-1">
				<label class="block text-xs text-ink-gray-5">Registered country</label>
				<Tooltip
					text="You'll be listed as a partner in this country, subject to approval and verification."
				>
					<LucideInfo class="h-3 w-3 text-ink-gray-5" />
				</Tooltip>
			</div>
			<div :class="{ 'has-error': errors.country }">
				<Autocomplete
					placeholder="Select"
					:model-value="onboarding.form.registered_country"
					:options="countryOptions"
					:max-options="countryOptions.length || 300"
					@update:model-value="setRegisteredCountry"
				>
					<template #target="{ togglePopover, isOpen }">
						<button
							type="button"
							class="flex h-7 w-full items-center justify-between gap-2 rounded border border-outline-gray-2 bg-surface-white px-2 text-base outline-none transition-colors hover:border-outline-gray-3 focus:ring-2 focus:ring-outline-gray-3"
							:class="{ 'ring-2 ring-outline-gray-3': isOpen }"
							@click="togglePopover()"
						>
							<span
								class="truncate"
								:class="
									onboarding.form.registered_country
										? 'text-ink-gray-7'
										: 'text-ink-gray-4'
								"
							>
								{{ onboarding.form.registered_country || 'Select' }}
							</span>
							<LucideChevronDown class="size-4 shrink-0 text-ink-gray-4" />
						</button>
					</template>
				</Autocomplete>
			</div>
		</div>
		<p v-if="errors.country" class="-mt-2 text-sm text-ink-red-4">
			{{ errors.country }}
		</p>

		<div v-if="isIndia" class="flex flex-col gap-1.5">
			<label class="block text-xs text-ink-gray-5">Registered state</label>
			<div :class="{ 'has-error': errors.registered_state }">
				<Autocomplete
					placeholder="Select"
					:model-value="onboarding.form.registered_state"
					:options="indianStateOptions"
					:max-options="indianStateOptions.length"
					@update:model-value="setRegisteredState"
				>
					<template #target="{ togglePopover, isOpen }">
						<button
							type="button"
							class="flex h-7 w-full items-center justify-between gap-2 rounded border border-outline-gray-2 bg-surface-white px-2 text-base outline-none transition-colors hover:border-outline-gray-3 focus:ring-2 focus:ring-outline-gray-3"
							:class="{ 'ring-2 ring-outline-gray-3': isOpen }"
							@click="togglePopover()"
						>
							<span
								class="truncate"
								:class="
									onboarding.form.registered_state
										? 'text-ink-gray-7'
										: 'text-ink-gray-4'
								"
							>
								{{ onboarding.form.registered_state || 'Select' }}
							</span>
							<LucideChevronDown class="size-4 shrink-0 text-ink-gray-4" />
						</button>
					</template>
				</Autocomplete>
			</div>
			<p v-if="errors.registered_state" class="text-sm text-ink-red-4">
				{{ errors.registered_state }}
			</p>
		</div>

		<EmailInput
			v-model="onboarding.form.company_email"
			ref="emailInputRef"
			label="Company email"
			placeholder="Email"
			:show-error="submitted"
			show-icon
			required-message="Company email is required."
			invalid-message="Enter a valid company email."
		/>

		<PhoneInput
			v-model="onboarding.form.contact"
			label="Contact"
			:countries="countryListResource.data || []"
			:country="onboarding.form.registered_country"
			placeholder="Mobile number"
			:class="{ 'has-error': errors.contact }"
		/>
		<p v-if="errors.contact" class="-mt-2 text-sm text-ink-red-4">
			{{ errors.contact }}
		</p>

		<p v-if="submitError" class="text-sm text-ink-red-4">
			{{ submitError }}
		</p>
	</form>
</template>

<style scoped>
.has-error :deep(input),
.has-error :deep(button) {
	border-color: var(--outline-red-3);
}
</style>
