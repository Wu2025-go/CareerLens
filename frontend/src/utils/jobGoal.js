export const createGoal = (input) => ({
  city: input?.city ?? '',
  job_category: input?.job_category ?? '',
  recruitment_type: input?.recruitment_type ?? '',
  keyword: input?.keyword ?? '',
  education: input?.education ?? '',
  min_salary: input?.min_salary ?? '',
  expand_city: Boolean(input?.expand_city),
})

export const buildGoal = (form, skills) => {
  const salary = form.min_salary === '' || form.min_salary == null ? null : Number(form.min_salary)
  if (salary !== null && (!Number.isFinite(salary) || salary < 0)) {
    throw new Error('最低月薪请输入 0 或正数，单位为 K。')
  }
  const unique = [...new Set(skills.map(skill => skill.trim()).filter(Boolean))]
  if (unique.length > 40 || unique.some(skill => skill.length > 80)) {
    throw new Error('最多填写 40 项技能，每项不超过 80 个字符。')
  }
  return {
    city: form.city || null,
    job_category: form.job_category || null,
    recruitment_type: form.recruitment_type || null,
    keyword: form.keyword?.trim() || null,
    education: form.education || null,
    min_salary: salary || null,
    expand_city: Boolean(form.expand_city),
    skills: unique,
  }
}

export const describeGoal = (goal = {}) => [
  goal.city || '全部城市',
  goal.job_category,
  goal.recruitment_type,
  goal.keyword && `关键词：${goal.keyword}`,
  goal.education && `我的学历：${goal.education}`,
  goal.min_salary && `最低月薪：${goal.min_salary}K`,
].filter(Boolean).join(' · ')

export const splitEnteredSkills = (value) => value.split(/[，,、;；|\n]+/).map(item => item.trim()).filter(Boolean)

export async function postJobGoal(path, data, signal) {
  const response = await fetch(path, {
    method: 'POST',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify(data),
    signal,
  })
  const result = await response.json().catch(() => null)
  if (!response.ok || !result) {
    throw new Error(typeof result?.detail === 'string' ? result.detail : '请求失败，请核对输入条件后重试。')
  }
  return result
}
