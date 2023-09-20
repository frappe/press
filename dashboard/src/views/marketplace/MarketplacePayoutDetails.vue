<script setup>
import { createResource } from 'frappe-ui';

const props = defineProps({
	payoutOrderName: {
		type: String,
		required: true
	}
});

const payout = createResource({
	url: 'press.api.marketplace.get_payout_details',
	auto: true,
	params: {
		name: props.payoutOrderName
	}
});
</script>
<template>
	<div>
		<Button v-if="payout.loading" :loading="true">Loading</Button>

		<div v-if="payout.data">
			<table class="text w-full text-sm">
				<thead>
					<tr class="text-gray-600">
						<th class="border-b py-3 pr-2 text-left font-normal">
							Description
						</th>
						<th
							class="whitespace-nowrap border-b py-3 pr-2 text-right font-normal"
						>
							Rate
						</th>
						<th
							class="whitespace-nowrap border-b py-3 pr-2 text-right font-normal"
						>
							Total Amount
						</th>
						<th
							class="whitespace-nowrap border-b py-3 pr-2 text-right font-normal"
						>
							Fee
						</th>
						<th
							class="whitespace-nowrap border-b py-3 pr-2 text-right font-normal"
						>
							Commission
						</th>
						<th class="border-b py-3 pr-2 text-right font-normal">
							Net Amount
						</th>
					</tr>
				</thead>

				<tbody>
					<tr v-for="(row, i) in payout.data.usd_items" :key="row.idx">
						<td class="border-b py-3 pr-2">
							{{ row.description || row.document_name }} -
							<strong class="font-semibold">{{ row.site }}</strong>
						</td>
						<td class="border-b py-3 pr-2 text-right">
							${{ row.rate }} x {{ row.quantity }}
						</td>
						<td class="border-b py-3 pr-2 text-right">
							${{ row.total_amount }}
						</td>
						<td class="border-b py-3 pr-2 text-right">
							${{ round(row.gateway_fee, 2) }}
						</td>
						<td class="border-b py-3 pr-2 text-right">
							${{ round(row.commission, 2) }}
						</td>
						<td class="border-b py-3 pr-2 text-right">
							${{ round(row.net_amount, 2) }}
						</td>
					</tr>
				</tbody>

				<tfoot>
					<tr>
						<td></td>
						<td></td>
						<td></td>
						<td class="pt-4 pb-2 pr-2 text-right font-semibold">Grand Total</td>
						<td
							class="whitespace-nowrap pt-4 pb-2 pr-2 text-right font-semibold"
						>
							${{ round(payout.data.net_total_usd, 2) }} + ₹{{
								round(payout.data.net_total_inr, 2)
							}}
						</td>
					</tr>
				</tfoot>

				<tbody>
					<tr v-for="(row, i) in payout.data.inr_items" :key="row.idx">
						<td class="border-b py-3 pr-2">
							{{ row.description || row.document_name }} -
							<strong class="font-semibold">{{ row.site }}</strong>
						</td>
						<td class="border-b py-3 pr-2 text-right">
							₹{{ row.rate }} x {{ row.quantity }}
						</td>
						<td class="border-b py-3 pr-2 text-right">
							₹{{ round(row.total_amount, 2) }}
						</td>
						<td class="border-b py-3 pr-2 text-right">
							₹{{ round(row.gateway_fee, 2) }}
						</td>
						<td class="border-b py-3 pr-2 text-right">
							₹{{ round(row.commission, 2) }}
						</td>
						<td class="border-b py-3 pr-2 text-right">
							₹{{ round(row.net_amount, 2) }}
						</td>
					</tr>
				</tbody>
			</table>
		</div>

		<ErrorMessage :message="payout.error" />
	</div>
</template>
