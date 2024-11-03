<template>
	<Dialog
		:options="{ title: `Finalize Unsettled Invoices` }"
		v-model="showDialog"
	>
		<template #body-content>
			<div class="prose text-base">
				You have unpaid invoices on your account for the following periods:
				<ul class="pt-2">
					<li
						class="font-semibold"
						v-for="invoice in $resources.unpaidInvoices.data"
					>
						{{
							date(invoice.period_end).toLocaleString({
								month: 'long',
								year: 'numeric'
							})
						}}
						-
						{{
							(invoice.currency === 'INR' ? '₹ ' : '$ ') + invoice.amount_due
						}}
					</li>
				</ul>
				Please finalize and settle them before removing all payment methods or
				disabling the account. You can check the details of invoices and make
				the payment from
				<Link to="/billing/invoices/">here</Link>. It might take up to 2 hours
				for the payment to reflect against your invoices.
			</div>
		</template>
		<template #actions>
			<Button
				variant="solid"
				class="w-full"
				@click="$resources.finalizeInvoices.submit()"
			>
				Finalize Invoices
			</Button>
		</template>
	</Dialog>
</template>

<script>
import { date } from '../../utils/format';
import { toast } from 'vue-sonner';

export default {
	name: 'FinalizeInvoicesDialog',
	props: {
		msg: String
	},
	data() {
		return {
			showDialog: true
		};
	},
	resources: {
		finalizeInvoices: {
			url: 'press.api.billing.finalize_invoices',
			onSuccess() {
				this.showDialog = false;
				toast.success('Invoices finalized successfully');
			}
		},
		unpaidInvoices: {
			url: 'press.api.billing.unpaid_invoices',
			auto: true
		}
	},
	methods: {
		date
	}
};
</script>
