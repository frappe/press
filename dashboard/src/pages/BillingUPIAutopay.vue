<template>
	<div class="p-5">
		<ObjectList :options="options" />

		<!-- Setup Autopay Dialog -->
		<Dialog
			v-model="showSetupDialog"
			:options="{
				title: 'Setup UPI Autopay',
				actions: [
					{
						label: 'Setup Autopay',
						variant: 'solid',
						loading: setupLoading,
						onClick: () => setupAutopay(),
					},
				],
			}"
		>
			<template #body-content>
				<p class="mb-4 text-p-base text-gray-700">
					UPI Autopay allows automatic payments for your Frappe Cloud invoices.
					You'll be redirected to authorize the mandate via your UPI app.
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
			</template>
		</Dialog>

		<!-- Authorization Link Dialog -->
		<Dialog
			v-model="showAuthDialog"
			:options="{
				title: 'Authorize UPI Autopay',
				actions: [
					{
						label: 'I have authorized',
						variant: 'solid',
						onClick: () => checkAuthStatus(),
					},
				],
			}"
		>
			<template #body-content>
				<div class="text-center">
					<p class="mb-4 text-p-base text-gray-700">
						Click the link below to authorize UPI Autopay in your UPI app.
					</p>
					<Button
						variant="solid"
						:link="authorizationLink"
						target="_blank"
						class="mb-4"
					>
						<template #prefix>
							<FeatherIcon name="external-link" class="h-4 w-4" />
						</template>
						Open Authorization Link
					</Button>
					<p class="text-p-sm text-gray-600">
						After authorizing in your UPI app, click "I have authorized" to
						refresh the status.
					</p>
				</div>
			</template>
		</Dialog>
	</div>
</template>

<script>
import { defineAsyncComponent, h } from 'vue';
import ObjectList from '../components/ObjectList.vue';
import { Badge, FeatherIcon, Dialog, FormControl, Button } from 'frappe-ui';
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
	},
	data() {
		return {
			showSetupDialog: false,
			showAuthDialog: false,
			maxAmount: 50000,
			setupLoading: false,
			authorizationLink: '',
			pendingMandateName: '',
		};
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
							label: 'Complete Authorization',
							onClick: () => {
								this.checkMandateStatus(row.name);
							},
							condition: () => row.status === 'Pending',
						},
						{
							label: 'Cancel',
							onClick: () => {
								confirmDialog({
									title: 'Cancel UPI Autopay',
									message:
										'Are you sure you want to cancel this UPI Autopay mandate?',
									onSuccess: ({ hide }) => {
										toast.promise(
											this.$call('press.api.billing.cancel_razorpay_mandate', {
												mandate_name: row.name,
											}).then(() => {
												listResource.reload();
												hide();
											}),
											{
												loading: 'Cancelling...',
												success: 'Mandate cancelled',
												error: 'Could not cancel mandate',
											},
										);
									},
								});
							},
							condition: () =>
								row.status === 'Active' || row.status === 'Pending',
						},
					];
				},
				orderBy: 'creation desc',
				primaryAction: () => {
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
		async setupAutopay() {
			if (!this.maxAmount || this.maxAmount < 100) {
				toast.error('Maximum amount must be at least ₹100');
				return;
			}

			this.setupLoading = true;
			try {
				const result = await this.$call(
					'press.api.billing.create_razorpay_mandate',
					{
						max_amount: this.maxAmount,
						auth_type: 'upi',
					},
				);

				this.showSetupDialog = false;
				this.authorizationLink = result.authorization_link;
				this.pendingMandateName = result.mandate_name;
				this.showAuthDialog = true;

				toast.success('Mandate created. Please authorize in your UPI app.');
			} catch (error) {
				toast.error(error.messages?.[0] || 'Failed to create mandate');
			} finally {
				this.setupLoading = false;
			}
		},

		async checkAuthStatus() {
			try {
				const mandates = await this.$call(
					'press.api.billing.get_razorpay_mandates',
				);
				const mandate = mandates.find(
					(m) => m.name === this.pendingMandateName,
				);

				if (mandate?.status === 'Active') {
					toast.success('UPI Autopay authorized successfully!');
					this.showAuthDialog = false;
					// Reload the list
					this.$refs?.list?.reload?.();
				} else if (mandate?.status === 'Pending') {
					toast.info('Authorization pending. Please complete in your UPI app.');
				} else {
					toast.error('Authorization failed or expired.');
					this.showAuthDialog = false;
				}
			} catch (error) {
				toast.error('Failed to check status');
			}
		},

		async checkMandateStatus(mandateName) {
			// For pending mandates, re-fetch and show auth dialog if needed
			try {
				const mandates = await this.$call(
					'press.api.billing.get_razorpay_mandates',
				);
				const mandate = mandates.find((m) => m.name === mandateName);

				if (mandate?.status === 'Active') {
					toast.success('Mandate is already active!');
				} else {
					toast.info('Please check your UPI app to complete authorization.');
				}
			} catch (error) {
				toast.error('Failed to check status');
			}
		},
	},
};
</script>
