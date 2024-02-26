import site from './site';
import bench from './bench';
import marketplace from './marketplace';

let objects = {
	Site: site,
	Bench: bench,
	Marketplace: marketplace
};

export function getObject(name) {
	return objects[name];
}

export default objects;
