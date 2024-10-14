import { defineAsyncComponent, h } from 'vue';
import { renderDialog } from '../../utils/components';
import type { BannerConfig, Resource } from './types';

export const clusterOptions = [
	'',
	'Bahrain',
	'Cape Town',
	'Frankfurt',
	'KSA',
	'London',
	'Mumbai',
	'Singapore',
	'UAE',
	'Virginia',
	'Zurich'
];

export function getUpsellBanner(site: Resource, title: string) {
	if (site.doc.current_plan?.private_benches || !site.doc.group_public) return;

	return {
		title: title,
		dismissable: true,
		id: site.name,
		button: {
			label: 'Upgrade Plan',
			variant: 'outline',
			onClick() {
				let SitePlansDialog = defineAsyncComponent(
					() => import('../../components/ManageSitePlansDialog.vue')
				);
				renderDialog(h(SitePlansDialog, { site: site.name }));
			}
		}
	} satisfies BannerConfig as BannerConfig;
}
