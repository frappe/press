<script setup>
import SuccessCheckIcon from '@/components/icons/SuccessCheckIcon.vue'
import { Button } from 'frappe-ui'

// onclick continue button, close the modal
const continueButtonClick = () => {
	emit('continue')
}

const emit = defineEmits(['continue'])
</script>

<template>
	<div class="flex flex-col gap-3.5 self-stretch justify-center items-center">
		<SuccessCheckIcon class="w-10 h-10" />
		<h2 class="text-4xl-semibold text-ink-gray-8">
			Thank you for registering as a Frappe partner!
		</h2>
		<p class="text-p-base text-ink-gray-6 min-w-[400px]">
			We will be contacting you shortly via email to guide you along the
			partnership journey.
		</p>

		<Button variant="solid" size="sm" @click="continueButtonClick">
			Continue your journey
		</Button>
	</div>
</template>
