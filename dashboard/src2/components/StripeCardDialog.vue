<template>
	<Dialog v-model="show" :options="{ title: 'Add new card' }">
		<template #body-content>
			<p class="text-sm mb-5 text-gray-700" v-if="message">
				{{ message }}
			</p>
			<CardForm @success="show = false" />
		</template>
	</Dialog>
</template>
<script>
import CardForm from './billing/CardForm.vue';
export default {
	name: 'StripeCardDialog',
	props: ['modelValue', 'message'],
	emits: ['update:modelValue'],
	components: {
		CardForm,
	},
	data() {
		return {
			_show: true,
		};
	},
	computed: {
		show: {
			get() {
				return this.modelValue == null ? this._show : this.modelValue;
			},
			set(value) {
				if (this.modelValue == null) {
					this._show = value;
					return;
				}
				this.$emit('update:modelValue', value);
			},
		},
	},
};
</script>
