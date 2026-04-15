<script setup>
import { computed, reactive, ref, useTemplateRef, onMounted } from 'vue';
import { FormControl, createResource } from 'frappe-ui';
import PostRegistrationMessage from '@/onboarding/modal/PostRegistrationMessage.vue';

const emit = defineEmits(['registered']);

const registered = ref(false);
const submitted = ref(false);

const countryListResource = createResource({
	url: 'press.api.account.country_list',
	cache: 'countryList',
	auto: true,
});

const countryOptions = computed(() => {
	return (countryListResource.data || []).map((c) => ({
		label: c.name,
		value: c.name,
	}));
});

const form = reactive({
	company_name: '',
	country: '',
	email: '',
	contact: '',
});

const errors = computed(() => {
	if (!submitted.value) return {};
	return {
		company_name: !form.company_name,
		country: !form.country,
		email: !form.email,
		contact: !form.contact,
	};
});

const companyNameRef = useTemplateRef('companyNameRef');

onMounted(() => {
	companyNameRef.value?.$el?.querySelector('input')?.focus();
});

const handleSubmit = () => {
	submitted.value = true;

	const hasErrors = Object.values(errors.value).some(Boolean);
	if (hasErrors) return;

	// TODO: call registration API
	registered.value = true;
	emit('registered');
};
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
			v-model="form.company_name"
			ref="companyNameRef"
			label="Company name"
			type="text"
			size="sm"
			variant="outline"
			placeholder="Registered company name"
			:class="{ 'has-error': errors.company_name }"
		/>

		<FormControl
			v-model="form.country"
			label="Registered country"
			type="select"
			size="sm"
			variant="outline"
			placeholder="Select"
			:options="countryOptions"
			:class="{ 'has-error': errors.country }"
		/>

		<FormControl
			v-model="form.email"
			label="Company email"
			type="email"
			size="sm"
			variant="outline"
			placeholder="Email"
			:class="{ 'has-error': errors.email }"
		>
			<template #prefix>
				<lucide-mail class="h-4 w-4 text-ink-gray-4" />
			</template>
		</FormControl>

		<FormControl
			v-model="form.contact"
			label="Contact"
			type="tel"
			size="sm"
			variant="outline"
			placeholder="Mobile number"
			:class="{ 'has-error': errors.contact }"
		>
			<template #prefix>
				<lucide-phone class="h-4 w-4 text-ink-gray-4" />
			</template>
		</FormControl>
	</form>
</template>

<style scoped>
.has-error :deep(input),
.has-error :deep(button[data-state]) {
	border-color: var(--outline-red-3);
}
</style>
