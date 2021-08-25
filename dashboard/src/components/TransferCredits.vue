<template>
	<div>
		<Input
			v-if="availablePartnerCredits"
			:label="
				`Amount to Transfer (Credits available: ${availablePartnerCredits.formatted})`
			"
			v-model.number="creditsToTransfer"
			name="amount"
			autocomplete="off"
			type="number"
			min="1"
			:max="availablePartnerCredits.value"
		/>
		<div v-else class="flex justify-center mt-8">
			<Spinner class="w-4 h-4 text-gray-600" />
		</div>
		<ErrorMessage
			class="mt-2"
			:error="$resources.transferPartnerCredits.error"
		/>
		<div class="flex justify-end mt-2">
			<Button @click="$emit('cancel')">
				Cancel
			</Button>
			<Button
				class="ml-2"
				type="primary"
				@click="$resources.transferPartnerCredits.submit()"
				:loading="$resources.transferPartnerCredits.loading"
			>
				Transfer
			</Button>
		</div>
	</div>
</template>
<script>
export default {
	name: 'TransferCreditsDialog',
	props: ['show', 'minimumAmount'],
	data() {
		return {
			creditsToTransfer: this.minimumAmount || null
		};
	},
	resources: {
		availablePartnerCredits: 'press.api.billing.get_available_partner_credits',
		transferPartnerCredits() {
			return {
				method: 'press.api.billing.transfer_partner_credits',
				params: {
					amount: this.creditsToTransfer
				},
				onSuccess() {
					this.creditsToTransfer = null;
					this.$emit('success');
				},
				validate() {
					if (this.creditsToTransfer < 0) {
						return 'Amount must be greater than 0';
					}
					if (
						this.minimumAmount &&
						this.creditsToTransfer < this.minimumAmount
					) {
						return `You must transfer a minimum amount of ${this.minimumAmount}`;
					}
				}
			};
		}
	},
	computed: {
		availablePartnerCredits() {
			return this.$resources.availablePartnerCredits.data;
		}
	}
};
</script>
