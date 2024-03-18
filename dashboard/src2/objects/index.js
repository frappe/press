import site from './site';
import bench from './bench';
import marketplace from './marketplace';
import server from './server';
import notification from './notification';

let objects = {
	Site: site,
	Bench: bench,
	Marketplace: marketplace,
	Server: server,
	Notification: notification
};

export function getObject(name) {
	return objects[name];
}

export default objects;
