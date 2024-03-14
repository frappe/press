import site from './site';
import bench from './bench';
import server from './server';
import notification from './notification';

let objects = {
	Site: site,
	Bench: bench,
	Server: server,
	Notification: notification
};

export function getObject(name) {
	return objects[name];
}

export default objects;
