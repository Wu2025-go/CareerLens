<script setup>
import { computed } from 'vue'
const props = defineProps({ result: { type: Object, required: true } })
const stats = computed(() => props.result.statistics)
const emit = defineEmits(['view-trends', 'recommend'])
const salary = value => value == null ? '暂无数据' : `${Number(value).toFixed(2)}K/月`
const maxMonth = computed(() => Math.max(1, ...stats.value.monthly_counts.map(item => item.count)))
</script>

<template>
  <section v-if="stats" class="statistics-panel" aria-label="筛选样本统计结果">
    <div class="metrics">
      <div><span>符合条件的样本</span><strong>{{ stats.job_count }} 条</strong></div>
      <div><span>薪资区间中点均值</span><strong>{{ salary(stats.avg_salary) }}</strong></div>
      <div><span>薪资区间中点中位数</span><strong>{{ salary(stats.median_salary) }}</strong></div>
    </div>
    <p>{{ stats.salary_method }} 有效薪资样本 {{ stats.salary_sample_count }} 条。</p>
    <p v-if="stats.intent === 'proportion'">分母 {{ stats.denominator_count }} 条，占比 {{ stats.share_percent == null ? '不可计算' : `${stats.share_percent}%` }}。{{ stats.denominator_note }}</p>
    <div v-if="stats.groups.length" class="table-wrap">
      <table><caption>相同条件下的城市样本对比</caption><thead><tr><th>城市</th><th>岗位数</th><th>参考均值</th><th>参考中位数</th></tr></thead>
        <tbody><tr v-for="group in stats.groups" :key="group.city"><td>{{ group.city }}</td><td>{{ group.job_count }}</td><td>{{ salary(group.avg_salary) }}</td><td>{{ salary(group.median_salary) }}</td></tr></tbody>
      </table>
    </div>
    <div v-if="stats.intent === 'trend'" class="months">
      <div v-for="item in stats.monthly_counts" :key="item.month"><span>{{ item.month }}</span><div class="track"><i :style="{ width: `${item.count / maxMonth * 100}%` }"></i></div><b>{{ item.count }}</b></div>
    </div>
    <details><summary>查看统计依据</summary>
      <p>全部 {{ stats.job_count }} 条命中记录参与计数；薪资只使用有效记录。预览前 {{ stats.evidence_ids.length }} 个岗位编号：{{ stats.evidence_ids.join('、') || '无' }}。</p>
      <p>范围：{{ result.dataset?.dataset_label }}；数据版本：{{ result.dataset?.dataset_version }}。本结果由程序计算，不是模型估算。</p>
    </details>
    <div v-if="!stats.compared_cities?.length" class="actions"><button type="button" @click="emit('view-trends', result.conditions)">查看相同条件的趋势图</button><button type="button" @click="emit('recommend', result.conditions)">查看对应岗位</button></div>
    <p v-else>如需查看单个城市的岗位，可在岗位推荐页选择该城市和相同岗位类别。</p>
  </section>
</template>

<style scoped>
.statistics-panel { background: white; padding: 24px; border-radius: 16px; margin: 16px 0; border: 1px solid #e2e8f0; }
.metrics { display: grid; grid-template-columns: repeat(3, minmax(0, 1fr)); gap: 18px; }
.metrics span { display: block; font-size: 12px; color: #64748b; margin-bottom: 8px; }.metrics strong { font-size: 22px; color: #4338ca; }
p, details { font-size: 13px; line-height: 1.8; color: #475569; overflow-wrap: anywhere; } summary { cursor: pointer; font-weight: 600; }
.table-wrap { overflow-x: auto; } table { border-collapse: collapse; width: 100%; margin: 16px 0; font-size: 13px; } caption { text-align: left; font-weight: 600; margin-bottom: 8px; }
th, td { padding: 10px; border-bottom: 1px solid #e2e8f0; text-align: left; } th { background: #f1f5f9; }
.months > div { display: flex; align-items: center; gap: 12px; margin: 8px 0; font-size: 12px; }.months span { width: 58px; }.track { flex: 1; background: #eef2ff; height: 12px; border-radius: 6px; }.track i { display: block; background: #6366f1; height: 100%; border-radius: inherit; }
.actions { display: flex; gap: 10px; flex-wrap: wrap; margin-top: 16px; } button { border: 1px solid #c7d2fe; background: #eef2ff; color: #4338ca; padding: 10px 14px; border-radius: 8px; cursor: pointer; }
@media (max-width: 650px) { .metrics { grid-template-columns: 1fr; }.statistics-panel { padding: 18px; } }
</style>
