import { visit, EXIT } from 'unist-util-visit';

export const urlToVidTag = () => (tree) => {
	visit(tree, 'paragraph', (node, index, parent) => {
		if (!node.children || node.children.length !== 1) return;

		const child = node.children[0];

		if (child.type !== 'link') return;

		const url = child.url;

		if (child.url.startsWith('https://github.com/user-attachments/assets/')) {
			parent.children[index] = {
				type: 'html',
				value: `<video src="${url}" controls playsinline muted width="100%"></video>`,
			};
		}
	});
};

export const rehypeFirstH1Link = () => {
	return (tree, file) => {
		const id = file.history[0]
			?.split('/')
			.pop()
			?.replace(/\.mdx?$/, '');

		if (!id) return;

		visit(tree, 'element', (node) => {
			if (node.tagName === 'h2') {
				node.children = [
					{
						type: 'element',
						tagName: 'a',
						properties: {
							href: `/releases/version/${id}`,
							class: 'no-underline font-semibold',
						},
						children: node.children,
					},
				];
				return EXIT;
			}
		});
	};
};

export const getFileFromRoute = (str: string) => {
	const filename = str?.split('/')?.pop()?.replace('.md', '');
	return filename?.replace('_', '.');
};
