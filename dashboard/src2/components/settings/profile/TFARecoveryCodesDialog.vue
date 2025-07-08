<template>
	<Dialog
		v-model="show"
		:options="{
			title: 'Authenticate to view 2FA recovery codes',
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
			<div class="space-y-4" v-else>
				<FormControl
					label="Email"
					type="email"
					:modelValue="$team.doc.user"
					name="email"
					disabled
				/>
				<FormControl
					v-if="isOTPSent"
					label="Verification Code"
					type="text"
					placeholder="123456"
					v-model="verificationCode"
					name="verificationCode"
					autocomplete="one-time-code"
					required
				/>
				<ErrorMessage
					class="mt-2"
					:message="$resources.getRecoveryCodes.error"
				/>
			</div>
		</template>
		<template v-if="!recoveryCodes.length" #actions>
			<Button
				v-if="!isOTPSent"
				label="Send verification code"
				class="w-full"
				variant="solid"
				@click="
					$resources.sendOTP.submit({
						email: $team.doc.user,
						for_2fa_keys: true,
					})
				"
				:loading="$resources.sendOTP.loading"
			/>
			<div v-else>
				<Button
					label="Fetch Recovery Codes"
					class="w-full"
					variant="solid"
					:loading="$resources.getRecoveryCodes.loading"
					@click="
						() =>
							$resources.getRecoveryCodes.submit({
								verification_code: verificationCode,
							})
					"
				/>
			</div>
		</template>
	</Dialog>
</template>

<script>
import TFARecoveryCodes from './TFARecoveryCodes.vue';
import { toast } from 'vue-sonner';

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
			verificationCode: '',
			isOTPSent: false,
		};
	},
	resources: {
		sendOTP() {
			return {
				url: 'press.api.account.send_otp',
				onSuccess() {
					this.isOTPSent = true;
					toast.success('Verification code sent to your email.');
				},
				onError(error) {
					toast.error(error.message || 'Failed to send verification code.');
				},
			};
		},
		getRecoveryCodes() {
			return {
				url: 'press.api.account.get_2fa_recovery_codes',
				onSuccess(codes) {
					this.recoveryCodes = codes;
				},
			};
		},
		resetRecoveryCodes() {
			return {
				url: 'press.api.account.reset_2fa_recovery_codes',
				onSuccess(codes) {
					this.recoveryCodes = codes;
					toast.success('Recovery codes have been reset.');
				},
			};
		},
	},
	methods: {
		closeDialog() {
			this.show = false;
			this.recoveryCodes = [];
			this.verificationCode = '';
			this.isOTPSent = false;
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
