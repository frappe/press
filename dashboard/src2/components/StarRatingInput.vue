<script setup>
import { ref } from 'vue';

// For v-model binding
const props = defineProps({
	modelValue: {
		type: Number,
		default: 5
	}
});
const emit = defineEmits(['update:modelValue']);

const tempValue = ref(null);
const value = ref(props.modelValue);
const ratings = [1, 2, 3, 4, 5];

const starOver = index => {
	tempValue.value = value.value;
	return (value.value = index);
};

const starOut = () => {
	return (value.value = tempValue.value);
};

const set = newValue => {
	tempValue.value = value.value;
	emit('update:modelValue', value.value);
	return (value.value = newValue);
};
</script>

<template>
	<div class="star-rating">
		<label
			class="star-rating__star"
			v-for="rating in ratings"
			v-on:click="set(rating)"
			v-on:mouseover="starOver(rating)"
			v-on:mouseout="starOut"
		>
			<input
				class="star-rating star-rating__checkbox"
				type="radio"
				:value="rating"
				v-model="value" />
			<svg
				class="h-4 w-4"
				xmlns="http://www.w3.org/2000/svg"
				viewBox="0 0 14 14"
				fill="none"
			>
				<path
					d="M6.56866 0.735724C6.76184 0.406233 7.23816 0.406233 7.43134 0.735725L9.16063 3.68535C9.23112 3.80559 9.34861 3.89095 9.48475 3.92084L12.8244 4.65401C13.1974 4.73591 13.3446 5.18892 13.091 5.47446L10.8201 8.03059C10.7275 8.1348 10.6826 8.27291 10.6963 8.41162L11.031 11.8144C11.0684 12.1945 10.683 12.4745 10.3331 12.3214L7.20032 10.9516C7.07261 10.8958 6.92739 10.8958 6.79968 10.9516L3.66691 12.3214C3.31696 12.4745 2.9316 12.1945 2.96899 11.8144L3.30371 8.41162C3.31736 8.27291 3.27248 8.1348 3.17991 8.03059L0.90903 5.47446C0.655358 5.18892 0.802551 4.73591 1.17561 4.65401L4.51525 3.92084C4.65139 3.89095 4.76888 3.80559 4.83937 3.68535L6.56866 0.735724Z"
					:fill="value >= rating && value != null ? '#ECAC4B' : '#C0C6CC'"
				/></svg
		></label>
	</div>
</template>

<style>
.star-rating__checkbox {
	position: absolute;
	overflow: hidden;
	clip: rect(0 0 0 0);
	height: 1px;
	width: 1px;
	margin: -1px;
	padding: 0;
	border: 0;
}

.star-rating__star {
	display: inline-block;
}

.star-rating__star:hover {
	cursor: pointer;
}
</style>
