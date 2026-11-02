/**
 * Vite plugin for VitePress that converts standalone GitHub permalink links
 * in Markdown files into embedded code blocks fetched at build time.
 *
 * Supported Markdown syntax (link must be the only content on its line):
 *
 *   [Label](https://github.com/owner/repo/blob/<ref>/path/to/file.py#L10-L20)
 *
 * The plugin fetches the file content from GitHub's raw content endpoint,
 * extracts the specified line range, and replaces the link with a fenced
 * code block and a small "View on GitHub" caption.
 */

import type { Plugin } from 'vite';

// ---------------------------------------------------------------------------
// Helpers
// ---------------------------------------------------------------------------

/** Matches a Markdown line that is _only_ a link: `[text](url)` */
const LINK_LINE_RE =
	/^\[([^\]]+)\]\((https:\/\/github\.com\/[^)]+)\)\s*$/gm;

/** Parses a GitHub blob URL */
const GITHUB_BLOB_RE =
	/^https:\/\/github\.com\/([^/]+)\/([^/]+)\/blob\/([^/]+)\/(.+?)(?:#L(\d+)(?:-L(\d+))?)?$/;

interface ParsedGitHubURL {
	owner: string;
	repo: string;
	ref: string;
	filepath: string;
	startLine?: number;
	endLine?: number;
	url: string;
}

function parseGitHubURL(url: string): ParsedGitHubURL | null {
	const m = url.match(GITHUB_BLOB_RE);
	if (!m) return null;
	return {
		owner: m[1],
		repo: m[2],
		ref: m[3],
		filepath: m[4],
		startLine: m[5] ? parseInt(m[5], 10) : undefined,
		endLine: m[6] ? parseInt(m[6], 10) : undefined,
		url,
	};
}

function langFromPath(filepath: string): string {
	const ext = filepath.split('.').pop()?.toLowerCase() ?? '';
	const map: Record<string, string> = {
		py: 'python',
		js: 'javascript',
		ts: 'typescript',
		jsx: 'jsx',
		tsx: 'tsx',
		rb: 'ruby',
		rs: 'rust',
		go: 'go',
		java: 'java',
		sh: 'shell',
		bash: 'bash',
		yml: 'yaml',
		yaml: 'yaml',
		json: 'json',
		toml: 'toml',
		md: 'markdown',
		css: 'css',
		html: 'html',
		xml: 'xml',
		sql: 'sql',
		lua: 'lua',
		vim: 'vim',
		c: 'c',
		cpp: 'cpp',
		h: 'c',
		hpp: 'cpp',
	};
	return map[ext] || ext;
}

// Simple in-memory cache keyed by raw URL to avoid duplicate network requests
const fileCache = new Map<string, string>();

function dedent(text: string): string {
	// Strip leading and trailing blank lines
	const trimmed = text.replace(/^\n+/, '').replace(/\n+$/, '');
	const lines = trimmed.split('\n');

	// Use the first non-empty line's indentation as the dedent amount
	const first = lines.find((l) => l.trim().length > 0);
	if (!first) return trimmed;
	const m = first.match(/^(\t+| +)/);
	if (!m) return trimmed;
	const prefix = m[1];

	return lines
		.map((l) => (l.startsWith(prefix) ? l.slice(prefix.length) : l))
		.join('\n');
}

async function fetchFileContent(parsed: ParsedGitHubURL): Promise<string> {
	const rawURL = `https://raw.githubusercontent.com/${parsed.owner}/${parsed.repo}/${parsed.ref}/${parsed.filepath}`;

	let content = fileCache.get(rawURL);
	if (content === undefined) {
		const resp = await fetch(rawURL);
		if (!resp.ok) {
			return `// Failed to fetch ${rawURL} (HTTP ${resp.status})`;
		}
		content = await resp.text();
		fileCache.set(rawURL, content);
	}

	const lines = content.split('\n');

	if (parsed.startLine !== undefined) {
		const start = parsed.startLine - 1; // 0-indexed
		const end = parsed.endLine ?? parsed.startLine;
		return dedent(lines.slice(start, end).join('\n'));
	}

	return content;
}

// ---------------------------------------------------------------------------
// Plugin
// ---------------------------------------------------------------------------

export function githubCodeEmbed(): Plugin {
	return {
		name: 'vitepress-github-code-embed',
		enforce: 'pre',

		async transform(code, id) {
			// Only process Markdown files
			if (!id.endsWith('.md')) return null;

			// Quick check – bail out early if there are no GitHub links
			if (!code.includes('github.com')) return null;

			// Find all standalone GitHub link lines
			const matches: {
				fullMatch: string;
				label: string;
				url: string;
				parsed: ParsedGitHubURL;
			}[] = [];

			let m: RegExpExecArray | null;
			// Reset lastIndex since we reuse the regex
			LINK_LINE_RE.lastIndex = 0;
			while ((m = LINK_LINE_RE.exec(code)) !== null) {
				const parsed = parseGitHubURL(m[2]);
				if (parsed) {
					matches.push({
						fullMatch: m[0],
						label: m[1],
						url: m[2],
						parsed,
					});
				}
			}

			if (matches.length === 0) return null;

			// Fetch all snippets in parallel
			const snippets = await Promise.all(
				matches.map((match) => fetchFileContent(match.parsed)),
			);

			// Replace each link with the embedded code block
			let result = code;
			for (let i = 0; i < matches.length; i++) {
				const match = matches[i];
				const snippet = snippets[i];
				const lang = langFromPath(match.parsed.filepath);
				const fileName = match.parsed.filepath.split('/').pop();

				const lineInfo =
					match.parsed.startLine !== undefined
						? match.parsed.endLine
							? `#L${match.parsed.startLine}-L${match.parsed.endLine}`
							: `#L${match.parsed.startLine}`
						: '';

				const replacement =
					`<small><a href="${match.url}" target="_blank" rel="noopener noreferrer">${match.label} — <code>${fileName}${lineInfo}</code> ↗</a></small>\n\n` +
					`\`\`\`${lang}\n${snippet}\n\`\`\``;

				result = result.replace(match.fullMatch, replacement);
			}

			return result;
		},
	};
}
