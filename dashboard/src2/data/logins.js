import { createResource } from 'frappe-ui';

let oauthLogins = createResource({
	url: 'press.api.oauth.get_custom_oauths',
	cache: 'custom.logins',
	auto: true,
	initialData: []
});

export let getCustomOauths = () => {
	return oauthLogins.data || [];
};

export let oauthProviders = () => {
	let providers = {};
	oauthLogins.data.map(
		d =>
			(providers[d.email_domain] = {
				social_login_key: d.social_login_key,
				provider_name: d.provider_name
			})
	);
	return providers;
};
