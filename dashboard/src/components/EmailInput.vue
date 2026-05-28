<script setup lang="ts">
import { FormControl } from 'frappe-ui'
import { computed } from 'vue'
import LucideMail from '~icons/lucide/mail'

defineOptions({ inheritAttrs: false })

const email = defineModel<string | undefined>({ default: '' })

const props = withDefaults(
	defineProps<{
		label?: string
		placeholder?: string
		showError?: boolean
		requiredMessage?: string
		invalidMessage?: string
		showIcon?: boolean
	}>(),
	{
		label: 'Email',
		placeholder: 'name@example.com',
		showError: false,
		requiredMessage: 'Email is required.',
		invalidMessage: 'Enter a valid email address.',
		showIcon: false,
	},
)

function getError() {
	const value = String(email.value || '').trim()
	if (!value) return props.requiredMessage
	if (!/^\S+@\S+\.\S+$/.test(value)) return props.invalidMessage
	return ''
}

const error = computed(() => (props.showError ? getError() : ''))

function validate() {
	return !getError()
}

defineExpose({ validate })
</script>

<template>
	<div v-bind="$attrs">
		<FormControl
			v-model="email"
			:label="label"
			type="email"
			size="sm"
			variant="outline"
			:placeholder="placeholder"
			:class="{ 'has-error': error }"
		>
			<template v-if="showIcon" #prefix>
				<LucideMail class="h-4 w-4 text-ink-gray-4" />
			</template>
		</FormControl>
		<p v-if="error" class="mt-1 text-sm text-ink-red-4">
			{{ error }}
		</p>
	</div>
</template>

<style scoped>
.has-error :deep(input) {
	border-color: var(--outline-red-3);
}
</style>
