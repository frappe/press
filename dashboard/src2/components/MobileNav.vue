<template>
	<Disclosure as="div" v-slot="{ open }">
		<div class="flex h-12 items-center border-b px-5">
			<span class="font-semibold">
				<router-link :to="{ name: 'Site List' }">
					<img
						:src="`/assets/press/images/frappecloud-logo.png`"
						class="h-7 w-7 shrink-0"
						alt="Frappe Cloud Logo"
					/>
				</router-link>
			</span>
			<Dropdown
				class="ml-auto"
				:options="[
					{
						label: 'Change Team',
						icon: 'command',
						onClick: () => (showTeamSwitcher = true)
					},
					{
						label: 'Support & Docs',
						icon: 'help-circle',
						onClick: support
					},
					{
						label: 'Logout',
						icon: 'log-out',
						onClick: $session.logout.submit
					}
				]"
			>
				<template v-slot="{ open }">
					<Button class="ml-auto">
						<template #suffix>
							<i-lucide-chevron-down class="h-3.5 w-3.5 text-gray-700" />
						</template>
						{{ $team?.get.loading ? 'Loading...' : $team.doc.user }}
					</Button>
				</template>
			</Dropdown>

			<DisclosureButton as="template">
				<Button class="ml-2">
					<template #icon>
						<i-lucide-x v-if="open" class="h-4 w-4 text-gray-700" />
						<i-lucide-menu v-else class="h-4 w-4 text-gray-700" />
					</template>
				</Button>
			</DisclosureButton>
		</div>
		<DisclosurePanel class="border-b bg-gray-100 px-5 py-2">
			<NavigationItems>
				<template v-slot="{ navigation }">
					<template v-for="(item, i) in navigation">
						<router-link custom v-slot="{ href, navigate }" :to="item.route">
							<a
								:href="href"
								@click="navigate"
								class="flex items-center rounded px-2 py-1.5 text-gray-800 transition"
								:class="[
									item.isActive ? 'bg-white shadow-sm' : 'hover:bg-gray-100',
									item.disabled ? 'pointer-events-none opacity-50' : '',
									$attrs.class
								]"
							>
								<div class="flex w-full items-center space-x-2">
									<span class="grid h-5 w-5 place-items-center">
										<component :is="item.icon" class="h-4 w-4 text-gray-500" />
									</span>
									<span class="text-base">{{ item.name }}</span>
								</div>
							</a>
						</router-link>
					</template>
				</template>
			</NavigationItems>
		</DisclosurePanel>
		<!-- TODO: update component name after dashboard-beta merges -->
		<SwitchTeamDialog2 v-model="showTeamSwitcher" />
	</Disclosure>
</template>
<script setup>
import { defineAsyncComponent, ref } from 'vue';
import { Disclosure, DisclosureButton, DisclosurePanel } from '@headlessui/vue';
import NavigationItems from './NavigationItems.vue';

const SwitchTeamDialog2 = defineAsyncComponent(() =>
	import('./SwitchTeamDialog.vue')
);
const showTeamSwitcher = ref(false);

function support() {
	window.open('https://frappecloud.com/support', '_blank');
}
</script>
