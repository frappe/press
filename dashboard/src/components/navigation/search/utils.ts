import { searchModalOpen } from '@/data/ui';
import { useMagicKeys, whenever } from '@vueuse/core';
import { addIntegrations } from './integrations';

export const filterLabels = (data, query) => {
	const q = query.toLowerCase();
	const result = {};

	for (const [group, v] of Object.entries(data)) {
		if (group.toLowerCase().includes(q)) {
			result[group] = { items: v.items };
			continue;
		}

		const filtered = v.items.filter((item) =>
			item.name.toLowerCase().includes(q),
		);

		if (filtered.length) {
			result[group] = { items: filtered };
		}
	}

	return result;
};

export const useSearch = async () => {
	const { meta_k } = useMagicKeys();

	whenever(meta_k, (n) => {
		if (n) searchModalOpen.value = true;
	});

	addIntegrations();
};
