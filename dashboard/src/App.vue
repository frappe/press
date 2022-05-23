<template>
	<div class="font-sans text-gray-900 antialiased">
		<div class="flex h-screen overflow-hidden">
			<div
				class="flex flex-1 overflow-y-auto"
				:class="{ 'sm:bg-gray-50': $route.meta.isLoginPage }"
			>
				<div class="flex-1">
					<SaasNavbar v-if="showSaas" />
					<Navbar v-if="$auth.isLoggedIn && !showSaas" />
					<div
						class="mx-auto justify-start lg:container"
						:class="{ flex: showSaas }"
					>
						<Sidebar v-if="showSaas" />
						<router-view v-slot="{ Component }">
							<keep-alive
								:include="[
									'Sites',
									'Benches',
									'Site',
									'Bench',
									'Marketplace',
									'Account',
									'MarketplaceApp'
								]"
							>
								<component :is="Component" />
							</keep-alive>
						</router-view>
					</div>
				</div>
			</div>
		</div>

		<NotificationToasts />
		<UserPrompts v-if="$auth.isLoggedIn" />
		<ConfirmDialogs />
	</div>
</template>
<script>
import Navbar from '@/components/Navbar.vue';
import SaasNavbar from '@/views/saas/SaasNavbar.vue';
import Sidebar from '@/views/saas/Sidebar.vue';
import UserPrompts from '@/views/UserPrompts.vue';
import ConfirmDialogs from './components/ConfirmDialogs.vue';
import NotificationToasts from './components/NotificationToasts.vue';
export default {
	name: 'App',
	components: {
		Navbar,
		SaasNavbar,
		Sidebar,
		UserPrompts,
		ConfirmDialogs,
		NotificationToasts
	},
	data() {
		return {
			viewportWidth: 0
		};
	},
	computed: {
		showSaas() {
			if (
				this.$auth.isLoggedIn &&
				this.$saas.isSaasLogin &&
				localStorage.getItem('saas_login')
			) {
				return true;
			}
			return false;
		}
	},
	provide: {
		viewportWidth: Math.max(
			document.documentElement.clientWidth || 0,
			window.innerWidth || 0
		)
	}
};
</script>
<style src="./assets/style.css"></style>
