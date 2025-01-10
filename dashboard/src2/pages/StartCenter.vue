<template>
	<div class="h-full sm:bg-gray-50">
		<div class="flex w-full items-center justify-center" v-if="false">
			<Spinner class="mr-2 w-4" />
			<p class="text-gray-800">Loading</p>
		</div>
		<div class="flex" v-else>
			<div class="h-full w-full overflow-auto">
				<SaaSLoginBox
					:title="`Hi, ${team?.doc?.user_info?.first_name}`"
					:subtitle="['Choose a site to log in to or visit the dashboard.']"
				>
					<template v-slot:default>
						<div class="space-y-4">
							<ObjectList :options="siteListOptions" />
						</div>
					</template>
				</SaaSLoginBox>
				<div class="flex w-full items-center justify-center pb-2">
					<Button
						class="mt-4"
						@click="
							team.doc.onboarding.complete
								? $router.push({
										name: 'Site List'
								  })
								: $router.push({
										name: 'Welcome'
								  })
						"
						icon-right="arrow-right"
						variant="ghost"
						label="Go to Dashboard"
					/>
				</div>
			</div>
		</div>
	</div>
</template>

<script setup>
import { computed, inject } from 'vue';
import { toast } from 'vue-sonner';
import { createListResource, createResource } from 'frappe-ui';
import SaaSLoginBox from '../components/auth/SaaSLoginBox.vue';
import { getToastErrorMessage } from '../utils/toast';
import ObjectList from '../components/ObjectList.vue';
import { trialDays } from '../utils/site';
import { userCurrency } from '../utils/format';

const team = inject('team');

const login = createResource({
	url: 'press.api.client.run_doc_method',
	onSuccess: url => {
		window.open(url.message, '_blank');
	}
});

const sites = createListResource({
	doctype: 'Site',
	filters: { status: 'Active' },
	fields: [
		'name',
		'site_label',
		'trial_end_date',
		'plan.plan_title as plan_title',
		'plan.price_usd as price_usd',
		'plan.price_inr as price_inr'
	],
	auto: true
});

const siteListOptions = computed(() => {
	return {
		data: () => sites.data || [],
		hideControls: true,
		emptyStateMessage: 'No sites found. Create a site from the dashboard.',
		onRowClick: row => {
			loginToSite(row.name);
		},
		columns: [
			{
				label: 'Site',
				fieldname: 'site_label',
				format: (_, row) => row.site_label || row.name
			},
			{
				label: '',
				fieldname: 'trial_end_date',
				align: 'right',
				class: ' text-sm',
				format: (value, row) => {
					if (value) return trialDays(value);
					if (row.price_usd > 0) {
						const india = team.doc?.currency === 'INR';
						const formattedValue = userCurrency(
							india ? row.price_inr : row.price_usd,
							0
						);
						return `${formattedValue}/mo`;
					}
					return row.plan_title;
				}
			}
		]
	};
});

function loginToSite(siteName) {
	if (!siteName) {
		toast.error('Please select a site');
		return;
	}

	toast.promise(
		login.submit({
			dt: 'Site',
			dn: siteName,
			method: 'login_as_team'
		}),
		{
			loading: 'Logging in ...',
			success: 'Logged in',
			error: e => getToastErrorMessage(e)
		}
	);
}
</script>
