import { toast } from 'vue-sonner';
import { h } from 'vue';

export function showErrorToast(error) {
	let errorMessage = error.messages?.length
		? error.messages.join('\n')
		: error.message;
	toast.error(errorMessage);
}

export function getToastErrorMessage(e, fallbackMessage = 'An error occurred') {
	const errorMessage = e.messages?.length
		? e.messages.join('<br>')
		: e.message || fallbackMessage;
	return h('div', {
		innerHTML: errorMessage,
	});
}
