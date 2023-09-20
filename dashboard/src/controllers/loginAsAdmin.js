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
		onError() {
			notify({
				title: 'Could not login as Administrator',
				color: 'red',
				icon: 'x'
			});
		}
	};
}
