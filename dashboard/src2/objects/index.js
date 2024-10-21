import site from './site';
import group from './group';
import bench from './bench';
import marketplace from './marketplace';
import server from './server';
import notification from './notification';

let objects = {
	Site: site,
	Group: group,
	Bench: bench,
	Marketplace: marketplace,
	Server: server,
	Notification: notification
};

export function getObject(name) {
	return objects[name];
}

export default objects;
