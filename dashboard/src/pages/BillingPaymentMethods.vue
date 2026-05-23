<template>
	<div class="p-5">
		<ObjectList v-if="$team?.doc?.payment_mode === 'Card'" :options="options" />

		<div
			v-if="$team?.doc?.currency === 'DZD'"
			class="mt-6 rounded-lg border border-gray-200 p-5"
		>
			<div class="flex items-center justify-between">
				<div class="flex flex-col gap-1.5">
					<div class="text-base font-medium text-ink-gray-9">
						Paiement Chargily (CIB / EDAHABIA)
					</div>
					<div class="text-sm text-ink-gray-7">
						Payez avec votre carte EDAHABIA ou CIB via Chargily Pay
					</div>
				</div>
				<Button
					label="Ajouter un paiement Chargily"
					@click="showChargilyDialog = true"
				>
					<template #prefix>
						<FeatherIcon class="h-4" name="plus" />
					</template>
				</Button>
			</div>
		</div>

		<AddPrepaidCreditsDialog
			v-if="showChargilyDialog"
			v-model="showChargilyDialog"
			@success="() => { showChargilyDialog = false; }"
		/>
	</div>
</template>
<script>
import { defineAsyncComponent, h, ref } from 'vue';
import ObjectList from '../components/ObjectList.vue';
import AddPrepaidCreditsDialog from '../components/billing/AddPrepaidCreditsDialog.vue';
import { Badge, Button, FeatherIcon, Tooltip } from 'frappe-ui';
import { toast } from 'vue-sonner';
import { confirmDialog, renderDialog, icon } from '../utils/components';
export default {
	name: 'BillingPaymentMethods',
	props: ['tab'],
	components: {
		ObjectList,
		AddPrepaidCreditsDialog,
		Button,
		FeatherIcon,
	},
	data() {
		return {
			showChargilyDialog: false,
		};
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
				emptyStateMessage: 'Aucune carte ajoutée.',
				columns: [
					{
						label: 'Nom sur la carte',
						fieldname: 'name_on_card',
					},
					{
						label: 'Carte',
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
									() => 'Par défaut',
								);
							}
						},
					},
					{
						label: 'Expiration',
						width: 0.5,
						format(value, row) {
							return `${row.expiry_month}/${row.expiry_year}`;
						},
					},
					{
						label: 'Mandaté',
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
										text: 'Le dernier paiement a échoué avec cette carte. Veuillez utiliser une autre carte.',
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
							label: 'Définir par défaut',
							onClick: () => {
								toast.promise(
									listResource.runDocMethod.submit({
										method: 'set_default',
										name: row.name,
									}),
									{
										loading: 'Définition par défaut...',
										success: 'Carte par défaut définie',
										error: 'Impossible de définir la carte par défaut',
									},
								);
							},
							condition: () => !row.is_default,
						},
						{
							label: 'Retirer',
							onClick: () => {
								if (row.is_default && this.$team.doc.payment_mode === 'Card') {
									toast.error('Impossible de retirer la carte par défaut');
									return;
								}
								confirmDialog({
									title: 'Retirer la carte',
									message: 'Êtes-vous sûr de vouloir retirer cette carte ?',
									onSuccess: ({ hide }) => {
										toast.promise(
											listResource.delete.submit(row.name, {
												onSuccess() {
													hide();
												},
											}),
											{
												loading: 'Suppression de la carte...',
												success: 'Carte retirée',
												error: (error) =>
													error.messages?.length
														? error.messages.join('\n')
														: error.message || 'Impossible de retirer la carte',
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
						label: 'Ajouter une carte',
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
