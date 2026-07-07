import { defineConfig } from 'vitepress';
import { withSidebar } from 'vitepress-sidebar';
import { githubCodeEmbed } from './plugins/github-code-embed';

// https://vitepress.dev/reference/site-config
export default defineConfig(
	withSidebar(
		{
			title: 'Frappe Cloud Internals',
			description: 'Documentation for Frappe Cloud architecture and code.',
			base: '/press/',
			vite: {
				plugins: [githubCodeEmbed()],
			},
			themeConfig: {
				// https://vitepress.dev/reference/default-theme-config
				nav: [
					{ text: 'Cloud', link: 'https://cloud.frappe.io/' },
					{ text: 'Agent', link: 'https://github.com/frappe/agent/' },
				],
				socialLinks: [
					{ icon: 'github', link: 'https://github.com/frappe/press' },
				],
			},
		},
		{
			documentRootPath: '/docs',
			capitalizeFirst: true,
			useTitleFromFileHeading: true,
			useFolderLinkFromIndexFile: true,
			useFolderTitleFromIndexFile: true,
		}
	),
);
