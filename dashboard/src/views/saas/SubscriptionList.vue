<script setup>
import { computed, ref } from 'vue';
import useResource from '@/composables/resource';
import call from '../../controllers/call';
import AppCard from './AppCard.vue';
import NewSubscription from './NewSubscription.vue';

const saasApps = useResource({
	method: 'press.api.saas.get_apps',
	auto: true
});

const subscriptions = useResource({
	method: 'press.api.saas.get_subscriptions',
	auto: true
});

const sites = computed(() => {
	return subscriptions.data;
});

const badge = status => {
	let color = '';
	if (status == 'Active') {
		color = 'green';
	} else {
		color = 'gray';
	}
	return {
		color: color,
		status: status
	};
};
</script>
<template>
	<div v-if="subscriptions" class="mt-8 flex-1">
		<div class="flex items-center justify-between pb-4">
			<h3 class="text-xl font-bold">Apps</h3>
			<router-link to="/saas/new-subscription">
				<Button type="primary" iconLeft="plus">New App</Button>
			</router-link>
		</div>
		<div
			class="py-2 px-2 sm:rounded-md sm:border sm:border-gray-100 sm:py-1 sm:px-2 sm:shadow"
		>
			<div
				v-if="sites && sites.length > 0"
				class="py-2"
				v-for="sub in sites"
				:key="sub.name"
			>
				<router-link
					:to="`/saas/apps/${sub.name}/plan`"
					:site="sub.site"
					class="block rounded-md py-2 hover:bg-gray-50 sm:px-2"
				>
					<div class="flex items-center justify-between sm:justify-start">
						<div class="text-base sm:w-4/12">
							{{ sub.app_name }}
						</div>
						<div class="text-base sm:w-4/12">
							<Badge class="pointer-events-none" v-bind="badge(sub.status)" />
						</div>
						<div class="w-2/12 text-sm text-gray-600 sm:block">
							{{ sub.site }}
						</div>
						<div class="text-right text-base sm:w-4/12">
							<Link
								:to="`https://${sub.site}`"
								target="_blank"
								class="inline-flex items-center text-sm"
								@click.stop
							>
								Visit Site
								<FeatherIcon name="external-link" class="ml-1 h-3 w-3" />
							</Link>
						</div>
					</div>
				</router-link>
			</div>
			<div v-else class="text-center py-4 text-base">
				No App Subscriptions Found
			</div>
		</div>
	</div>
	<NewSubscription v-else />
</template>
