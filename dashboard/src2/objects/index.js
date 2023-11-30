import site from './site';
import bench from './bench';

let objects = {
	Site: site,
	Bench: bench
};

export function getObject(name) {
	return objects[name];
}

export default objects;
