import { createResource } from 'frappe-ui';

let team = createResource({
	url: 'press.api.account.get',
	cache: 'CurrentTeam'
});

export default team;
