<template>
	<div class="space-y-4">
		<AlertBanner
			title="Save these recovery codes in a safe place. You can use them to
				reset two factor authentication if you lose access to your
				authenticator app."
			type="warning"
		/>

		<!-- Display recovery codes -->
		<ClickToCopy label="Copy Recovery Codes" :textContent="recoveryCodesStr" />

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
import ClickToCopy from '../../../components/ClickToCopyField.vue';

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
		ClickToCopy,
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
