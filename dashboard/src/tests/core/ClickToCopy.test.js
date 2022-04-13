import { nextTick } from 'vue';
import { mount } from '@vue/test-utils';
import { describe, expect, test, vi } from 'vitest';
import ClickToCopyField from '@/components/ClickToCopyField.vue';

// Mocking clipboard API
let clipboardData = '';
Object.assign(window.navigator, {
	clipboard: {
		writeText: vi.fn(data => {
			clipboardData = data;
			return Promise.resolve();
		}),
		readText: vi.fn(() => clipboardData)
	}
});

describe('ClickToCopyField Component', () => {
	test('displays the passed text content', () => {
		expect(ClickToCopyField).toBeTruthy();

		const wrapper = mount(ClickToCopyField, {
			props: {
				textContent: 'Test'
			}
		});

		expect(wrapper.html()).contains('Test');
	});

	test("let's us copy with a button click", async () => {
		expect(ClickToCopyField).toBeTruthy();

		const wrapper = mount(ClickToCopyField, {
			props: {
				textContent: 'Test'
			}
		});

		wrapper.find('button').isVisible();
		wrapper.find('button').trigger('click');

		await nextTick();

		expect(navigator.clipboard.readText()).toBe('Test');
	});
});
