<template>
    <div ref="chartDiv" v-show="!error" class="h-full w-full min-w-[300px] md:min-w-[400px] min-h-[300px]"></div>
    <div v-show="error" class="flex h-full w-full items-center justify-center text-center text-red-500">
        Error: {{ error }}
    </div>
</template>

<script setup>
import { init } from 'echarts';
import {
    computed,
    ref,
    onMounted,
    onBeforeUnmount,
    watch,
    nextTick,
} from 'vue';
import useAxisChartOptions from 'frappe-ui/src/components/Charts/axisChartOptions';

const props = defineProps({
    data: {
        type: Array,
        required: true,
    },
    onZoomEvent: {
        type: Function,
        required: false,
    },
});

const error = ref('');
const options = computed(() => {
    try {
        return useAxisChartOptions({
            data: props.data,
            xAxis: {
                key: 'timestamp',
                type: 'time',
                title: 'Day',
                timeGrain: 'minute',
            },
            yAxis: {
                title: 'Count',
            },
            stacked: true,
            series: [
                { name: 'INSERT', type: 'bar' },
                { name: 'UPDATE', type: 'bar' },
                { name: 'DELETE', type: 'bar' },
                { name: 'SELECT', type: 'bar' },
                { name: 'OTHER', type: 'bar' },
            ],
            echartOptions: {
                legend: { show: true },
                toolbox: {
                    show: true,

                    feature: {
                        dataZoom: {
                            show: true,
                            yAxisIndex: 'none',
                            title: {
                                zoom: 'Zoom',
                            },
                            icon: {
                                zoom: 'image://data:image/svg+xml;base64,PHN2ZyB4bWxucz0iaHR0cDovL3d3dy53My5vcmcvMjAwMC9zdmciIHdpZHRoPSIyNCIgaGVpZ2h0PSIyNCIgdmlld0JveD0iMCAwIDI0IDI0IiBmaWxsPSJub25lIiBzdHJva2U9IiMwMDAwMDAiIHN0cm9rZS13aWR0aD0iMiIgc3Ryb2tlLWxpbmVjYXA9InJvdW5kIiBzdHJva2UtbGluZWpvaW49InJvdW5kIiBjbGFzcz0ibHVjaWRlIGx1Y2lkZS16b29tLWluLWljb24gbHVjaWRlLXpvb20taW4iPjxjaXJjbGUgY3g9IjExIiBjeT0iMTEiIHI9IjgiLz48bGluZSB4MT0iMjEiIHgyPSIxNi42NSIgeTE9IjIxIiB5Mj0iMTYuNjUiLz48bGluZSB4MT0iMTEiIHgyPSIxMSIgeTE9IjgiIHkyPSIxNCIvPjxsaW5lIHgxPSI4IiB4Mj0iMTQiIHkxPSIxMSIgeTI9IjExIi8+PC9zdmc+',
                                back: 'none',
                            },
                        },
                        restore: {
                            show: false, // This hides the reset/restore button
                        },
                    },
                }
            },
        });
    } catch (e) {
        error.value = e.message;
        return {};
    }
});

let chart;
const chartDiv = ref();

function debounce(func, wait) {
    let timeout;
    return function executedFunction(...args) {
        const later = () => {
            clearTimeout(timeout);
            func(...args);
        };
        clearTimeout(timeout);
        timeout = setTimeout(later, wait);
    };
}

function onZoomEventHandler(event) {
    if (!props.onZoomEvent) return;
    if (!props.data || props.data.length < 2) return;

    const info = event.batch?.[0] || event;

    let startValue, endValue;

    if ('startValue' in info) {
        startValue = info.startValue;
        endValue = info.endValue;
    } else {
        const data = props.data;
        const len = data.length;

        const startIndex = Math.floor((info.start / 100) * (len - 1));
        const endIndex = Math.floor((info.end / 100) * (len - 1));

        startValue = data[startIndex].timestamp;
        endValue = data[endIndex].timestamp;
    }

    // Find actual matching data entries
    const data = props.data;
    const startItem = data.find((d) => d.timestamp >= startValue) || data[0];
    const endItem =
        data.find((d) => d.timestamp >= endValue) || data[data.length - 1];

    props.onZoomEvent(startItem, endItem);
}

const onZoomEventHandlerDebounced = debounce(onZoomEventHandler, 1000);

function enableDataZoomSelectAutomatically() {
    if (!chart) return;

    const zr = chart.getZr();
    zr.on('mousemove', function handler() {
        chart.dispatchAction({
            type: 'takeGlobalCursor',
            key: 'dataZoomSelect',
            dataZoomSelectActive: true,
        });
        zr.off('mousemove', handler); // Remove after trigerring the event
    });
}

onMounted(() => {
    if (!chartDiv.value) return;

    chart = init(chartDiv.value, 'light', { renderer: 'svg' });
    chart.setOption({ ...options.value }, true);

    nextTick(() => {
        enableDataZoomSelectAutomatically();
    });

    chart.on('datazoom', function (zoom) {
        onZoomEventHandlerDebounced(zoom);
    });

    const resizeDebounce = debounce(() => {
        chart.resize({
            animation: {
                duration: 300,
            },
        });
    }, 250);

    let resizeObserver = new ResizeObserver(resizeDebounce);
    setTimeout(() => resizeObserver.observe(chartDiv.value), 500);
    onBeforeUnmount(() => resizeObserver.unobserve(chartDiv.value));
});

watch(
    () => options.value,
    (newOptions) => {
        if (chart) {
            chart.setOption(newOptions, true);
            enableDataZoomSelectAutomatically();
        }
    },
    { deep: true },
);
</script>
