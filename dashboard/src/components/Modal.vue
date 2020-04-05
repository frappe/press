<template>
	<portal to="modals">
		<div
			v-show="show"
			class="fixed inset-x-0 bottom-0 px-4 pb-4 sm:inset-0 sm:flex sm:items-center sm:justify-center"
		>
			<div v-show="show" class="fixed inset-0 transition-opacity" @click="hide">
				<div class="absolute inset-0 bg-gray-900 opacity-75"></div>
			</div>

			<div
				v-show="show"
				class="overflow-hidden transition-all transform bg-white rounded-lg shadow-xl sm:max-w-lg sm:w-full"
			>
				<slot></slot>
			</div>
		</div>
	</portal>
</template>

<script>
export default {
	name: 'Modal',
	model: {
		prop: 'show',
		event: 'change'
	},
	props: {
		show: {
			type: Boolean,
			default: false
		}
	},
	created() {
		this.escapeListener = e => {
			if (e.key === 'Escape') {
				this.hide();
			}
		};
		document.addEventListener('keydown', this.escapeListener);
	},
	destroyed() {
		document.removeEventListener('keydown', this.escapeListener);
	},
	methods: {
		hide() {
			this.$emit('change', false);
		}
	}
};
</script>
