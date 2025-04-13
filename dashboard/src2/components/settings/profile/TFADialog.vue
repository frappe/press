<template>
	<Dialog
		v-model="show"
		:options="{
			title: is2FAEnabled
				? 'Disable Two-Factor Authentication'
				: 'Enable Two-Factor Authentication'
		}"
	>
		<template #body-content>
			<Configure2FA @enabled="closeDialog" @disabled="closeDialog" />
		</template>
	</Dialog>
</template>

<script>
import Configure2FA from '../../auth/Configure2FA.vue';

export default {
	props: {
		modelValue: {
			type: Boolean,
			required: true
		}
	},
	components: {
		Configure2FA
	},
	methods: {
		closeDialog() {
			this.show = false;
		}
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
			}
		}
	}
};
</script>
