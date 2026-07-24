<template>
  <div class="trend">
    <el-card>
      <template #header>
        <div class="card-header">
          <span>趋势分析</span>
        </div>
      </template>

      <el-form :inline="true" style="margin-bottom: 20px;">
        <el-form-item label="检验项目">
          <el-select
            v-model="selectedItems"
            multiple
            filterable
            remote
            reserve-keyword
            placeholder="请搜索并选择检验项目"
            :remote-method="remoteSearch"
            :loading="loading"
            style="width: 400px;"
          >
            <el-option
              v-for="item in items"
              :key="item.item_id"
              :label="`${item.item_name}${item.abbr ? ' (' + item.abbr + ')' : ''}`"
              :value="item.item_id"
            />
          </el-select>
        </el-form-item>
        <el-form-item>
          <el-button type="primary" @click="loadTrend" :disabled="selectedItems.length === 0">
            查看趋势
          </el-button>
          <el-button @click="clearSelection" style="margin-left: 10px;">
            清空选择
          </el-button>
        </el-form-item>
      </el-form>

      <div v-if="trendData && trendData.length > 0" ref="chartRef" style="height: 600px;"></div>
      <el-empty v-else description="请选择检验项目查看趋势" />
    </el-card>
  </div>
</template>

<script setup lang="ts">
import { ref, onMounted, nextTick, onUnmounted } from 'vue'
import * as echarts from 'echarts'
import { trendApi, type TrendItem, type TrendAnalysisResponse } from '@/api'
import { ElMessage, ElMessageBox } from 'element-plus'
import { useRouter } from 'vue-router'

const router = useRouter()
const items = ref<TrendItem[]>([])
const selectedItems = ref<number[]>([])
const trendData = ref<TrendAnalysisResponse[]>([])
const chartRef = ref<HTMLElement>()
const loading = ref(false)
let chart: echarts.ECharts | null = null

const colorPalette = [
  '#409EFF', '#67C23A', '#E6A23C', '#F56C6C', '#909399',
  '#7232DD', '#3B82F6', '#EC4899', '#10B981', '#F97316'
]

const loadItems = async (keyword?: string) => {
  try {
    loading.value = true
    const res = await trendApi.getItems(keyword)
    items.value = res.data
  } catch (error) {
    ElMessage.error('加载失败')
    console.error(error)
  } finally {
    loading.value = false
  }
}

const remoteSearch = (keyword: string) => {
  loadItems(keyword)
}

const clearSelection = () => {
  selectedItems.value = []
  trendData.value = []
  if (chart) {
    chart.dispose()
    chart = null
  }
}

const loadTrend = async () => {
  if (selectedItems.value.length === 0) return
  try {
    const res = await trendApi.getAnalysis(selectedItems.value)
    trendData.value = res.data
    await nextTick()
    renderChart()
  } catch (error) {
    ElMessage.error('加载失败')
    console.error(error)
  }
}

