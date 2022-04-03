<template>
	<teleport to="#modals">
		<div
			v-show="show"
			class="fixed inset-0 flex items-center justify-center px-4 py-4"
		>
			<div
				v-show="show"
				class="fixed inset-0 transition-opacity"
				@click="onBackdropClick"
			>
				<div class="absolute inset-0 bg-gray-900 opacity-75"></div>
			</div>

			<div
				v-show="show"
				class="w-full transform overflow-auto rounded-lg bg-white shadow-xl transition-all"
				:class="widthClasses"
				style="max-height: 95vh"
			>
				<slot></slot>
			</div>
		</div>
	</teleport>
</template>

<script>
export default {
	name: 'Modal',
	emits: ['update:show'],
	props: {
		show: {
			type: Boolean,
			default: false
		},
		dismissable: {
			type: Boolean,
			default: true
		},
		width: {
			default: 'auto'
		}
	},
	created() {
		if (!this.dismissable) return;
		this.escapeListener = e => {
			if (e.key === 'Escape') {
				this.hide();
			}
		};
		document.addEventListener('keydown', this.escapeListener);
	},
	unmounted() {
		document.removeEventListener('keydown', this.escapeListener);
	},
	methods: {
		onBackdropClick() {
			if (!this.dismissable) return;
			this.hide();
		},
		hide() {
			this.$emit('update:show', false);
		}
	},
	computed: {
		widthClasses() {
			if (this.width === 'auto') {
				return ['sm:max-w-lg'];
			} else if (this.width === 'half') {
				return ['sm:max-w-2xl'];
			} else {
				return [];
			}
		}
	}
};
</script>
