<template>
	<div class="flex flex-col md:flex-row h-full">
		<AppSidebar
			v-if="!isSignupFlow && !isHideSidebar && $session.user && $team?.doc && route.name !== 'Login'"
		/>

		<div class="w-full overflow-auto z-0" id="scrollContainer">
			<div
				class="border bg-surface-red-2 px-5 py-3 text-base text-ink-red-4"
				v-if="
        !isSignupFlow &&
        !isSiteLogin &&
        !$session.user &&
        !$route.meta.isLoginPage
      "
			>
				You are not logged in.
				<router-link to="/login" class="underline">Login</router-link>
				to access dashboard.
			</div>

			<router-view />
		</div>
	</div>

	<Toaster
		position="top-right"
		:toastOptions="{ class: 'text-sm prose-sm dark:bg-surface-cards dark:border-outline-gray-2 text-ink-gray-9' }"
	/>
	<component v-for="dialog in dialogs" :is="dialog" :key="dialog.id" />
	<SearchModal v-if="searchModalOpen" />
	<PartnerRegistrationModal
		v-if="partnerRegistrationModalOpen"
		v-model="partnerRegistrationModalOpen"
	/>
</template>

<script setup>
import { computed, defineAsyncComponent, provide, ref, watch } from 'vue'
import { useRoute } from 'vue-router'
import { Toaster } from 'vue-sonner'
import SearchModal from '@/components/navigation/search/Popup.vue'
import { useSearch } from '@/components/navigation/search/utils'
import { partnerRegistrationModalOpen, searchModalOpen } from '@/data/ui'
import { initTheme } from '@/utils/useTheme'
import { session } from './data/session.js'
import { getTeam } from './data/team'
import { dialogs } from './utils/components'

const AppSidebar = defineAsyncComponent(
	() => import('./components/navigation/sidebar/Sidebar.vue'),
)
const PartnerRegistrationModal = defineAsyncComponent(
	() => import('./onboarding/modal/PartnerOnboardingModal.vue'),
)

const route = useRoute()
const team = getTeam()

const isHideSidebar = computed(() => {
	const alwaysHideSidebarRoutes = [
		'Site Login',
		'SignupLoginToSite',
		'SignupSetup',
	]
	const alwaysHideSidebarPaths = ['/dashboard/site-login']

	if (!session.user) return false
	if (
		alwaysHideSidebarRoutes.includes(route.name) ||
		alwaysHideSidebarPaths.includes(window.location.pathname)
	)
		return true

	return (
		route.meta.hideSidebar && session.user && team?.doc?.hide_sidebar === true
	)
})

const isSignupFlow = ref(
	window.location.pathname.startsWith('/dashboard/create-site') ||
		window.location.pathname.startsWith('/dashboard/setup-account') ||
		window.location.pathname.startsWith('/dashboard/site-login') ||
		window.location.pathname.startsWith('/dashboard/signup'),
)
const isSiteLogin = ref(window.location.pathname.endsWith('/site-login'))

watch(
	() => route.name,
	() => {
		isSignupFlow.value =
			window.location.pathname.startsWith('/dashboard/create-site') ||
			window.location.pathname.startsWith('/dashboard/setup-account') ||
			window.location.pathname.startsWith('/dashboard/site-login') ||
			window.location.pathname.startsWith('/dashboard/signup')
	},
)

provide('team', team)
provide('session', session)

watch(
	() => team?.doc?.onboarding?.complete,
	(x) => {
		if (x) useSearch()
	},
	{ once: true },
)

initTheme()
</script>

<style src="./assets/style.css"></style>
