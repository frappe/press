<template>
	<div
		class="pointer-events-none fixed inset-0 flex items-start justify-end px-4 py-6 sm:p-6"
	>
		<div>
			<Notification
				v-bind="props"
				class="mb-4"
				:key="i"
				v-for="(props, i) in notifications"
				@dismiss="hideNotification"
			/>
		</div>
	</div>
</template>
<script>
import Vue from 'vue';
import Notification from './Notification.vue';

export default {
	name: 'NotificationToasts',
	data() {
		return {
			notifications: []
		};
	},
	components: {
		Notification
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
