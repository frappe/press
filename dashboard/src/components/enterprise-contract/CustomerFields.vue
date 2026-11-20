<template>
	<div class="flex flex-col gap-4">
		<div class="grid grid-cols-1 gap-4 sm:grid-cols-2">
			<FormControl
				v-model="order.billing_email"
				label="Billing email"
				type="email"
				:required="true"
			/>
			<FormControl v-model="order.contact_person" label="Contact person" />
			<FormControl v-model="order.designation" label="Designation" />
		</div>
		<FormControl
			v-model="order.legal_entities_covered"
			label="Legal entities covered"
			description="Comma separated, if more than one."
		/>
	</div>
</template>

<script setup>
import { FormControl } from 'frappe-ui'

defineProps({ order: { type: Object, required: true } })
</script>
