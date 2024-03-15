<template>
	<Dialog v-model="show" :options="{ title: 'Add new card' }">
		<template #body-content>
			<StripeCard2 @complete="show = false" />
		</template>
	</Dialog>
</template>
<script>
import StripeCard from './StripeCard.vue';
export default {
	name: 'StripeCardDialog',
	props: ['modelValue'],
	emits: ['update:modelValue'],
	components: {
		StripeCard2: StripeCard
	},
	data() {
		return {
			_show: true
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
			}
		}
	}
};
</script>
