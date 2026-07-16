<script setup lang="ts">
import { computed, onMounted } from 'vue'
import FCLogo from '../components/icons/FCLogo.vue'
import { getActiveSites } from '../data/sites'
import { getTeam } from '../data/team'
import { session } from '../data/session'

defineOptions({ name: 'Quickstart' })

const team = getTeam()
const sitesResource = getActiveSites()
const sites = computed(() => sitesResource.data || [])

const accountDropdownOptions = [
	{ label: 'Logout', icon: 'log-out', onClick: session.logout.submit },
]

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

			<Button class='!text-ink-gray-7'>
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

			<Button>
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

		<div class="mt-8 flex items-center justify-between text-sm border-b pb-3">
			<span class="font-medium text-ink-gray-9">Your sites</span>
			<span class="text-ink-gray-5">{{ sites.length }} sites</span>
		</div>

		<template v-if="sites.length">
			<a
				class="flex items-center justify-between py-3 border-b"
				v-for="site in sites"
				:key="site.name"
				:href="'https://' + site.name"
			>
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
				<div class="flex items-center gap-2">
					<Badge :label="site.status" />
					<LucideChevronRight class="size-4 text-ink-gray-4" />
				</div>
			</a>
		</template>

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
