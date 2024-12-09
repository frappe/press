<template>
	<div class="relative flex h-full flex-col">
		<div class="h-full flex-1">
			<div class="flex h-full">
				<div
					v-if="!isSaaSFlow && !$isMobile && !isHideSidebar"
					class="relative block min-h-0 flex-shrink-0 overflow-hidden hover:overflow-auto"
				>
					<AppSidebar v-if="$session.user" />
				</div>
				<div class="w-full overflow-auto" id="scrollContainer">
					<MobileNav
						v-if="!isSaaSFlow && $isMobile && !isHideSidebar && $session.user"
					/>
					<div
						v-if="!isSaaSFlow && !$session.user && !$route.meta.isLoginPage"
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

const AppSidebar = defineAsyncComponent(() =>
	import('./components/AppSidebar.vue')
);
const MobileNav = defineAsyncComponent(() =>
	import('./components/MobileNav.vue')
);

const route = useRoute();
const team = getTeam();

const isHideSidebar = computed(() => {
	if (!session.user) return false;
	return (
		// using window.location.pathname as router is undefined initially
		(window.location.pathname === '/dashboard/welcome' ||
			route.name === 'Welcome') &&
		session.user &&
		team?.doc?.hide_sidebar === true
	);
});

const isSaaSFlow = ref(window.location.pathname.startsWith('/dashboard/saas'));

watch(
	() => route.name,
	() => {
		isSaaSFlow.value = window.location.pathname.startsWith('/dashboard/saas');
	}
);

provide('team', team);
</script>

<style src="../src/assets/style.css"></style>
