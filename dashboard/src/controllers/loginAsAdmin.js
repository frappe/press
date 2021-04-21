export function loginAsAdmin(siteName) {
	return {
		method: 'press.api.site.login',
		params: { name: siteName },
		onSuccess(sid) {
			if (sid) {
				window.open(`https://${siteName}/desk?sid=${sid}`, '_blank');
			}
		},
		onError() {
			this.$notify({
				title: 'An error occurred',
				color: 'red',
				icon: 'x'
			});
		}
	};
}
