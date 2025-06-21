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
			label="Close"
			@click="() => $emit('close')"
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
	computed: {
		recoveryCodesStr() {
			return this.recoveryCodes.join('\n');
		},
	},
};
</script>
