<template>
	<div class="relative flex h-full flex-col">
		<div class="h-full flex-1">
			<div class="flex h-full">
				<div
					v-if="!isSignupFlow && !$isMobile && !isHideSidebar"
					class="relative block min-h-0 flex-shrink-0 overflow-hidden hover:overflow-auto"
				>
					<AppSidebar v-if="$session.user && $team?.doc" />
				</div>
				<div class="w-full overflow-auto z-0" id="scrollContainer">
					<MobileNav
						v-if="!isSignupFlow && $isMobile && !isHideSidebar && $session.user"
					/>
					<div
						v-if="
							!isSignupFlow &&
							!isSiteLogin &&
							!$session.user &&
							!$route.meta.isLoginPage
						"
						class="border bg-red-200 px-5 py-3 text-base text-red-900"
					>
						You are not logged in.
						<router-link to="/login" class="underline">Login</router-link> to
						access dashboard.
					</div>
					<router-view />
				</div>
			</div>
		</div>
		<Toaster position="top-right" />
		<component v-for="dialog in dialogs" :is="dialog" :key="dialog.id" />
	</div>
</template>

<script setup>
import { defineAsyncComponent, computed, watch, ref, provide } from 'vue';
import { Toaster } from 'vue-sonner';
import { dialogs } from './utils/components';
import { useRoute } from 'vue-router';
import { getTeam } from './data/team';
import { session } from './data/session.js';

const AppSidebar = defineAsyncComponent(
	() => import('./components/AppSidebar.vue'),
);
const MobileNav = defineAsyncComponent(
	() => import('./components/MobileNav.vue'),
);

const route = useRoute();
const team = getTeam();

const isHideSidebar = computed(() => {
	const alwaysHideSidebarRoutes = [
		'Site Login',
		'SignupLoginToSite',
		'SignupSetup',
	];
	const alwaysHideSidebarPaths = ['/dashboard/site-login'];

	if (!session.user) return false;
	if (
		alwaysHideSidebarRoutes.includes(route.name) ||
		alwaysHideSidebarPaths.includes(window.location.pathname)
	)
		return true;

	return (
		route.meta.hideSidebar && session.user && team?.doc?.hide_sidebar === true
	);
});

const isSignupFlow = ref(
	window.location.pathname.startsWith('/dashboard/create-site') ||
		window.location.pathname.startsWith('/dashboard/setup-account') ||
		window.location.pathname.startsWith('/dashboard/site-login') ||
		window.location.pathname.startsWith('/dashboard/signup'),
);
const isSiteLogin = ref(window.location.pathname.endsWith('/site-login'));

watch(
	() => route.name,
	() => {
		isSignupFlow.value =
			window.location.pathname.startsWith('/dashboard/create-site') ||
			window.location.pathname.startsWith('/dashboard/setup-account') ||
			window.location.pathname.startsWith('/dashboard/site-login') ||
			window.location.pathname.startsWith('/dashboard/signup');
	},
);

provide('team', team);
provide('session', session);
</script>

<style src="./assets/style.css"></style>
