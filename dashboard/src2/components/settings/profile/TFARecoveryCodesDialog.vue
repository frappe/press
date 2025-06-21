<template>
	<Dialog
		v-model="show"
		:options="{
			title: 'Two-Factor Authentication Recovery Codes',
		}"
		@close="closeDialog"
	>
		<template #body-content>
			<TFARecoveryCodes
				v-if="recoveryCodes.length"
				:recoveryCodes="recoveryCodes"
				@close="closeDialog"
				@reset="() => $resources.resetRecoveryCodes.submit()"
				with-reset
			/>
			<div v-else class="space-y-4">
				<FormControl
					label="Password"
					type="password"
					placeholder="•••••"
					v-model="password"
					name="password"
					autocomplete="current-password"
					required
				/>
				<ErrorMessage :message="$resources.getRecoveryCodes.error" />
				<Button
					label="Fetch Recovery Codes"
					class="w-full"
					variant="solid"
					@click="() => $resources.getRecoveryCodes.submit({ password })"
				/>
			</div>
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
			password: '',
			recoveryCodes: [],
		};
	},
	resources: {
		getRecoveryCodes() {
			return {
				url: 'press.api.account.get_2fa_recovery_codes',
				onSuccess(codes) {
					// Reset the password after fetching recovery codes.
					this.password = '';
					this.recoveryCodes = codes;
				},
			};
		},
		resetRecoveryCodes() {
			return {
				url: 'press.api.account.reset_2fa_recovery_codes',
				onSuccess(codes) {
					this.recoveryCodes = codes;
					this.$toast.success('Recovery codes have been reset.');
				},
			};
		},
	},
	methods: {
		closeDialog() {
			this.show = false;
			this.recoveryCodes = [];
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
