import React from 'react';
import ReactMarkdown from 'react-markdown';
import remarkGfm from 'remark-gfm';
import { Prism as SyntaxHighlighter } from 'react-syntax-highlighter';
import { oneDark } from 'react-syntax-highlighter/dist/cjs/styles/prism';
import type { Components } from 'react-markdown';

interface MessageMarkdownProps {
  content: string;
}

export const MessageMarkdown: React.FC<MessageMarkdownProps> = ({ content }) => {
  const components: Components = {
    code({ node, className, children, ...props }) {
      const match = /language-(\w+)/.exec(className || '');
      const inline = !match;

      if (!inline && match) {
        const CodeComponent = SyntaxHighlighter as any;
        return (
          <CodeComponent
            style={oneDark}
            language={match[1]}
            PreTag="div"
            className="rounded-lg !mt-2 !mb-2"
          >
            {String(children).replace(/\n$/, '')}
          </CodeComponent>
        );
      }

      return (
        <code
          className="bg-gray-100 dark:bg-gray-800 rounded px-1.5 py-0.5 text-sm font-mono"
          {...props}
        >
          {children}
        </code>
      );
    },
    a({ node, children, href, ...props }) {
      return (
        <a
          href={href}
          target="_blank"
          rel="noopener noreferrer"
          className="text-blue-600 dark:text-blue-400 hover:underline"
          {...props}
        >
          {children}
        </a>
      );
    },
    ul({ node, children, ...props }) {
      return (
        <ul className="list-disc list-inside space-y-1 my-2" {...props}>
          {children}
        </ul>
      );
    },
    ol({ node, children, ...props }) {
      return (
        <ol className="list-decimal list-inside space-y-1 my-2" {...props}>
          {children}
        </ol>
      );
    },
    p({ node, children, ...props }) {
      return (
        <p className="mb-2 last:mb-0" {...props}>
          {children}
        </p>
      );
    },
    h1({ node, children, ...props }) {
      return (
        <h1 className="text-2xl font-bold mt-4 mb-2" {...props}>
          {children}
        </h1>
      );
    },
    h2({ node, children, ...props }) {
      return (
        <h2 className="text-xl font-bold mt-3 mb-2" {...props}>
          {children}
        </h2>
      );
    },
    h3({ node, children, ...props }) {
      return (
        <h3 className="text-lg font-bold mt-2 mb-1" {...props}>
          {children}
        </h3>
      );
    },
    blockquote({ node, children, ...props }) {
      return (
        <blockquote
          className="border-l-4 border-gray-300 dark:border-gray-600 pl-4 italic my-2"
          {...props}
        >
          {children}
        </blockquote>
      );
    },
    table({ node, children, ...props }) {
      return (
        <div className="overflow-x-auto my-2">
          <table className="min-w-full divide-y divide-gray-200 dark:divide-gray-700" {...props}>
            {children}
          </table>
        </div>
      );
    },
    th({ node, children, ...props }) {
      return (
        <th
          className="px-4 py-2 bg-gray-100 dark:bg-gray-800 text-left text-sm font-semibold"
          {...props}
        >
          {children}
        </th>
      );
    },
    td({ node, children, ...props }) {
      return (
        <td className="px-4 py-2 text-sm border-t border-gray-200 dark:border-gray-700" {...props}>
          {children}
        </td>
      );
    },
  };

  return (
    <div className="prose prose-sm dark:prose-invert max-w-none">
      <ReactMarkdown remarkPlugins={[remarkGfm]} components={components}>
        {content}
      </ReactMarkdown>
    </div>
  );
};