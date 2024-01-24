import { io } from 'socket.io-client';
import config from '../../../../../sites/common_site_config.json';

let host = window.location.hostname;
let port = window.location.port ? `:${config.socketio_port}` : '';
let protocol = port ? 'http' : 'https';
let siteName = window.site_name || host;
let url = `${protocol}://${host}${port}/${siteName}`;
let socket = io(url, {
	withCredentials: true
});

export default socket;
