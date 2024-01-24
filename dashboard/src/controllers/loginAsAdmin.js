import { notify } from '@/utils/toast';

export function loginAsAdmin(siteName) {
	return {
		url: 'press.api.site.login',
		params: { name: siteName },
		onSuccess(data) {
			if (data?.sid && data?.site) {
				window.open(`https://${data.site}/desk?sid=${data.sid}`, '_blank');
			}
		},
		validate() {
			// hack to display the toast
			notify({
				title: 'Attempting to login as Administrator',
				message: `Please wait...`,
				icon: 'alert-circle',
				color: 'yellow'
			});
		},
		onError(err) {
			notify({
				title: 'Could not login as Administrator',
				message: err.messages.join('\n'),
				color: 'red',
				icon: 'x'
			});
		}
	};
}
