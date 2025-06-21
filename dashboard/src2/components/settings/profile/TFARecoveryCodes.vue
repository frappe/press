<template>
	<div class="space-y-4">
		<AlertBanner
			title="Save these recovery codes in a safe place. You can use them to
				reset two factor authentication if you lose access to your
				authenticator app."
			type="warning"
		/>

		<div class="rounded border border-gray-200 bg-gray-50 p-4">
			<div class="text-sm text-gray-700">
				{{ recoveryCodesStr }}
			</div>
		</div>

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
	},
	emits: ['close'],
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
