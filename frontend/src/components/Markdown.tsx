function InlineText({ text }: { text: string }) {
  const parts = text.split(/(\*\*.*?\*\*|`.*?`|\[source:.*?\])/g)

  return (
    <>
      {parts.map((part, index) => {
        if (part.startsWith('**') && part.endsWith('**')) {
          return (
            <strong key={index} className="font-black text-inherit">
              {part.slice(2, -2)}
            </strong>
          )
        }
        if (part.startsWith('`') && part.endsWith('`')) {
          return (
            <code key={index} className="rounded-md bg-slate-200/70 px-1.5 py-0.5 text-[0.92em] font-bold text-slate-800">
              {part.slice(1, -1)}
            </code>
          )
        }
        if (part.startsWith('[source:')) {
          return (
            <span key={index} className="mx-1 rounded-full border border-blue-100 bg-blue-50 px-2 py-0.5 text-[11px] font-black text-blue-700">
              {part}
            </span>
          )
        }
        return <span key={index}>{part}</span>
      })}
    </>
  )
}

export default function Markdown({ text }: { text: string }) {
  const lines = text.split('\n')

  return (
    <div className="space-y-2 whitespace-pre-wrap break-words leading-7">
      {lines.map((line, index) => {
        const trimmed = line.trim()
        if (!trimmed) return <div key={index} className="h-1" />

        if (trimmed.startsWith('- ') || trimmed.startsWith('* ') || trimmed.startsWith('• ')) {
          return (
            <div key={index} className="flex gap-2">
              <span className="mt-[1px] shrink-0 text-slate-400">•</span>
              <p className="min-w-0">
                <InlineText text={trimmed.replace(/^[-*•]\s*/, '')} />
              </p>
            </div>
          )
        }

        return (
          <p key={index}>
            <InlineText text={trimmed} />
          </p>
        )
      })}
    </div>
  )
}
