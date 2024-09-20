<template>
	<Dialog :options="{ title: title }" v-model="showDialog">
		<template v-slot:body-content>
			<BuyPrepaidCreditsForm
				@success="onSuccess"
				:minimumAmount="minimumAmount"
				:modelValue="modelValue"
			/>
		</template>
	</Dialog>
</template>
<script>
import BuyPrepaidCreditsForm from './BuyPrepaidCreditsForm.vue';

export default {
	name: 'BuyPrepaidCreditsDialog',
	components: {
		BuyPrepaidCreditsForm
	},
	props: {
		minimumAmount: {
			type: Number,
			default: 0
		},
		title: {
			type: String,
			default: 'Add credits to your account'
		}
	},
	emits: ['update:modelValue', 'success'],
	methods: {
		onSuccess() {
			this.$emit('success');
		},
		onCancel() {
			this.showDialog = false;
		}
	},
	computed: {
		totalAmount() {
			let creditsToBuy = this.creditsToBuy || 0;
			if (this.$team.doc.currency === 'INR') {
				return (
					creditsToBuy +
					creditsToBuy * (this.$team.doc.billing_info.gst_percentage || 0)
				).toFixed(2);
			} else {
				return creditsToBuy;
			}
		},
		showDialog: {
			get() {
				return this.modelValue;
			},
			set(value) {
				this.$emit('update:modelValue', value);
			}
		}
	}
};
</script>
