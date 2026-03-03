<template>
	<div class="p-5">
		<ObjectList :options="options" ref="mandateList" />

		<!-- Setup Autopay Dialog -->
		<Dialog
			v-model="showSetupDialog"
			:options="{
				title: 'Setup UPI Autopay',
				actions: [
					{
						label: 'Setup Autopay',
						variant: 'solid',
						loading: $resources.createRazorpayMandate.loading,
						onClick: () => setupAutopay(),
					},
				],
			}"
		>
			<template #body-content>
				<p class="mb-4 text-p-base text-gray-700">
					UPI Autopay allows automatic payments for your Frappe Cloud invoices.
					You'll authorize via Razorpay Checkout.
				</p>
				<FormControl
					label="Maximum Amount (INR)"
					type="number"
					v-model="maxAmount"
					:min="1000"
					:max="100000"
					placeholder="50000"
				/>
				<p class="mt-2 text-p-sm text-gray-600">
					This is the maximum amount that can be auto-debited per transaction.
					Recommended: Set higher than your typical monthly invoice.
				</p>
				<ErrorMessage
					class="mt-3"
					:message="$resources.createRazorpayMandate.error"
				/>
			</template>
		</Dialog>
	</div>
</template>

<script>
import { defineAsyncComponent, h } from 'vue';
import ObjectList from '../components/ObjectList.vue';
import {
	Badge,
	FeatherIcon,
	Dialog,
	FormControl,
	Button,
	ErrorMessage,
} from 'frappe-ui';
import { toast } from 'vue-sonner';
import { confirmDialog, icon } from '../utils/components';

export default {
	name: 'BillingUPIAutopay',
	components: {
		ObjectList,
		Dialog,
		FormControl,
		Button,
		FeatherIcon,
		ErrorMessage,
	},
	data() {
		return {
			showSetupDialog: false,
			maxAmount: 50000,
			pendingMandateName: '',
		};
	},
	mounted() {
		this.loadRazorpayScript();
	},
	resources: {
		createRazorpayMandate() {
			return {
				url: 'press.api.billing.create_razorpay_mandate',
				params: {
					max_amount: this.maxAmount,
					auth_type: 'upi',
				},
				onSuccess(data) {
					this.pendingMandateName = data.mandate_name;
					this.showSetupDialog = false;
					this.openRazorpayCheckout(data);
				},
				onError(error) {
					toast.error(error.messages?.[0] || 'Failed to create mandate');
				},
			};
		},
		handleMandateSuccess() {
			return {
				url: 'press.api.billing.handle_razorpay_mandate_success',
				onSuccess() {
					toast.success('UPI Autopay authorized successfully!');
					this.$refs.mandateList?.reload?.();
					this.$team.reload();
				},
				onError(error) {
					toast.error(error.messages?.[0] || 'Failed to verify authorization');
				},
			};
		},
		cancelMandate() {
			return {
				url: 'press.api.billing.cancel_razorpay_mandate',
				onSuccess() {
					toast.success('Mandate cancelled');
				},
				onError() {
					toast.error('Could not cancel mandate');
				},
			};
		},
	},
	computed: {
		options() {
			return {
				doctype: 'Razorpay Mandate',
				fields: [
					'name',
					'mandate_id',
					'status',
					'method',
					'auth_type',
					'max_amount',
					'expires_on',
					'is_default',
					'upi_vpa',
					'creation',
				],
				filterByTeam: true,
				emptyStateMessage: 'No UPI Autopay mandates set up.',
				columns: [
					{
						label: 'UPI ID',
						fieldname: 'upi_vpa',
						format(value) {
							return value || '-';
						},
					},
					{
						label: 'Status',
						fieldname: 'status',
						type: 'Component',
						component({ row }) {
							const statusColors = {
								Pending: 'orange',
								Active: 'green',
								Paused: 'yellow',
								Cancelled: 'red',
								Failed: 'red',
								Expired: 'gray',
							};
							return h(
								Badge,
								{ theme: statusColors[row.status] || 'gray' },
								() => row.status,
							);
						},
					},
					{
						label: 'Max Amount',
						fieldname: 'max_amount',
						format(value) {
							return `₹${value?.toLocaleString('en-IN') || 0}`;
						},
					},
					{
						label: 'Expires On',
						fieldname: 'expires_on',
						type: 'Date',
					},
					{
						label: '',
						fieldname: 'is_default',
						type: 'Component',
						component({ row }) {
							if (row.is_default) {
								return h(Badge, { theme: 'blue' }, () => 'Default');
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
										success: () => {
											this.$team.reload();
											return 'Default mandate set';
										},
										error: 'Could not set default mandate',
									},
								);
							},
							condition: () => !row.is_default && row.status === 'Active',
						},
						{
							label: 'Cancel',
							onClick: () => {
								confirmDialog({
									title: 'Cancel UPI Autopay',
									message:
										'Are you sure you want to cancel this UPI Autopay mandate?',
									onSuccess: ({ hide }) => {
										this.$resources.cancelMandate
											.submit({
												mandate_name: row.name,
											})
											.then(() => {
												listResource.reload();
												hide();
											});
									},
								});
							},
							condition: () =>
								row.status === 'Active' || row.status === 'Pending',
						},
					];
				},
				orderBy: 'creation desc',
				primaryAction: ({ listResource }) => {
					// Hide button if active mandate exists
					const hasActiveMandate = listResource.data?.some(
						(mandate) => mandate.status === 'Active',
					);
					if (hasActiveMandate) {
						return null;
					}
					return {
						label: 'Setup Autopay',
						slots: {
							prefix: icon('plus'),
						},
						onClick: () => {
							this.showSetupDialog = true;
						},
					};
				},
			};
		},
	},
	methods: {
		loadRazorpayScript() {
			if (window.Razorpay) return;
			const script = document.createElement('script');
			script.src = 'https://checkout.razorpay.com/v1/checkout.js';
			script.async = true;
			document.head.appendChild(script);
		},

		setupAutopay() {
			if (!this.maxAmount || this.maxAmount < 100) {
				toast.error('Maximum amount must be at least ₹100');
				return;
			}
			this.$resources.createRazorpayMandate.submit();
		},

		openRazorpayCheckout(orderData) {
			const options = {
				key: orderData.key_id,
				order_id: orderData.order_id,
				customer_id: orderData.customer_id,
				recurring: '1',
				name: 'Frappe Cloud',
				description: 'UPI Autopay Authorization',
				handler: (response) => {
					console.log('What response coming here:', response);
					this.handlePaymentSuccess(response);
				},
				modal: {
					ondismiss: () => {
						toast.info('Authorization cancelled');
					},
				},
				theme: {
					color: '#171717',
				},
			};

			const rzp = new window.Razorpay(options);
			rzp.on('payment.failed', (response) => {
				this.handlePaymentFailure(response);
			});
			rzp.open();
		},

		handlePaymentSuccess(response) {
			console.log('Log whats happening here:', response);
			this.$resources.handleMandateSuccess.submit({
				razorpay_payment_id: response.razorpay_payment_id,
				razorpay_order_id: response.razorpay_order_id,
				razorpay_signature: response.razorpay_signature,
				mandate_name: this.pendingMandateName,
			});
		},

		handlePaymentFailure(response) {
			const error = response.error;
			toast.error(error.description || 'Authorization failed');
		},
	},
};
</script>
