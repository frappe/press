<template>
	<div>
		<div
			class="flex h-screen w-screen items-center justify-center"
			v-if="false"
		>
			<Spinner class="mr-2 w-4" />
			<p class="text-gray-800">Loading</p>
		</div>
		<div class="flex h-screen overflow-hidden sm:bg-gray-50" v-else>
			<div class="w-full overflow-auto">
				<SaaSLoginBox
					:title="`Hi, ${team?.doc?.user_info?.first_name}`"
					:subtitle="['Choose a site to log in to or visit the dashboard.']"
				>
					<template v-slot:default>
						<div class="space-y-4">
							<div class="space-y-4">
								<FormControl
									class="w-full"
									type="autocomplete"
									:options="
										(sites.data || []).map(site => ({
											label: site.site_label || site.name,
											value: site.name,
											description: site.site_label ? site.name : null
										}))
									"
									v-model="selectedSite"
									placeholder="Select a site"
								/>
								<div class="flex items-end gap-1">
									<Button
										class="w-full"
										:disabled="!selectedSite"
										@click="loginToSite"
										icon-left="external-link"
										label="Login to Site"
										:loading="login.loading"
									/>

									<Button
										class="w-full"
										@click="
											team.doc.onboarding.complete
												? $router.push({
														name: 'Site List'
												  })
												: $router.push({
														name: 'Welcome'
												  })
										"
										icon-left="tool"
										label="Go to Dashboard"
									/>
								</div>
							</div>
						</div>
					</template>
				</SaaSLoginBox>
			</div>
		</div>
	</div>
</template>

<script setup>
import { computed, inject, ref } from 'vue';
import { toast } from 'vue-sonner';
import { createListResource, createResource } from 'frappe-ui';
import SaaSLoginBox from '../components/auth/SaaSLoginBox.vue';
import { getToastErrorMessage } from '../utils/toast';
import { useRoute } from 'vue-router';

const team = inject('team');
const route = useRoute();

const selectedSite = ref('');

const login = createResource({
	url: 'press.api.client.run_doc_method',
	onSuccess: url => {
		window.open(url.message, '_blank');
	}
});

const product = route.query.product;
createListResource({
	doctype: 'Site',
	filters: { status: 'Active', standby_for_product: product },
	fields: ['name', 'site_label'],
	auto: !!product,
	onSuccess: data => {
		if (data.length === 1) {
			selectedSite.value = {
				value: data[0].name
			};
		}
	}
});

const sites = createListResource({
	doctype: 'Site',
	filters: { status: 'Active', standby_for_product: ['is', 'set'] },
	fields: ['name', 'site_label'],
	auto: true
});

function loginToSite() {
	if (!selectedSite) {
		toast.error('Please select a site');
		return;
	}

	toast.promise(
		login.submit({
			dt: 'Site',
			dn: selectedSite.value.value,
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
