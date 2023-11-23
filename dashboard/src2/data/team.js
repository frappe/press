import { createResource } from 'frappe-ui';

let team = createResource({
	url: '/api/method/press.api.account.current_team',
	cache: 'CurrentTeam'
});
team.fetch();

export default team;
