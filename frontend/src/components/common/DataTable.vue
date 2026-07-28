<template>
  <div class="data-table-wrapper">
    <table class="data-table">
      <thead>
        <tr>
          <th v-for="col in columns" :key="col.key" :style="{ width: col.width }">
            {{ col.label }}
          </th>
        </tr>
      </thead>
      <tbody>
        <tr v-for="(row, i) in data" :key="i">
          <td v-for="col in columns" :key="col.key">
            <slot :name="'cell-' + col.key" :row="row" :value="row[col.key]">
              {{ formatValue(row[col.key]) }}
            </slot>
          </td>
        </tr>
        <tr v-if="data.length === 0">
          <td :colspan="columns.length" class="empty">{{ emptyText }}</td>
        </tr>
      </tbody>
    </table>
  </div>
</template>

<script setup lang="ts">
defineProps<{
  columns: { key: string; label: string; width?: string }[]
  data: Record<string, any>[]
  emptyText?: string
}>()

function formatValue(val: any): string {
  if (val === null || val === undefined) return '—'
  if (typeof val === 'boolean') return val ? '是' : '否'
  if (typeof val === 'number') return Number.isInteger(val) ? val.toString() : val.toFixed(4)
  return String(val)
}
</script>

<style scoped>
.data-table-wrapper { overflow-x: auto; }
.data-table { width: 100%; border-collapse: collapse; font-size: 13px; }
.data-table th { text-align: left; padding: 10px 12px; color: var(--text-muted); font-weight: 600; border-bottom: 1px solid var(--glass-border); font-size: 11px; text-transform: uppercase; white-space: nowrap; }
.data-table td { padding: 8px 12px; border-bottom: 1px solid rgba(255,255,255,0.03); }
.data-table tr:hover { background: var(--glass-bg); }
.empty { text-align: center; color: var(--text-muted); padding: 32px; }
</style>
