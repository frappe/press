<template>
	<div class="sticky top-0 z-10 shrink-0">
		<Header>
			<Breadcrumbs
				:items="[
					{ label: 'Contracts', route: '/contracts' },
					{ label: name, route: `/contracts/${name}` },
				]"
			/>
		</Header>
	</div>

	<div class="mx-auto w-full max-w-3xl px-4 sm:px-5">
		<div
			v-if="contract.loading && !contract.data"
			class="flex justify-center py-24"
		>
			<Spinner class="h-6" />
		</div>
		<ErrorMessage
			v-else-if="contract.error"
			class="py-6"
			:message="contract.error"
		/>
		<ContractDetails
			v-else-if="contract.data"
			class="py-8"
			:contract="contract.data"
		/>
	</div>
</template>

<script setup>
import { Breadcrumbs, createResource, ErrorMessage, Spinner } from 'frappe-ui'
import ContractDetails from '../components/enterprise-contract/ContractDetails.vue'
import Header from '../components/Header.vue'

const props = defineProps({ name: { type: String, required: true } })

const contract = createResource({
	url: 'press.api.enterprise_contract.get_contract',
	params: { name: props.name },
	auto: true,
})
</script>
