import site from './site';
import bench from './bench';
import marketplace from './marketplace';
import server from './server';
import databaseServer from './db-server';

let objects = {
	Site: site,
	Bench: bench,
	Marketplace: marketplace,
	Server: server,
	DatabaseServer: databaseServer
};

export function getObject(name) {
	return objects[name];
}

export default objects;
