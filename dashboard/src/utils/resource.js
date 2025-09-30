import { createDocumentResource, getCachedDocumentResource } from 'frappe-ui';

export function getDocResource(object) {
	let doc = getCachedDocumentResource(object.doctype, object.name);
	if (!doc) doc = createDocumentResource(object);
	return doc;
}
