<template>
	<div class="font-sans text-gray-900 antialiased">
		<div class="flex h-screen overflow-hidden">
			<div
				class="flex flex-1 overflow-y-auto"
				:class="{ 'sm:bg-gray-50': $route.meta.isLoginPage }"
			>
				<div class="flex-1">
					<Navbar v-if="$auth.isLoggedIn" />
					<div class="mx-auto lg:container">
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

		<!-- For Teleports -->
		<div id="modals"></div>
		<div id="popovers"></div>

		<NotificationToasts />
		<UserPrompts />
		<ConfirmDialogs />
	</div>
</template>
<script>
import Navbar from '@/components/Navbar.vue';
import UserPrompts from '@/views/UserPrompts.vue';
import ConfirmDialogs from './components/ConfirmDialogs.vue';
import NotificationToasts from './components/NotificationToasts.vue';

export default {
	name: 'App',
	components: {
		Navbar,
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
