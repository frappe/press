import { toast } from 'vue-sonner'

export function showOnboardingToast(
	type: 'success' | 'error',
	message: string,
) {
	return toast[type](message, { position: 'bottom-right' })
}
