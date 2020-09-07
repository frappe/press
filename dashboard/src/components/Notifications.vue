<template>
	<div>
		<Popover :show-popup="isOpen" :hide-arrow="true" :placement="'bottom-end'">
			<div
				slot="target"
				class="h-full"
				v-on-outside-click="() => (isOpen = false)"
			>
				<button
					class="p-1 text-gray-900 rounded-md hover:bg-gray-50"
					aria-label="Notifications Menu"
					aria-haspopup="true"
					@click="isOpen = !isOpen"
				>
					<!-- bell-icon -->
					<!-- prettier-ignore -->
					<svg v-show="!newNotifications" width="20" height="20" viewBox="0 0 20 20" fill="none" xmlns="http://www.w3.org/2000/svg">
						<path d="M12.4658 15.0275H16.5867L15.4287 13.8695C15.2732 13.714 15.1499 13.5293 15.0658 13.3261C14.9816 13.1229 14.9383 12.9051 14.9384 12.6852V9.09341C14.9385 8.07055 14.6215 7.07281 14.0311 6.23755C13.4407 5.40228 12.6059 4.77057 11.6417 4.4294V4.14835C11.6417 3.71118 11.468 3.29192 11.1589 2.98279C10.8497 2.67367 10.4305 2.5 9.99331 2.5C9.55614 2.5 9.13687 2.67367 8.82775 2.98279C8.51862 3.29192 8.34496 3.71118 8.34496 4.14835V4.4294C6.42463 5.10852 5.04825 6.94066 5.04825 9.09341V12.686C5.04825 13.1294 4.87188 13.5555 4.55787 13.8695L3.3999 15.0275H7.52078M12.4658 15.0275H7.52078M12.4658 15.0275C12.4658 15.6832 12.2053 16.3121 11.7417 16.7758C11.278 17.2395 10.6491 17.5 9.99331 17.5C9.33755 17.5 8.70866 17.2395 8.24497 16.7758C7.78128 16.3121 7.52078 15.6832 7.52078 15.0275" stroke="#192734" stroke-linecap="round" stroke-linejoin="round"/>
					</svg>
					<!-- bell-icon-with-red-dot -->
					<!-- prettier-ignore -->
					<svg v-show="newNotifications" width="20" height="20" viewBox="0 0 20 20" fill="none" xmlns="http://www.w3.org/2000/svg">
						<path d="M12.4658 15.0275H16.5867L15.4287 13.8695C15.2732 13.714 15.1499 13.5293 15.0658 13.3261C14.9816 13.1229 14.9383 12.9051 14.9384 12.6852V9.09341C14.9385 8.07055 14.6215 7.07281 14.0311 6.23755C13.4407 5.40228 12.6059 4.77057 11.6417 4.4294V4.14835C11.6417 3.71118 11.468 3.29192 11.1589 2.98279C10.8497 2.67367 10.4305 2.5 9.99331 2.5C9.55614 2.5 9.13687 2.67367 8.82775 2.98279C8.51862 3.29192 8.34496 3.71118 8.34496 4.14835V4.4294C6.42463 5.10852 5.04825 6.94066 5.04825 9.09341V12.686C5.04825 13.1294 4.87188 13.5555 4.55787 13.8695L3.3999 15.0275H7.52078M12.4658 15.0275H7.52078M12.4658 15.0275C12.4658 15.6832 12.2053 16.3121 11.7417 16.7758C11.278 17.2395 10.6491 17.5 9.99331 17.5C9.33755 17.5 8.70866 17.2395 8.24497 16.7758C7.78128 16.3121 7.52078 15.6832 7.52078 15.0275" stroke="#192734" stroke-linecap="round" stroke-linejoin="round"/>
						<path d="M14 6.75C15.5188 6.75 16.75 5.51878 16.75 4C16.75 2.48122 15.5188 1.25 14 1.25C12.4812 1.25 11.25 2.48122 11.25 4C11.25 5.51878 12.4812 6.75 14 6.75Z" fill="#FF5858" stroke="white" stroke-width="1.5"/>
					</svg>
				</button>
			</div>
			<div slot="content" class="z-10 bg-white rounded-md w-96 max-h-120">
				<div
					v-if="notifications.length === 0"
					class="flex flex-col items-center justify-center w-full h-96"
				>
					<!-- prettier-ignore -->
					<svg class="w-16 h-16 stroke-current" viewBox="0 0 72 70" fill="none" xmlns="http://www.w3.org/2000/svg">
						<path d="M1 36C1 27.1634 8.16344 20 17 20H60C66.0751 20 71 24.9249 71 31V55C71 56.1046 70.1046 57 69 57H3C1.89543 57 1 56.1046 1 55V36Z" class="text-gray-600 " stroke-width="2"/>
						<path d="M1 36C1 27.1634 8.16344 20 17 20V20C25.8366 20 33 27.1634 33 36V57H1.72549C1.32481 57 1 56.6752 1 56.2745V36Z" class="text-gray-600 " stroke-width="2"/>
						<path d="M10 34H22" class="text-blue-500 " stroke-width="2" stroke-linecap="round"/>
						<path opacity="0.5" d="M10 38H17" class="text-blue-300 " stroke-width="2" stroke-linecap="round"/>
						<path d="M37 57H29V67C29 68.1046 29.8954 69 31 69H35C36.1046 69 37 68.1046 37 67V57Z" class="text-gray-600 " stroke-width="2"/>
						<path d="M46 11.4956H59.9942V1H50.3732C47.9679 1 46 2.96793 46 5.37318V31" class="text-gray-600 " stroke-width="2" stroke-miterlimit="10"/>
						<circle cx="46" cy="33" r="3" class="text-gray-600 " stroke-width="2"/>
					</svg>
					<div class="mt-4 text-base font-medium">No new notifications</div>
				</div>
				<div class="p-2" v-else>
					<div
						class="py-3.5 pl-3 pr-4 text-base hover:bg-gray-50 rounded-md flex"
						v-for="notification in notifications"
						:key="notification.message"
					>
						<div class="w-1 h-5 mr-2">
							<span
								v-show="!notification.read"
								class="flex-shrink-0 inline-block w-1 h-1 bg-blue-500 rounded-full"
							></span>
						</div>
						<p class="leading-5" v-html="notification.message"></p>
					</div>
				</div>
			</div>
		</Popover>
	</div>
</template>
<script>
import Popover from '@/components/Popover';

export default {
	name: 'Notifications',
	components: {
		Popover
	},
	data() {
		return {
			isOpen: false
		};
	},
	watch: {
		isOpen(value) {
			if (!value) {
				// mark all as read when notification dropdown is closed
				if (this.newNotifications) {
					this.$resources.markAsRead
						.submit()
						.then(() => this.$resources.notifications.reload());
				}
			}
		}
	},
	resources: {
		notifications: {
			method: 'press.api.account.notifications',
			auto: true,
			default: []
		},
		markAsRead: {
			method:
				'frappe.desk.doctype.notification_log.notification_log.mark_all_as_read'
		}
	},
	computed: {
		notifications() {
			return this.$resources.notifications.data;
		},
		newNotifications() {
			if (this.notifications.length === 0) return false;
			return this.notifications.some(n => !n.read);
		}
	}
};
</script>
