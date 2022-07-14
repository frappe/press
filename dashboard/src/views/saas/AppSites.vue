<script setup>
import { computed, ref } from 'vue';
import useResource from '@/composables/resource';
import call from '../../controllers/call';

const props = defineProps({ app: Object, appName: String });

const sites = useResource({
	method: 'press.api.saas.get_sites',
	auto: true,
	params: {
		name: props.appName
	}
});

let sitesList = computed(() => {
	return sites.data;
});

const siteBadge = site => {
	let status = site.status;
	let color = '';

	if (site.status == 'Active') {
		color = 'green';
	} else if (site.status == 'Inactive') {
		color = 'grey';
	} else if (site.status == 'Broken') {
		color = 'red';
	}

	return {
		color,
		status
	};
};

const dropdownItems = (team_name, site_name) => {
	return [
		{
			label: 'Login As Administrator',
			action: async () => {
				let sid = await call('press.api.site.login', { name: site_name });

				if (sid) {
					window.open(`https://${site_name}/desk?sid=${sid}`, '_blank');
				}
			}
		},
		{
			label: 'Visit Site',
			icon: 'external-link',
			action: r => {
				window.open(`https://${site_name}`, '_blank');
			}
		},
		{
			label: 'Update Site',
			action: () => alert('This feature will be released soon')
		}
	];
};
</script>

<template>
	<div v-if="props.appName">
		<Card title="Customer Sites" v-if="sitesList">
			<div class="my-2" v-for="site in sitesList" :key="site.name">
				<div class="flex items-center justify-between sm:justify-start">
					<div class="text-base sm:w-4/12">
						{{ site.name }}
					</div>
					<div class="text-base sm:w-4/12">
						<Badge class="pointer-events-none" v-bind="siteBadge(site)" />
					</div>
					<div class="text-base sm:w-4/12">
						{{ site.plan }}
					</div>
					<div class="text-base sm:w-4/12">
						{{ site.team }}
					</div>
					<Dropdown
						class="ml-2"
						:items="dropdownItems(site.team, site.name)"
						right
					>
						<template v-slot="{ toggleDropdown }">
							<Button icon-right="chevron-down" @click="toggleDropdown()"
								>Actions</Button
							>
						</template>
					</Dropdown>
				</div>
			</div>
		</Card>
	</div>
</template>
