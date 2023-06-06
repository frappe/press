<template>
	<div>
		<label class="text-lg font-semibold">
			Choose a name for your Self Hosted server
		</label>
		<p class="text-base text-gray-700 mt-3">
			Name your server based on its purpose
		</p>
		<div class="space-y-2">
			<Input class="z-10 w-full rounded-r-none" type="text" :value="title" @change="titleChange"
				placeholder="ABC-Prod 1" />
		</div>
		<div class="mt-6 space-y-2">
			<h2 class="text-lg font-semibold">Add Domain</h2>

			<p class="text-base text-gray-700">
				Add Domain pointing to Server
			</p>
			<Input class="z-10 w-full rounded-r-none" type="text" :value="domain" @change="$emit('update:domain', $event)"
				placeholder="abc.example.com" />
		</div>
		<ErrorMessage class="mt-4" :message="errorMessage" />
	</div>
</template>
<script>
export default {
	name: 'SelfHostedHostname',
	props: ['title', 'domain'],
	emits: ['update:title', 'update:domain', 'error'],
	data() {
		return {
			errorMessage: null
		};
	},
	methods: {
		async titleChange(e) {
			let title = e;
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
