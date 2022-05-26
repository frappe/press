import { mount, config } from '@vue/test-utils';
import { test, describe, expect } from 'vitest';
import RichSelect from '@/components/RichSelect.vue';
import { setupGlobalConfig } from '../setup/msw';
import { nextTick } from 'vue';

setupGlobalConfig(config); // Setup vue app global config

// Ref: Testing teleports
// https://test-utils.vuejs.org/guide/advanced/teleport.html#interacting-with-the-teleported-component

let wrapper;

beforeEach(() => {
	// create teleport target
	const el = document.createElement('div');
	el.id = 'popovers';
	document.body.appendChild(el);

	wrapper = mount(RichSelect, {
		props: {
			value: 'opt-1',
			options: [
				{
					label: 'Option 1',
					value: 'opt-1',
					image: 'https://via.placeholder.com/100x100'
				},
				{
					label: 'Option 2',
					value: 'opt-2',
					image: 'https://via.placeholder.com/200x200'
				}
			]
		}
	});
});

afterEach(() => {
	// clean up
	document.body.outerHTML = '';
});

describe('Rich Select Component', () => {
	test('should display a dropdown menu', () => {
		expect(RichSelect).toBeTruthy();

		expect(wrapper.find('button').exists()).toBe(true);

		// Image should be displayed along with the label
		expect(wrapper.find('img').exists()).toBe(true);
		expect(wrapper.find('img').attributes('src')).toBe(
			'https://via.placeholder.com/100x100'
		);

		expect(wrapper.text()).toContain('Option 1');
	});

	test('should display a popup with desired options', () => {
		expect(wrapper.find('button').exists()).toBe(true);
		wrapper.find('button').trigger('click');

		// Test images are displayed
		const images = document.getElementsByTagName('img');
		expect(images.length).toBe(2);
		expect(images[0].src).toBe('https://via.placeholder.com/100x100');
		expect(images[1].src).toBe('https://via.placeholder.com/200x200');

		// Test labels are displayed
		expect(images[0].parentNode.children[1].innerHTML).toBe('Option 1');
		expect(images[1].parentNode.children[1].innerHTML).toBe('Option 2');
	});

	test('should emit on clicking of other option', () => {
		wrapper.find('button').trigger('click');
		expect(wrapper.text()).toContain('Option 1');
		const images = document.getElementsByTagName('img');

		images[1].parentNode.click();
		expect(wrapper.emitted('change')[0]).toEqual(['opt-2']);
	});
});
