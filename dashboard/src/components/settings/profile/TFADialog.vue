<template>
	<Dialog
		v-model="show"
		:options="{
			title,
		}"
		@close="closeDialog"
	>
		<template #body-content>
			<TFARecoveryCodes
				v-if="is2FAEnabled && recoveryCodes.length"
				:recoveryCodes="recoveryCodes"
			/>
			<Configure2FA
				v-else
				@enabled="closeDialog"
				@disabled="closeDialog"
				@update-recovery-codes="(codes) => (recoveryCodes = codes)"
			/>
		</template>
	</Dialog>
</template>

<script>
import Configure2FA from '../../auth/Configure2FA.vue';
import TFARecoveryCodes from './TFARecoveryCodes.vue';

export default {
	props: {
		modelValue: {
			type: Boolean,
			required: true,
		},
	},
	components: {
		Configure2FA,
		TFARecoveryCodes,
	},
	data() {
		return {
			recoveryCodes: [],
		};
	},
	methods: {
		closeDialog() {
			this.show = false;
			this.recoveryCodes = [];
		},
	},
	computed: {
		is2FAEnabled() {
			return this.$team.doc?.user_info?.is_2fa_enabled;
		},
		show: {
			get() {
				return this.modelValue;
			},
			set(value) {
				this.$emit('update:modelValue', value);
			},
		},
		title() {
			if (this.is2FAEnabled && this.recoveryCodes.length) {
				return 'Two-Factor Authentication Recovery Codes';
			} else if (this.is2FAEnabled) {
				return 'Disable Two-Factor Authentication';
			} else {
				return 'Enable Two-Factor Authentication';
			}
		},
	},
};
</script>
