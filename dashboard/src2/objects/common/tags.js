import { h, defineAsyncComponent } from 'vue';
import { confirmDialog, icon, renderDialog } from '../../utils/components';
import { toast } from 'vue-sonner';

export function tagTab() {
	return {
		label: 'Tags',
		icon: icon('tag'),
		route: 'tags',
		type: 'list',
		list: {
			doctype: 'Resource Tag',
			filters: documentResource => {
				return {
					parent: documentResource.name,
					parenttype: documentResource.doctype
				};
			},
			orderBy: 'creation desc',
			columns: [
				{
					label: 'Tag',
					fieldname: 'tag_name'
				}
			],
			primaryAction({ listResource: tags, documentResource }) {
				return {
					label: 'Add Tag',
					slots: {
						prefix: icon('plus')
					},
					onClick() {
						let AddTagDialog = defineAsyncComponent(() =>
							import('../../components/AddTagDialog.vue')
						);
						renderDialog(
							h(AddTagDialog, {
								doctype: documentResource.doctype,
								docname: documentResource.name,
								onAdded() {
									tags.reload();
								}
							})
						);
					}
				};
			},
			rowActions({ row, listResource: tags, documentResource }) {
				return [
					{
						label: 'Remove',
						onClick() {
							if (documentResource.removeTag.loading) return;
							confirmDialog({
								title: 'Remove Tag',
								message: `Are you sure you want to remove the tag <b>${row.tag_name}</b>?`,
								onSuccess({ hide }) {
									documentResource.removeTag.submit(
										{
											tag: row.tag_name
										},
										{
											onSuccess() {
												tags.reload();
												hide();
											}
										}
									);
									toast.promise(documentResource.removeTag.promise, {
										loading: 'Removing tag...',
										success: () => `Tag ${row.tag_name} removed`,
										error: e => {
											return e.messages.length
												? e.messages.join('\n')
												: e.message;
										}
									});
								}
							});
						}
					}
				];
			}
		}
	};
}
