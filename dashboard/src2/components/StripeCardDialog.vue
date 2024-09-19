<template>
	<Dialog v-model="show" :options="{ title: 'Add new card' }">
		<template #body-content>
			<p class="text-sm mb-5 text-gray-700" v-if="message">
				{{ message }}
			</p>
			<!-- <StripeCard2 @complete="show = false" /> -->
			<MidTransCard @complete="show = false" />
		</template>
	</Dialog>
</template>
<script>
import StripeCard from './StripeCard.vue';
import MidTransCard from './MidtransCard.vue';
export default {
	name: 'StripeCardDialog',
	props: ['modelValue', 'message'],
	emits: ['update:modelValue'],
	components: {
		StripeCard2: StripeCard,
		MidTransCard : MidTransCard
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
