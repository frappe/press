<template>
	<portal to="modals">
		<div
			v-show="open"
			class="fixed bottom-0 inset-x-0 px-4 pb-4 sm:inset-0 sm:flex sm:items-center sm:justify-center"
		>
			<div
				v-show="open"
				class="fixed inset-0 transition-opacity"
				@click="open = false"
			>
				<div class="absolute inset-0 bg-gray-900 opacity-75"></div>
			</div>

			<div
				v-show="open"
				class="bg-white rounded-lg overflow-hidden shadow-xl transform transition-all sm:max-w-lg sm:w-full"
			>
				<slot></slot>
			</div>
		</div>
	</portal>
</template>

<script>
export default {
	name: 'Modal',
	props: {
		show: {
			type: Boolean,
			default: false
		}
	},
	watch: {
		show: {
			immediate: true,
			handler(value) {
				this.open = value;
			}
		},
		open(value) {
			if (value === false) {
				this.$emit('hide');
			}
		}
	},
	created() {
		this.escapeListener = e => {
			if (e.key === 'Escape') {
				this.open = false;
			}
		};
		document.addEventListener('keydown', this.escapeListener);
	},
	destroyed() {
		document.removeEventListener('keydown', this.escapeListener);
	},
	data() {
		return {
			open: false
		};
	}
};
</script>
