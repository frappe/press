<script setup>
import Notification from './Notification.vue';
import { hideNotification, notifications } from '@/utils/toast';
</script>

<template>
	<div
		class="pointer-events-none fixed inset-0 flex items-start justify-end px-4 py-6 sm:p-6"
	>
		<div class="fixed top-15">
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
