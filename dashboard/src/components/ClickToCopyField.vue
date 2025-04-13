<template>
	<div class="relative rounded-lg border-2 border-gray-200 bg-gray-100 p-3">
		<div class="select-all break-all text-xs text-gray-800">
			<pre
				:class="{
					'whitespace-pre-wrap': breakLines,
					'overflow-x-auto': !breakLines
				}"
				:style="
					!breakLines
						? 'scrollbar-width: none; -ms-overflow-style: none; -webkit-scrollbar: none;'
						: ''
				"
				>{{ textContent }}</pre
			>
		</div>
		<button
			class="absolute right-2 top-2 rounded-sm border border-gray-200 bg-white p-1 text-xs text-gray-600"
			variant="outline"
			@click="copyTextContentToClipboard"
		>
			{{ copied ? 'copied' : 'copy' }}
		</button>
	</div>
</template>

<script>
import { toast } from 'vue-sonner';

export default {
	props: {
		textContent: {
			type: String,
			required: true
		},
		breakLines: {
			type: Boolean,
			default: true
		}
	},
	data() {
		return {
			copied: false
		};
	},
	methods: {
		copyTextContentToClipboard() {
			const clipboard = window.navigator.clipboard;
			clipboard.writeText(this.textContent).then(() => {
				this.copied = true;
				setTimeout(() => {
					this.copied = false;
				}, 4000);
				toast.success('Copied to clipboard!');
			});
		}
	}
};
</script>
