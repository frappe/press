<script setup lang="ts">
import { computed, onMounted } from 'vue'
import FCLogo from '../components/icons/FCLogo.vue'
import { getActiveSites } from '../data/sites'
import { getTeam } from '../data/team'
import { session } from '../data/session'
import { trialDays } from '../utils/site'
import { planTitle } from '../utils/format'
import { getDocResource } from '../utils/resource'

defineOptions({ name: 'Quickstart' })

const team = getTeam()
const sitesResource = getActiveSites()
const sites = computed(() => sitesResource.data || [])

const sitePlan = (site) =>
	site.trial_end_date ? trialDays(site.trial_end_date) : planTitle(site)

const siteLoginMethods = {
	loginAsAdmin: 'login_as_admin',
	loginAsTeam: 'login_as_team',
}

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

		login.submit({ reason: '' }).then((url) => window.open(url, '_blank'))
	}
}

onMounted(() => {
	if (!sitesResource.data) sitesResource.list.fetch()
})
</script>

<template>
	<div class="mx-auto max-w-2xl px-5 py-10 min-h-screen" v-if="team?.doc">
		<!-- header -->
		<div class="flex items-center gap-2">
			<FCLogo class="size-8 rounded" />
			<div class="flex flex-col gap-0.5 mr-auto">
				<div class="text-base font-medium text-ink-gray-9">Frappe Cloud</div>
				<div class="text-sm text-ink-gray-5">Account</div>
			</div>

			<Button class="!text-ink-gray-7">
				<template #prefix>
					<Avatar
						:label="team.doc.user_info.first_name"
						:image="team.doc.user_info.user_image"
						size="sm"
						class="[&>*]:bg-surface-gray-4"
					/>
				</template>
				{{ team.doc.user_info.email }}
			</Button>

			<Button @click="session.logout.submit">
				<template #prefix>
					<LucideLogOut class="size-4" />
				</template>
				Sign out</Button
			>
		</div>

		<div class="flex items-start justify-between mt-10">
			<div>
				<h2 class="text-2xl font-semibold text-ink-gray-9">
					Where do you want to go?
				</h2>
				<p class="mt-1 text-p-base text-ink-gray-5">
					Select a site or continue to Frappe Cloud.
				</p>
			</div>

			<Button variant="solid" :route="{ name: 'Site List' }">
				Go to Dashboard
				<template #suffix>
					<lucide-arrow-right class="size-4" />
				</template>
			</Button>
		</div>

		<table class="mt-8 w-full text-sm" v-if="sites.length">
			<thead>
				<tr class="border-b">
					<th class="pb-3 text-left font-medium text-ink-gray-9">Your sites</th>
					<th class="pb-3 text-right font-normal text-ink-gray-5">Plan</th>
					<th class="pb-3 text-right font-normal text-ink-gray-5">
						{{ sites.length }}
						sites
					</th>
				</tr>
			</thead>

			<tbody>
				<tr
					class="border-b cursor-pointer"
					v-for="site in sites"
					:key="site.name"
					@click="openSite(site)"
				>
					<td class="py-3">
						<div class="flex items-center gap-3">
							<Avatar
								:label="site.host_name || site.name"
								shape="square"
								size="lg"
							/>
							<span class="text-base text-ink-gray-9">
								{{ site.host_name || site.name }}
							</span>
						</div>
					</td>
					<td class="py-3 text-right text-ink-gray-5">
						{{ sitePlan(site) }}
					</td>
					<td class="py-3">
						<div class="flex items-center gap-2 justify-end">
							<Badge :label="site.status" />
							<LucideChevronRight class="size-4 text-ink-gray-4" />
						</div>
					</td>
				</tr>
			</tbody>
		</table>

		<p class="mt-2 flex flex-col items-center gap-3 py-8 text-center" v-else>
			You don't have any sites yet.
		</p>

		<div
			class="flex justify-center gap-2 pt-4 text-sm text-ink-gray-6"
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
			<span>·</span>
			<a
				class="hover:text-ink-gray-8"
				href="https://frappecloud.com/policies"
				target="_blank"
			>
				Terms
			</a>
		</div>
	</div>
</template>
