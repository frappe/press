<script setup>
import { getCurrentInstance, ref } from 'vue';
import Notification from './Notification.vue';

const app = getCurrentInstance();
const notifications = ref([]);

const hideNotification = id => {
	notifications.value = notifications.value.filter(props => props.id !== id);
};

const notify = props => {
	props.id = Math.floor(Math.random() * 1000 + Date.now());
	notifications.value.push(props);
	setTimeout(() => hideNotification(props.id), props.timeout || 5000);
};

// Attach to global instance
app.appContext.config.globalProperties.$notify = notify;
</script>

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
