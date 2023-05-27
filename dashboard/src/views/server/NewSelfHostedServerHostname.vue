<template>
	<div>
		<label class="text-lg font-semibold">
			Choose a name for your Self Hosted server
		</label>
		<p class="text-base text-gray-700">
			Name your server based on its purpose. For e.g., Personal Websites,
			Staging Server, etc.
		</p>
		<div class="mt-4 flex">
			<input
				class="form-input z-10 w-full rounded-r-none"
				type="text"
				:value="title"
				@change="titleChange"
				placeholder="Server"
			/>
		</div>
		<div class="mt-4">
			<ErrorMessage :message="errorMessage" />
		</div>
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
