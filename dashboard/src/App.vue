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
						<keep-alive
							:include="['Sites', 'Benches', 'Site', 'Bench', 'Account']"
						>
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
		<UserPrompts />
		<Dialog
			:title="dialog.title"
			v-for="dialog in confirmDialogs"
			v-model="dialog.show"
			@close="removeConfirmDialog(dialog)"
		>
			<div class="prose">
				<p class="text-base" v-html="dialog.message"></p>
			</div>
			<template slot="actions">
				<Button type="secondary" @click="removeConfirmDialog(dialog)">
					Cancel
				</Button>
				<Button
					class="ml-2"
					:type="dialog.actionType"
					@click="onDialogAction(dialog)"
				>
					{{ dialog.actionLabel }}
				</Button>
			</template>
		</Dialog>
	</div>
</template>
<script>
import Vue from 'vue';
import Notification from '@/components/Notification';
import Navbar from '@/components/Navbar';
import UserPrompts from '@/views/UserPrompts';

export default {
	name: 'App',
	components: {
		Notification,
		Navbar,
		UserPrompts
	},
	data() {
		return {
			notifications: [],
			confirmDialogs: [],
			viewportWidth: 0
		};
	},
	created() {
		Vue.prototype.$notify = this.notify;
		Vue.prototype.$confirm = this.confirm;
	},
	provide: {
		viewportWidth: Math.max(
			document.documentElement.clientWidth || 0,
			window.innerWidth || 0
		)
	},
	methods: {
		notify(props) {
			props.id = Math.floor(Math.random() * 1000 + Date.now());
			this.notifications.push(props);
			setTimeout(() => this.hideNotification(props.id), props.timeout || 5000);
		},
		confirm(dialog) {
			dialog.show = true;
			this.confirmDialogs.push(dialog);
		},
		onDialogAction(dialog) {
			let closeDialog = () => this.removeConfirmDialog(dialog);
			dialog.action(closeDialog);
		},
		removeConfirmDialog(dialog) {
			this.confirmDialogs = this.confirmDialogs.filter(
				_dialog => dialog !== _dialog
			);
		},
		hideNotification(id) {
			this.notifications = this.notifications.filter(props => props.id !== id);
		}
	}
};
</script>
<style src="./assets/style.css"></style>
