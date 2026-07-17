<script setup lang="ts">
import { computed, onMounted, ref } from 'vue'
import { Spinner } from 'frappe-ui'
import { toast } from 'vue-sonner'
import FCLogo from '@/components/icons/FCLogo.vue'
import { getActiveSites } from '@/data/sites'
import { getTeam } from '@/data/team'
import { trialDays } from '@/utils/site'
import { getDocResource } from '@/utils/resource'
import { getToastErrorMessage } from '@/utils/toast'

defineOptions({ name: 'Quickstart' })

const team = getTeam()
const sitesResource = getActiveSites()
const sites = computed(() => sitesResource.data || [])

const sitePlan = (site) =>
	site.trial_end_date ? trialDays(site.trial_end_date) : null

const siteLoginMethods = {
	loginAsAdmin: 'login_as_admin',
	loginAsTeam: 'login_as_team',
}

const loadingSite = ref(null)

const openSite = (site) => {
	if (site.status !== 'Archived' && site.setup_wizard_complete) {
		let siteURL = `https://${site.name}`
		if (site.version === 'Nightly' || Number(site.version?.split(' ')[1]) >= 15)
			siteURL += '/apps'
		window.open(siteURL, '_blank')
		return
	}

	if (site.status === 'Active' && !site.setup_wizard_complete) {
		const doc = getDocResource({
			doctype: 'Site',
			name: site.name,
			whitelistedMethods: siteLoginMethods,
		})

		const login = site.additional_system_user_created
			? doc.loginAsTeam
			: doc.loginAsAdmin

		loadingSite.value = site.name
		login
			.submit({ reason: '' })
			.then((url) => window.open(url, '_blank'))
			.catch((e) => {
				toast.error(getToastErrorMessage(e, 'Failed to set up site'))
			})
			.finally(() => {
				loadingSite.value = null
			})
		return
	}

	toast.error(`${site.host_name || site.name} isn't ready yet`)
}

onMounted(() => {
	if (!sitesResource.data) sitesResource.list.fetch()
})
</script>

<template>
	<div class="mx-auto max-w-sm px-5 py-20 min-h-screen" v-if="team?.doc">
		<!-- header -->
		<div class="flex items-center gap-2"></div>

		<FCLogo class="size-10 rounded mb-6" />

		<h2 class="text-2xl font-semibold text-ink-gray-9">
			Where do you want to go?
		</h2>

		<p class="mt-1 text-p-base text-ink-gray-5 mb-8">
			Select a site or continue to Frappe Cloud.
		</p>

		<template v-if="sites.length">
			<a
				v-for="(site, i) in sites.slice(0,3)"
				:key="site.name"
				class="grid grid-cols-[auto_1fr_auto] items-center gap-1.5 mb-3 cursor-pointer"
				@click="openSite(site)"
			>
				<LucideGlobe class="size-4 text-ink-gray-6 mt-1 mr-1" />
				<span class="text-base text-ink-gray-9">
					{{ site.host_name || site.name }}
				</span>

				<Spinner
					v-if="loadingSite === site.name"
					class="size-4 text-ink-gray-4"
				/>
				<LucideArrowRight v-else class="size-4 text-ink-gray-6" />

				<span />

				<div
					class="flex gap-2 items-center col-span-2 pb-3"
					:class="i == sites.slice(0,3).length - 1 ? '' : 'border-b'"
				>
					<span class="text-ink-gray-5" v-if="sitePlan(site)">
						{{ sitePlan(site) }}</span
					>
					<Badge :label="site.status" variant='outline' />
				</div>
			</a>
		</template>

		<p class="mt-2 flex flex-col items-center gap-3 py-8 text-center" v-else>
			You don't have any sites yet.
		</p>

		<Button variant="solid" :route="{ name: 'Site List' }" class="w-full mt-2">
			Go to Dashboard
		</Button>

		<div
			class="flex justify-center gap-2 pt-4  text-ink-gray-6"
			:class="sites.length ? '' : 'border-t'"
		>
			<a
				class="hover:text-ink-gray-8"
				href="https://frappe.io/contact-us"
				target="_blank"
			>
				Contact us
			</a>
			<span>·</span>
			<a
				class="hover:text-ink-gray-8"
				href="https://support.frappe.io/helpdesk/my-tickets/new"
				target="_blank"
			>
				Support
			</a>
		</div>
	</div>
</template>
