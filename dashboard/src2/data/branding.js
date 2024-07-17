import { createResource } from 'frappe-ui';

export let BrandInfo = createResource({
	url: 'press.api.utils.get_brand_details',
	cache: 'site.brand',
	initialData: []
});

export function fetchBrandInfo() {
	BrandInfo.fetch();
}

export function getBrandInfo() {
	return brand.data || [];
}
