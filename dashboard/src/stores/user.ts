import { defineStore } from 'pinia';

declare global {
	interface Window {
		user: {
			id: number;
			name: string;
			email: string;
			is_system_manager: boolean;
			is_desk_user: boolean;
			is_beta_tester: boolean;
		}
	}
}

export const useUserStore = defineStore('user', {
	state: () => ({
		...window.user,
		isSystemManager: window.user.is_system_manager,
		isDeskUser: window.user.is_desk_user,
		isBetaTester: window.user.is_beta_tester,
	})
})
