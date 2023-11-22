import { toast } from 'vue-sonner';
import dayjs from './utils/dayjs';
import session from './data/session';
import theme from '../tailwind.theme.json';
import { debounce } from 'frappe-ui';
import { getTeam } from './data/team';
import * as formatters from './utils/format';

export default function globals(app) {
	app.config.globalProperties.$session = session;
	app.config.globalProperties.$toast = toast;
	app.config.globalProperties.$dayjs = dayjs;
	app.config.globalProperties.$theme = theme;
	app.config.globalProperties.$platform = getPlatform();
	app.config.globalProperties.$format = formatters;
	app.config.globalProperties.$log = console.log;
	app.config.globalProperties.$debounce = debounce;
	app.config.globalProperties.$team = getTeam();
}

function getPlatform() {
	const ua = navigator.userAgent.toLowerCase();

	if (ua.indexOf('win') > -1) {
		return 'win';
	} else if (ua.indexOf('mac') > -1) {
		return 'mac';
	} else if (ua.indexOf('x11') > -1 || ua.indexOf('linux') > -1) {
		return 'linux';
	}
}
