<template>
	<div class="relative rounded-lg border-2 p-2">
		<p class="select-all break-all font-mono text-sm text-gray-800">
			{{ textContent }}
		</p>
		<Button
			class="absolute right-1 top-[1.5px] p-3"
			icon="copy"
			@click="copyTextContentToClipboard"
		/>
	</div>
</template>

<script>
import { notify } from '@/utils/toast';

export default {
	props: ['textContent'],
	methods: {
		copyTextContentToClipboard() {
			const clipboard = window.navigator.clipboard;
			clipboard.writeText(this.textContent).then(() => {
				notify({
					title: 'Copied to clipboard!',
					icon: 'check',
					color: 'green'
				});
			});
		}
	}
};
</script>
