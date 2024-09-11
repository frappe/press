<template>
	<div>
		<div
			class="mt-6 flex items-center justify-center"
			v-if="$resources.qrUrl.loading"
		>
			<LoadingText />
		</div>
		<div
			v-else-if="is2FAEnabled && $route.name !== 'Enable2FA'"
			class="space-y-4"
		>
			<AlertBanner
				title="Your account will be less secure if you disable 2FA"
				type="error"
			/>

			<!-- Steps for user to follow -->
			<div class="rounded border border-gray-200 bg-gray-50 p-4">
				<h3 class="text-lg font-semibold">Steps to Disable 2FA</h3>
				<ol class="mt-2 list-disc pl-2 text-sm">
					<li>Open the authenticator app</li>
					<li>Enter the code from the app below</li>
				</ol>
			</div>

			<FormControl
				label="Verify the code from the app to disable 2FA"
				v-model="totpCode"
			/>
		</div>

		<div v-else class="space-y-4">
			<div class="w-full">
				<VueQrcode
					v-if="qrUrl"
					class="mx-auto"
					:value="qrUrl"
					type="image/png"
					:color="{ dark: '#000000ff', light: '#ffffffff' }"
				/>
			</div>

			<!-- Steps for user to follow -->
			<div class="rounded border border-gray-200 bg-gray-50 p-4">
				<h3 class="text-lg font-semibold">Steps to Enable 2FA</h3>
				<ol class="ml-1 mt-2 list-disc pl-2 text-sm text-gray-700">
					<li>
						Download an authenticator app on your phone, such as
						<a
							class="underline"
							target="_blank"
							href="https://play.google.com/store/apps/details?id=com.google.android.apps.authenticator2"
						>
							Google Authenticator</a
						>
						or
						<a
							target="_blank"
							class="underline"
							href="https://github.com/beemdevelopment/Aegis"
						>
							Aegis</a
						>
						or use a browser extension like
						<a
							class="underline"
							target="_blank"
							href="https://support.1password.com/one-time-passwords/"
						>
							1Password</a
						>
					</li>
					<li>Scan the QR code</li>
					<li>
						Unable to scan? You can use the
						<span class="cursor-pointer underline" @click="showSetupKey = true">
							setup key</span
						>
						to manually configure your authenticator app
					</li>
					<li>Enter the code from the authenticator app below</li>
				</ol>
				<p class="mt-4 text-sm text-gray-700">
					<strong>Note:</strong> If you lose access to your authenticator app,
					your account will be locked out. Make sure to backup your vault/key.
				</p>
			</div>

			<div
				v-if="showSetupKey"
				class="rounded border border-gray-200 bg-gray-50 p-4"
			>
				<h3 class="text-lg font-semibold">Setup Key</h3>
				<p class="mt-2 text-sm">
					{{ setupKey }}
				</p>
			</div>

			<FormControl
				label="Verify the code from the app to enable 2FA"
				v-model="totpCode"
			/>
		</div>

		<div class="!mt-8 flex justify-center">
			<Button
				v-if="!is2FAEnabled"
				class="w-full"
				variant="solid"
				label="Enable 2FA"
				:disabled="!totpCode"
				:loading="$resources.enable2FA.loading"
				@click="enable2FA"
			/>
			<Button
				v-else
				class="w-full"
				variant="solid"
				label="Disable 2FA"
				:disabled="!totpCode"
				:loading="$resources.disable2FA.loading"
				@click="disable2FA"
			/>
		</div>
	</div>
</template>

<script>
import VueQrcode from 'vue-qrcode';
import { toast } from 'vue-sonner';
import AlertBanner from '../AlertBanner.vue';

export default {
	emits: ['enabled', 'disabled'],
	data() {
		return {
			qrUrl: '', // not storing as computed property to avoid re-fetching on dialog close
			totpCode: '',
			showSetupKey: false
		};
	},
	components: {
		AlertBanner,
		VueQrcode
	},
	methods: {
		enable2FA() {
			toast.promise(
				this.$resources.enable2FA.submit({
					totp_code: this.totpCode
				}),
				{
					loading: 'Enabling 2FA...',
					success: () => {
						this.totpCode = '';

						// avoid flickering of 2FA dialog
						setTimeout(() => {
							this.$team.reload();
						}, 500);
						this.$emit('enabled');

						return '2FA enabled successfully';
					},
					error(err) {
						if (err.messages) {
							if (err.messages.includes('Invalid TOTP code')) {
								return 'Invalid TOTP code. Please try again.';
							} else {
								return err.messages.join('.');
							}
						} else {
							return 'Failed to enable 2FA';
						}
					}
				}
			);
		},
		disable2FA() {
			toast.promise(
				this.$resources.disable2FA.submit({
					totp_code: this.totpCode
				}),
				{
					loading: 'Disabling 2FA...',
					success: () => {
						this.totpCode = '';

						// avoid flickering of 2FA dialog
						setTimeout(() => {
							this.$team.reload();
						}, 500);

						this.$emit('disabled');

						return '2FA disabled successfully';
					},
					error(err) {
						if (err.messages) {
							if (err.messages.includes('Invalid TOTP code')) {
								return 'Invalid TOTP code. Please try again.';
							} else {
								return err.messages.join('.');
							}
						} else {
							return 'Failed to disable 2FA';
						}
					}
				}
			);
		}
	},
	resources: {
		qrUrl() {
			return {
				url: 'press.api.account.get_2fa_qr_code_url',
				auto: true,
				onSuccess(qr_code_url) {
					this.qrUrl = qr_code_url;
				}
			};
		},
		enable2FA() {
			return {
				url: 'press.api.account.enable_2fa'
			};
		},
		disable2FA() {
			return {
				url: 'press.api.account.disable_2fa'
			};
		}
	},
	computed: {
		setupKey() {
			if (!this.qrUrl) return null;
			return this.qrUrl.match(/secret=(.*?)&issuer/)[1];
		},
		is2FAEnabled() {
			return this.$team.doc?.user_info?.is_2fa_enabled;
		}
	}
};
</script>
