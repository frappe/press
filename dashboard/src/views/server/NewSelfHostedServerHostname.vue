<template>
	<div>
		<label class="text-lg font-semibold">
			Choose a name for your Self Hosted server
		</label>
		<p class="my-3 text-base text-gray-700">
			Name your server based on its purpose
		</p>
		<div class="space-y-2">
			<FormControl
				class="z-10 w-full rounded-r-none"
				:value="title"
				@change="titleChange"
				placeholder="AcmeCorp Production Server"
			/>
		</div>
		<ErrorMessage class="mt-4" :message="errorMessage" />
	</div>
</template>
<script>
export default {
	name: 'SelfHostedHostname',
	props: ['title'],
	emits: ['update:title', 'error'],
	data() {
		return {
			errorMessage: null
		};
	},
	methods: {
		async titleChange(e) {
			let title = e.target.value;
			this.$emit('update:title', title);
			let error = this.validateTitle(title);
			this.errorMessage = error;
			this.$emit('error', error);
		},
		validateTitle(title) {
			if (!title) {
				return 'Server name cannot be left blank';
			}
			return null;
		}
	}
};
</script>
