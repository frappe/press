<template>
	<div
		class="flex flex-row items-center justify-between rounded-lg border-2 p-2"
	>
		<p class="overflow-hidden font-mono text-sm text-gray-800">
			{{ textContent }}
		</p>
		<Button icon="copy" @click="copyTextContentToClipboard" />
	</div>
</template>

<script>
export default {
	props: ['textContent'],
	methods: {
		copyTextContentToClipboard() {
			const clipboard = window.navigator.clipboard;
			clipboard.writeText(this.textContent).then(() => {
				this.$notify({
					title: 'Copied to clipboard!',
					icon: 'check',
					color: 'green'
				});
			});
		}
	}
};
</script>
