import { mount } from '@vue/test-utils';
import { test, describe, expect } from 'vitest';
import StarRatingInput from '@/components/StarRatingInput.vue';

describe('Star Rating Component', () => {
	test('should display 5 star icons', () => {
		expect(StarRatingInput).toBeTruthy();

		const wrapper = mount(StarRatingInput);
		expect(wrapper.findAll('svg').length).toBe(5);
	});

	test('should emit on star click', () => {
		const wrapper = mount(StarRatingInput);

		// Click on the second star
		wrapper.findAll('svg')[1].trigger('click');

		// An modelValue update event should be emitted
		expect(wrapper.emitted()).toHaveProperty('update:modelValue');

		// The modelValue should be 1
		const updateEvent = wrapper.emitted('update:modelValue');

		// Should emit "2" as the emit payload
		expect(updateEvent[1][0]).toBe(2);
	});
});
