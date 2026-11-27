<script setup>
import { datasetScope, datasetInfo, datasetError, refreshDatasetInfo } from '../utils/dataset'
</script>

<template>
  <section class="dataset-controls" :class="{ simulation: datasetScope !== 'real' }" aria-label="数据范围与来源">
    <label>数据范围
      <select v-model="datasetScope">
        <option value="real">实采样本 · 正式分析</option>
        <option value="synthetic">仿真样本 · 功能测试</option>
        <option value="all">全部样本 · 混合测试</option>
      </select>
    </label>
    <div v-if="datasetInfo">
      <p>{{ datasetInfo.dataset_label }} {{ datasetInfo.sample_count.toLocaleString() }} 条
        <span v-if="datasetInfo.publish_date_end"> · 发布日期 {{ datasetInfo.publish_date_start }} 至 {{ datasetInfo.publish_date_end }}</span>
      </p>
      <small>{{ datasetInfo.notice }} 数据版本 {{ datasetInfo.dataset_version }}。</small>
    </div>
    <p v-if="datasetError" role="status">{{ datasetError }} <button type="button" @click="refreshDatasetInfo">重试</button></p>
  </section>
</template>

<style scoped>
.dataset-controls { display: flex; align-items: center; gap: 20px; padding: 13px 16px; margin-bottom: 22px; border: 1px solid #dce4ef; border-radius: 12px; background: #fff; color: #334155; }
label { display: grid; gap: 5px; flex-shrink: 0; font-size: 12px; font-weight: 600; }
select { padding: 8px; max-width: 100%; background: white; border: 1px solid #cbd5e1; border-radius: 6px; color: #1e293b; font: inherit; }
p { margin: 0 0 4px; font-size: 13px; } small { font-size: 11px; color: #64748b; line-height: 1.6; }
.simulation { background: #fff8ed; border-color: #e9be73; }
@media (max-width: 650px) { .dataset-controls { align-items: stretch; flex-direction: column; gap: 10px; } }
</style>
