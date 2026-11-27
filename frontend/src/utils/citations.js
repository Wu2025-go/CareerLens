// 正文按岗位展示一个入口，完整的不同摘录仍保留在引用详情中。
export function citationLinks(citations) {
  const links = new Map()
  for (const citation of Array.isArray(citations) ? citations : []) {
    if (typeof citation?.job_id !== 'string' || !citation.job_id.trim()) continue
    const id = citation.job_id.trim()
    if (!links.has(id)) links.set(id, { job_id: id, quotes: [] })
    const quote = typeof citation.quote === 'string' ? citation.quote.trim() : ''
    const item = links.get(id)
    if (quote && !item.quotes.includes(quote)) item.quotes.push(quote)
  }
  return [...links.values()]
}
