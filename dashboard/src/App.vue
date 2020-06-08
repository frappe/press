<template>
	<div class="font-sans antialiased text-gray-900">
		<div class="flex h-screen overflow-hidden">
			<div
				class="flex flex-1 overflow-y-auto"
				:class="{ 'sm:bg-gray-50': $route.meta.isLoginPage }"
			>
				<div class="flex-1">
					<Navbar v-if="$auth.isLoggedIn" />
					<div class="container mx-auto">
						<keep-alive :include="['Sites', 'Apps', 'Site', 'App', 'Account']">
							<router-view />
						</keep-alive>
					</div>
				</div>
			</div>
		</div>
		<portal-target name="popovers" multiple></portal-target>
		<portal-target name="modals" multiple></portal-target>
		<div
			class="fixed inset-0 flex items-start justify-end px-4 py-6 pointer-events-none sm:p-6"
		>
			<div>
				<Notification
					class="mb-4"
					:key="i"
					v-for="(props, i) in notifications"
					v-bind="props"
					@dismiss="hideNotification"
				/>
			</div>
		</div>
		<CountrySelectionDialog />
	</div>
</template>
<script>
import Vue from 'vue';
import Notification from '@/components/Notification';
import Navbar from '@/components/Navbar';
import CountrySelectionDialog from '@/views/CountrySelectionDialog';

export default {
	name: 'App',
	components: {
		Notification,
		Navbar,
		CountrySelectionDialog
	},
	data() {
		return {
			notifications: []
		};
	},
	created() {
		Vue.prototype.$notify = this.notify;
	},
	methods: {
		notify(props) {
			props.id = Math.floor(Math.random() * 1000 + Date.now());
			this.notifications.push(props);
			setTimeout(() => this.hideNotification(props.id), props.timeout || 5000);
		},
		hideNotification(id) {
			this.notifications = this.notifications.filter(props => props.id !== id);
		}
	}
};
</script>
<style src="./assets/style.css"></style>
