<template>
	<div
		class="p-2 items-center rounded-lg flex flex-row border-2 justify-between"
	>
		<p class="text-sm text-gray-800 font-mono overflow-hidden">
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
