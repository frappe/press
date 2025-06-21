<template>
	<div class="space-y-4">
		<AlertBanner
			title="Save these recovery codes in a safe place. You can use them to
				reset two factor authentication if you lose access to your
				authenticator app."
			type="warning"
		/>

		<div class="rounded border border-gray-200 bg-gray-50 p-4">
			<div class="font-mono text-sm leading-loose text-gray-700">
				{{ recoveryCodesStr }}
			</div>
		</div>

		<!-- Reset button only shown if withReset prop is true -->
		<Button
			v-if="withReset"
			class="w-full"
			variant="subtle"
			label="Reset Recovery Codes"
			@click="() => $emit('reset')"
		/>
		<Button
			class="w-full"
			variant="solid"
			label="Download"
			@click="downloadCodes"
		/>
	</div>
</template>

<script>
import AlertBanner from '../../AlertBanner.vue';

export default {
	props: {
		recoveryCodes: {
			type: Array,
			required: true,
		},
		withReset: {
			type: Boolean,
			default: false,
		},
	},
	emits: ['close', 'reset'],
	components: {
		AlertBanner,
	},
	methods: {
		downloadCodes() {
			const blob = new Blob([this.recoveryCodesStr], {
				type: 'text/plain',
			});
			const url = URL.createObjectURL(blob);
			const a = document.createElement('a');
			a.href = url;
			a.download = 'recovery_codes.txt';
			document.body.appendChild(a);
			a.click();
			document.body.removeChild(a);
			URL.revokeObjectURL(url);
		},
	},
	computed: {
		recoveryCodesStr() {
			return this.recoveryCodes.join('\n');
		},
	},
};
</script>
