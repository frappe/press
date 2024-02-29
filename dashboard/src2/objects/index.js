import site from './site';
import bench from './bench';
import server from './server';

let objects = {
	Site: site,
	Bench: bench,
	Server: server
};

export function getObject(name) {
	return objects[name];
}

export default objects;
