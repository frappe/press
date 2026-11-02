<template>
	<div>
		<div class="flex items-center gap-2 pb-3 overflow-auto">
			<TextInput
				v-model="search"
				placeholder="Search contracts"
				class="w-56 shrink-0"
			>
				<template #prefix>
					<lucide-search class="size-4 text-ink-gray-5" />
				</template>
			</TextInput>
			<MultiSelect
				v-model="selectedStatuses"
				placeholder="Status"
				class="!w-44 shrink-0 *:text-ink-gray-5"
				:options="statusOptions"
			/>
		</div>

		<div class="overflow-x-auto">
			<table class="contracts-table w-full">
				<thead class="text-ink-gray-5 text-sm">
					<tr>
						<th class="rounded-l">Contract</th>
						<th>Status</th>
						<th>Plan</th>
						<th>Yearly Price</th>
						<th>Start Date</th>
						<th class="rounded-r">Price Locked Until</th>
					</tr>
				</thead>
				<tbody class="text-base text-ink-gray-8">
					<tr v-for="row in visible" :key="row.name" class="*:border-b">
						<td class="font-medium">
							<router-link
								v-if="hasDetails(row)"
								class="hover:underline"
								:to="{ name: 'Contract', params: { name: row.name } }"
							>
								{{ row.name }}
							</router-link>
							<template v-else>{{ row.name }}</template>
						</td>
						<td>
							<Badge
								variant="subtle"
								class="w-fit"
								:theme="contractStatusBadge(row.status).theme"
							>
								<span
									class="size-1.5 rounded-full shrink-0 mr-0.5"
									:class="contractStatusBadge(row.status).dot"
								/>
								{{ row.status }}
							</Badge>
						</td>
						<td>{{ row.plan_title }}</td>
						<td>{{ money(row.yearly_price, row.currency) }}</td>
						<td>{{ hasDetails(row) ? formatDate(row.start_date) : '—' }}</td>
						<td>
							{{ hasDetails(row) ? formatDate(row.price_locked_until) : '—' }}
						</td>
					</tr>
				</tbody>
			</table>
		</div>

		<div
			v-if="!visible.length"
			class="py-10 text-center text-sm text-ink-gray-5"
		>
			No contracts
		</div>

		<div class="flex justify-end py-2 text-sm text-ink-gray-5">
			Total {{ visible.length }}
			{{ visible.length === 1 ? 'contract' : 'contracts' }}
		</div>
	</div>
</template>

<script setup>
import { Badge, MultiSelect, TextInput } from 'frappe-ui'
import { computed, ref } from 'vue'
import { contractStatusBadge, formatDate, money } from './format'

const props = defineProps({
	contracts: { type: Array, required: true },
})

const statusOptions = ['Pending Signature', 'Active', 'Cancelled'].map(
	(label) => ({ label, value: label }),
)

const search = ref('')
const selectedStatuses = ref([])

const visible = computed(() => {
	const query = search.value.trim().toLowerCase()
	return props.contracts.filter(
		(row) =>
			(!selectedStatuses.value.length ||
				selectedStatuses.value.includes(row.status)) &&
			`${row.name} ${row.plan_title}`.toLowerCase().includes(query),
	)
})

// A cancelled order has no agreement or payments to open.
const hasDetails = (row) => row.status !== 'Cancelled'
</script>

<style scoped>
.contracts-table th {
	@apply p-2 bg-surface-gray-1 text-left font-normal;
}

.contracts-table td {
	@apply p-2 whitespace-nowrap;
}
</style>
