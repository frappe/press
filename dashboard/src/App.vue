<template>
	<div class="font-sans text-gray-900 antialiased">
		<div class="flex h-screen overflow-hidden">
			<div
				class="flex flex-1 overflow-y-auto"
				:class="{ 'sm:bg-gray-50': $route.meta.isLoginPage }"
			>
				<div class="flex-1">
					<div class="mx-auto flex flex-row justify-start">
						<Sidebar
							class="hidden top-0 sm:flex flex-shrink-0 w-64"
							v-if="$auth.isLoggedIn"
						/>
						<router-view
							v-slot="{ Component }"
							class="w-full pb-8 sm:mr-0 p-6"
						>
							<keep-alive
								:include="[
									'Sites',
									'Benches',
									'Servers',
									'Site',
									'Bench',
									'Server',
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
import Sidebar from '@/views/saas/Sidebar.vue';
import UserPrompts from '@/views/onboarding/UserPrompts.vue';
import ConfirmDialogs from '@/components/ConfirmDialogs.vue';
import NotificationToasts from '@/components/NotificationToasts.vue';
export default {
	name: 'App',
	components: {
		Navbar,
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
	provide: {
		viewportWidth: Math.max(
			document.documentElement.clientWidth || 0,
			window.innerWidth || 0
		)
	}
};
</script>
<style src="./assets/style.css"></style>
