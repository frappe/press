<script setup lang="ts">
import { createResource, FormControl } from 'frappe-ui'
import { computed, inject, onMounted, ref, useTemplateRef } from 'vue'
import EmailInput from '@/components/EmailInput.vue'
import PhoneInput from '@/components/PhoneInput.vue'
import PostRegistrationMessage from '@/onboarding/modal/PostRegistrationMessage.vue'
import { usePartnerOnboarding } from '@/onboarding/usePartnerOnboarding'

const emit = defineEmits(['registered'])

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

const errors = computed(() => {
	if (!submitted.value) return {}
	return {
		company_name: !onboarding.form.company_name,
		country: !onboarding.form.registered_country,
		contact: !onboarding.form.contact,
	}
})

const companyNameRef = useTemplateRef('companyNameRef')
const emailInputRef = useTemplateRef('emailInputRef')

onMounted(() => {
	companyNameRef.value?.$el?.querySelector('input')?.focus()
})

const handleSubmit = async () => {
	submitted.value = true
	submitError.value = ''

	const hasErrors = Object.values(errors.value).some(Boolean)
	if (hasErrors || !emailInputRef.value?.validate()) return

	try {
		await onboarding.save()
		registered.value = true
		emit('registered')
	} catch (error: any) {
		submitError.value = error.messages?.[0] || error.message
	}
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
			Register your company to become a partner
		</p>

		<FormControl
			v-model="onboarding.form.company_name"
			ref="companyNameRef"
			label="Company name"
			type="text"
			size="sm"
			variant="outline"
			placeholder="Registered company name"
			:class="{ 'has-error': errors.company_name }"
		/>
		<p v-if="errors.company_name" class="-mt-2 text-sm text-ink-red-4">
			Company name is required.
		</p>

		<FormControl
			v-model="onboarding.form.registered_country"
			label="Registered country"
			type="select"
			size="sm"
			variant="outline"
			placeholder="Select"
			:options="countryOptions"
			:class="{ 'has-error': errors.country }"
		/>
		<p v-if="errors.country" class="-mt-2 text-sm text-ink-red-4">
			Registered country is required.
		</p>

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
			Contact number is required.
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
