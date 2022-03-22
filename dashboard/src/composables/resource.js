import { unref, reactive, getCurrentInstance } from 'vue';
import { Resource } from '@/resourceManager/ResourceManager';

export default function useResource(options) {
	const resourceOptions = unref(options);
	const _vm = getCurrentInstance();
	const resource = reactive(new Resource(_vm, resourceOptions));

	if (options.auto) {
		resource.reload();
	}

	return resource;
}
