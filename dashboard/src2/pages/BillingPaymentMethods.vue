<template>
	<div class="p-5">
		<ObjectList :options="options" />
	</div>
</template>
<script>
import { defineAsyncComponent, h } from 'vue';
import ObjectList from '../components/ObjectList.vue';
import { Badge, FeatherIcon, Tooltip } from 'frappe-ui';
import { toast } from 'vue-sonner';
import { confirmDialog, renderDialog, icon } from '../utils/components';
export default {
	name: 'BillingPaymentMethods',
	props: ['tab'],
	components: {
		ObjectList,
	},
	computed: {
		options() {
			return {
				doctype: 'Stripe Payment Method',
				fields: [
					'name',
					'is_default',
					'expiry_month',
					'expiry_year',
					'brand',
					'stripe_mandate_id',
				],
				emptyStateMessage: 'No cards added.',
				columns: [
					{
						label: 'Name on Card',
						fieldname: 'name_on_card',
					},
					{
						label: 'Card',
						fieldname: 'last_4',
						width: 1.5,
						format(value) {
							return `•••• ${value}`;
						},
						prefix: (row) => {
							return this.cardBrandIcon(row.brand);
						},
						suffix(row) {
							if (row.is_default) {
								return h(
									Badge,
									{
										theme: 'green',
									},
									() => 'Default',
								);
							}
						},
					},
					{
						label: 'Expiry',
						width: 0.5,
						format(value, row) {
							return `${row.expiry_month}/${row.expiry_year}`;
						},
					},
					{
						label: 'Mandated',
						type: 'Component',
						width: 1,
						align: 'center',
						component({ row }) {
							if (row.stripe_mandate_id) {
								return h(FeatherIcon, {
									name: 'check-circle',
									class: 'h-4 w-4 text-green-600',
								});
							}
						},
					},
					{
						label: '',
						type: 'Component',
						align: 'right',
						component({ row }) {
							if (row.is_default && row.stripe_payment_method) {
								return h(
									Tooltip,
									{
										text: 'The last payment failed on this card. Please use a different card.',
									},
									() =>
										h(FeatherIcon, {
											name: 'alert-circle',
											class: 'h-4 w-4 text-red-600',
										}),
								);
							}
						},
					},
					{
						label: '',
						fieldname: 'creation',
						type: 'Timestamp',
						align: 'right',
					},
				],
				rowActions: ({ listResource, row }) => {
					return [
						{
							label: 'Set as default',
							onClick: () => {
								toast.promise(
									listResource.runDocMethod.submit({
										method: 'set_default',
										name: row.name,
									}),
									{
										loading: 'Setting as default...',
										success: 'Default card set',
										error: 'Could not set default card',
									},
								);
							},
							condition: () => !row.is_default,
						},
						{
							label: 'Remove',
							onClick: () => {
								if (row.is_default && this.$team.doc.payment_mode === 'Card') {
									toast.error('Cannot remove default card');
									return;
								}
								confirmDialog({
									title: 'Remove Card',
									message: 'Are you sure you want to remove this card?',
									onSuccess: ({ hide }) => {
										toast.promise(
											listResource.delete.submit(row.name, {
												onSuccess() {
													hide();
												},
											}),
											{
												loading: 'Removing card...',
												success: 'Card removed',
												error: (error) =>
													error.messages?.length
														? error.messages.join('\n')
														: error.message || 'Could not remove card',
											},
										);
									},
								});
							},
						},
					];
				},
				orderBy: 'creation desc',
				primaryAction() {
					return {
						label: 'Add Card',
						slots: {
							prefix: icon('plus'),
						},
						onClick: () => {
							let StripeCardDialog = defineAsyncComponent(
								() => import('../components/StripeCardDialog.vue'),
							);
							renderDialog(StripeCardDialog);
						},
					};
				},
			};
		},
	},
	methods: {
		formatCurrency(value) {
			if (value === 0) {
				return '';
			}
			return this.$format.userCurrency(value);
		},
		cardBrandIcon(brand) {
			let component = {
				'master-card': defineAsyncComponent(
					() => import('@/components/icons/cards/MasterCard.vue'),
				),
				visa: defineAsyncComponent(
					() => import('@/components/icons/cards/Visa.vue'),
				),
				amex: defineAsyncComponent(
					() => import('@/components/icons/cards/Amex.vue'),
				),
				jcb: defineAsyncComponent(
					() => import('@/components/icons/cards/JCB.vue'),
				),
				generic: defineAsyncComponent(
					() => import('@/components/icons/cards/Generic.vue'),
				),
				'union-pay': defineAsyncComponent(
					() => import('@/components/icons/cards/UnionPay.vue'),
				),
			}[brand || 'generic'];
			return h(component, { class: 'h-4 w-6' });
		},
	},
};
</script>
