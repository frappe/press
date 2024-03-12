import site from './site';
import bench from './bench';
import marketplace from './marketplace';
import server from './server';

let objects = {
	Site: site,
	Bench: bench,
	Marketplace: marketplace,
	Server: server
};

export function getObject(name) {
	return objects[name];
}

export default objects;
