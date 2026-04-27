import { visit } from 'unist-util-visit';

export const urlToVidTag = () => (tree) => {
  visit(tree, 'paragraph', (node, index, parent) => {
    if (!node.children || node.children.length !== 1) return;

    const child = node.children[0];

    if (child.type !== 'link') return;

    const url = child.url;

    if (child.url.startsWith('https://github.com/user-attachments/assets/')) {
      parent.children[index] = {
        type: 'html',
        value: `<video src="${url}" controls playsinline muted width="100%"></video>`
      };
    }
  });
};
