<template>
	<Dialog
		v-model="show"
		:options="{
			title: 'Two-Factor Authentication Recovery Codes',
		}"
	>
		<template #body-content>
			<TFARecoveryCodes :recoveryCodes="recoveryCodes" @close="closeDialog" />
		</template>
	</Dialog>
</template>

<script>
import TFARecoveryCodes from './TFARecoveryCodes.vue';

export default {
	props: {
		modelValue: {
			type: Boolean,
			required: true,
		},
	},
	components: {
		TFARecoveryCodes,
	},
	data() {
		return {
			recoveryCodes: [],
		};
	},
	resources: {
		getRecoveryCodes() {
			return {
				url: 'press.api.account.get_2fa_recovery_codes',
				auto: true,
				onSuccess(codes) {
					this.recoveryCodes = codes;
				},
			};
		},
	},
	methods: {
		closeDialog() {
			this.show = false;
		},
	},
	computed: {
		show: {
			get() {
				return this.modelValue;
			},
			set(value) {
				this.$emit('update:modelValue', value);
			},
		},
	},
};
</script>
