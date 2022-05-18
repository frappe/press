import { mount } from '@vue/test-utils';
import { describe, expect, test } from 'vitest';
import FeatureList from '@/components/FeatureList.vue';

describe('FeatureList Component', () => {
	test('feature list renders with 2 features in correct order', async () => {
		expect(FeatureList).toBeTruthy();

		const wrapper = mount(FeatureList, {
			props: {
				features: ['Feature 1', 'Feature 2']
			}
		});

		expect(wrapper.findAll('li').length).toBe(2);
		expect(wrapper.findAll('li')[0].text()).toBe('Feature 1');
		expect(wrapper.findAll('li')[1].text()).toBe('Feature 2');
	});
});
