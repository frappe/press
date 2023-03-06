<template>
	<div>
		<Card
			v-if="profileData && profileData.profile_created"
			title="Payout Preferences"
			subtitle="Used for payouts for your premium apps"
		>
			<div class="divide-y-2">
				<ListItem
					title="Payout Method"
					:description="payoutMethod || 'Not Set'"
				/>

				<ListItem
					v-if="payoutMethod == 'PayPal'"
					title="PayPal ID"
					:description="payPalId || 'Not Set'"
				/>

				<ListItem
					v-if="payoutMethod == 'Bank Transfer'"
					title="Account Holder Name"
					:description="acName || 'Not Set'"
				/>

				<ListItem
					v-if="payoutMethod == 'Bank Transfer'"
					title="Account Number"
					:description="acNumber || 'Not Set'"
				/>
			</div>

			<template #actions>
				<Button icon-left="edit" @click="showEditProfileDialog = true"
					>Edit</Button
				>
			</template>
		</Card>

		<Dialog
			:options="{ title: 'Edit Publisher Profile' }"
			v-model="showEditProfileDialog"
		>
			<template v-slot:body-content>
				<div class="grid grid-cols-1 gap-4 sm:grid-cols-2">
					<Input
						label="Preferred Payment Method"
						type="select"
						:options="['Frappe Cloud Credits', 'Bank Transfer', 'PayPal']"
						v-model="payoutMethod"
					/>

					<Input
						v-if="payoutMethod == 'PayPal'"
						label="PayPal ID"
						type="text"
						v-model="payPalId"
					/>

					<Input
						label="GSTIN (if applicable)"
						v-if="payoutMethod != 'Frappe Cloud Credits'"
						type="text"
						v-model="gstin"
					/>

					<Input
						v-if="payoutMethod == 'Bank Transfer'"
						label="Account Number"
						type="text"
						v-model="acNumber"
					/>

					<Input
						v-if="payoutMethod == 'Bank Transfer'"
						label="Account Holder Name"
						type="text"
						v-model="acName"
					/>

					<Input
						label="Bank Name, Branch, IFS Code"
						v-if="payoutMethod == 'Bank Transfer'"
						type="textarea"
						v-model="otherDetails"
					/>
				</div>

				<ErrorMessage
					class="mt-4"
					:error="$resources.updatePublisherProfile.error"
				/>
			</template>

			<template #actions>
				<div class="space-x-2">
					<Button @click="showEditProfileDialog = false">Cancel</Button>
					<Button
						appearance="primary"
						:loading="$resources.updatePublisherProfile.loading"
						loadingText="Saving..."
						@click="$resources.updatePublisherProfile.submit()"
					>
						Save
					</Button>
				</div>
			</template>
		</Dialog>
	</div>
</template>

<script>
export default {
	props: ['profileData'],
	emits: ['profileUpdated'],
	data() {
		return {
			showEditProfileDialog: false,
			payoutMethod: '',
			payPalId: '',
			acNumber: '',
			acName: '',
			gstin: '',
			otherDetails: ''
		};
	},
	mounted() {},
	resources: {
		updatePublisherProfile() {
			return {
				method: 'press.api.marketplace.update_publisher_profile',
				params: {
					profile_data: {
						preferred_payout_method: this.payoutMethod,
						paypal_id: this.payPalId,
						bank_account_number: this.acNumber,
						bank_account_holder_name: this.acName,
						gstin: this.gstin,
						other_bank_details: this.otherDetails
					}
				},
				onSuccess() {
					this.showEditProfileDialog = false;
					this.$emit('profileUpdated');
				}
			};
		}
	},
	watch: {
		profileData(data) {
			if (data && data.profile_created) {
				this.payoutMethod = data.profile_info.preferred_payout_method;
				this.payPalId = data.profile_info.paypal_id;
				this.acNumber = data.profile_info.bank_account_number;
				this.acName = data.profile_info.bank_account_holder_name;
				this.gstin = data.profile_info.gstin;
				this.otherDetails = data.profile_info.other_bank_details;
			}
		}
	}
};
</script>
