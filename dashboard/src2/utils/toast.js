import { toast } from 'vue-sonner';

export function showErrorToast(error) {
	let errorMessage = e.messages.length ? e.messages.join('\n') : e.message;
	toast.error(errorMessage);
}