const renderChart = () => {
  if (!chartRef.value || !trendData.value || trendData.value.length === 0) return
  
  if (chart) {
    chart.dispose()
  }
  
  chart = echarts.init(chartRef.value)
  
  const series = trendData.value.map((item, index) => ({
    name: `${item.item_name}${item.abbr ? ' (' + item.abbr + ')' : ''}`,
    type: 'line',
    data: item.data.map(d => ({
      value: d.value,
      report_id: d.report_id,
      time: d.time,
      hospital: d.hospital,
      flag: d.flag
    })),
    smooth: true,
    symbol: 'circle',
    symbolSize: 8,
    markPoint: {
      data: [
        { type: 'max', name: '最大值' },
        { type: 'min', name: '最小值' }
      ]
    },
    lineStyle: {
      color: colorPalette[index % colorPalette.length],
      width: 2
    },
    itemStyle: {
      color: colorPalette[index % colorPalette.length]
    },
    emphasis: {
      focus: 'series',
      itemStyle: {
        borderWidth: 2,
        borderColor: '#fff'
      }
    }
  }))

  const allDates = new Set<string>()
  trendData.value.forEach(item => {
    item.data.forEach(d => {
      allDates.add(d.time.split('T')[0])
    })
  })

  const option: echarts.EChartsOption = {
    title: {
      text: '检验指标趋势图',
      left: 'center',
      textStyle: {
        fontSize: 16,
        fontWeight: 'bold'
      }
    },
    tooltip: {
      trigger: 'item',
      formatter: (params: any) => {
        const data = params.data
        if (!data) return ''
        let html = `<div style="font-weight:bold;margin-bottom:8px;">${params.seriesName}</div>`
        html += `<div>日期：${data.time ? data.time.split('T')[0] : '-'}</div>`
        html += `<div>数值：${data.value !== undefined ? data.value : '-'}</div>`
        if (data.hospital) {
          html += `<div>医院：${data.hospital}</div>`
        }
        if (data.flag) {
          html += `<div>标记：<span style="color:red;">${data.flag}</span></div>`
        }
        if (data.report_id) {
          html += `<div style="margin-top:8px;color:#409EFF;cursor:pointer;" onclick="window.open('/review/${data.report_id}', '_blank')">点击查看报告</div>`
        }
        return html
      }
    },
    legend: {
      data: trendData.value.map(item => `${item.item_name}${item.abbr ? ' (' + item.abbr + ')' : ''}`),
      bottom: 10,
      itemWidth: 20,
      itemHeight: 10
    },
    grid: {
      left: '3%',
      right: '4%',
      bottom: '15%',
      top: '15%',
      containLabel: true
    },
    xAxis: {
      type: 'category',
      boundaryGap: false,
      data: Array.from(allDates).sort(),
      axisLine: {
        lineStyle: {
          color: '#ccc'
        }
      },
      axisLabel: {
        color: '#666',
        rotate: 45,
        fontSize: 12
      },
      splitLine: {
        show: true,
        lineStyle: {
          color: '#eee',
          type: 'dashed'
        }
      }
    },
    yAxis: {
      type: 'value',
      axisLine: {
        show: true,
        lineStyle: {
          color: '#ccc'
        }
      },
      axisLabel: {
        color: '#666',
        fontSize: 12
      },
      splitLine: {
        show: true,
        lineStyle: {
          color: '#eee',
          type: 'dashed'
        }
      }
    },
    dataZoom: [
      {
        type: 'inside',
        start: 0,
        end: 100,
        zoomLock: false
      },
      {
        type: 'slider',
        start: 0,
        end: 100,
        height: 20,
        bottom: 40,
        borderColor: '#ddd',
        fillerColor: 'rgba(64, 158, 255, 0.2)',
        handleStyle: {
          color: '#409EFF'
        },
        textStyle: {
          color: '#666'
        }
      }
    ],
    toolbox: {
      feature: {
        zoom: {
          title: {
            zoom: '区域缩放',
            back: '重置缩放'
          }
        },
        dataZoom: {
          title: {
            dataZoom: '数据缩放',
            dataZoomReset: '重置缩放'
          },
          yAxisIndex: 'none'
        },
        restore: {
          title: '重置'
        },
        saveAsImage: {
          title: '保存图片'
        }
      },
      right: 20,
      top: 20
    },
    series
  }
  
  chart.setOption(option)

  chart.on('click', (params: any) => {
    const data = params.data
    if (data && data.report_id) {
      ElMessageBox.confirm(
        `确定要跳转到报告审核页面查看该数据点吗？\n日期：${data.time ? data.time.split('T')[0] : '-'}\n数值：${data.value !== undefined ? data.value : '-'}`,
        '提示',
        {
          confirmButtonText: '确定',
          cancelButtonText: '取消',
          type: 'info'
        }
      ).then(() => {
        router.push(`/review/${data.report_id}`)
      }).catch(() => {
        ElMessage.info('已取消跳转')
      })
    }
  })
}

const handleResize = () => {
  if (chart) {
    chart.resize()
  }
}

onMounted(() => {
  loadItems()
  window.addEventListener('resize', handleResize)
})

onUnmounted(() => {
  window.removeEventListener('resize', handleResize)
  if (chart) {
    chart.dispose()
    chart = null
  }
})
</script>

<style scoped>
.card-header {
  display: flex;
  justify-content: space-between;
  align-items: center;
}
</style>
