<template>
  <svg :width="size" :height="size" viewBox="0 0 24 24" fill="none" aria-hidden="true" focusable="false">
    <path
      v-for="(d, i) in paths"
      :key="'p' + i"
      :d="d"
      stroke="currentColor"
      :stroke-width="strokeWidth"
      stroke-linecap="round"
      stroke-linejoin="round"
    />
    <circle
      v-for="(c, i) in circles"
      :key="'c' + i"
      :cx="c[0]"
      :cy="c[1]"
      :r="c[2]"
      stroke="currentColor"
      :stroke-width="strokeWidth"
      fill="none"
    />
  </svg>
</template>

<script setup>
import { computed } from 'vue'

const props = defineProps({
  name: { type: String, required: true },
  size: { type: [Number, String], default: 20 },
  strokeWidth: { type: [Number, String], default: 1.8 }
})

// 极简线性图标集：只保留项目用得到的形状，避免引入整包图标库
const ICONS = {
  book: {
    paths: ['M4.5 6.5A2.5 2.5 0 0 1 7 4H20v16H7A2.5 2.5 0 0 1 4.5 17.5z', 'M4.5 6.5v11', 'M8.5 8.5h7.5', 'M8.5 12h5.5'],
    circles: []
  },
  sparkles: {
    paths: [
      'M12 3.8l1.7 4.6 4.6 1.7-4.6 1.7L12 16.4l-1.7-4.6L5.7 10.1l4.6-1.7z',
      'M18.4 15.2l.8 2.1 2.1.8-2.1.8-.8-2.1-2.1-.8z'
    ],
    circles: []
  },
  cart: {
    paths: ['M3.5 4.5h2.6l2.2 9.6h9.7', 'M7.6 14.1h9.9l1.9-6.4H6.2'],
    circles: [[10.2, 18.6, 1.4], [17.4, 18.6, 1.4]]
  },
  receipt: {
    paths: [
      'M6.5 3.5h11V20l-2.75-1.6-2.75 1.6-2.75-1.6L6.5 20z',
      'M9.5 8h5',
      'M9.5 11.5h5'
    ],
    circles: []
  },
  search: {
    paths: ['M15.6 15.6L20 20'],
    circles: [[10.6, 10.6, 6.2]]
  },
  plus: { paths: ['M12 6.5v11', 'M6.5 12h11'], circles: [] },
  user: {
    paths: ['M5.2 19.6c0-3.6 3-5.8 6.8-5.8s6.8 2.2 6.8 5.8'],
    circles: [[12, 8.2, 3.4]]
  },
  arrow: { paths: ['M5 12h13.5', 'M13 6.2l5.8 5.8-5.8 5.8'], circles: [] },
  check: { paths: ['M5 12.4l4.6 4.6L19 7.2'], circles: [] },
  close: { paths: ['M6.4 6.4l11.2 11.2', 'M17.6 6.4L6.4 17.6'], circles: [] },
  star: {
    paths: ['M12 3.8l2.4 5 5.5.8-4 3.9 1 5.5-5 4.9-5-.9 1-5.5-4-3.9 5.5-.8z'],
    circles: []
  },
  truck: {
    paths: ['M3.5 7.2h9.6v9H3.5z', 'M13.1 10.4h3.3l2.9 2.9v2.9h-6.2z'],
    circles: [[7.4, 18.4, 1.4], [17.3, 18.4, 1.4]]
  },
  refresh: {
    paths: ['M19.6 12a7.6 7.6 0 1 1-2.3-5.4', 'M19.6 4.4v4h-4'],
    circles: []
  },
  clock: {
    paths: ['M12 7.4V12l3.2 2'],
    circles: [[12, 12, 8]]
  },
  tag: {
    paths: ['M4.6 9.4V5.2a.6.6 0 0 1 .6-.6h4.2L20 15.2 15.2 20z'],
    circles: [[8.4, 8.4, 1.4]]
  },
  key: {
    paths: ['M12.9 12.9L20 20', 'M16.3 16.3l2.1-2.1', 'M18.5 14.1l1.6-1.6'],
    circles: [[9.2, 9.2, 4.4]]
  },
  eye: {
    paths: ['M2.8 12s3.5-6.2 9.2-6.2S21.2 12 21.2 12s-3.5 6.2-9.2 6.2S2.8 12 2.8 12z'],
    circles: [[12, 12, 3]]
  },
  eyeOff: {
    paths: [
      'M3.4 3.4l17.2 17.2',
      'M10.2 6.2A9.8 9.8 0 0 1 12 6c5.7 0 9.2 6 9.2 6a16 16 0 0 1-3.4 4.1',
      'M6.4 7.6C4.2 9.3 2.8 12 2.8 12s3.5 6 9.2 6c1.5 0 2.8-.4 4-1'
    ],
    circles: []
  },
  camera: {
    paths: ['M3.4 9.2h3.3l1.6-2.4h7.4l1.6 2.4h3.3v9.6H3.4z'],
    circles: [[12, 13.7, 3.3]]
  },
  pencil: {
    paths: ['M4.4 19.6l.9-4.1L15.2 5.6l3.2 3.2L8.5 18.7z', 'M13.9 6.9l3.2 3.2'],
    circles: []
  },
  shield: {
    paths: ['M12 3.2l7.2 2.9v5.6c0 4.4-3 7.6-7.2 9.6-4.2-2-7.2-5.2-7.2-9.6V6.1z', 'M8.9 11.9l2.2 2.2 3.9-3.9'],
    circles: []
  },
  logout: {
    paths: ['M10 5.4H5.4v13.2H10', 'M14.4 8.2L18.6 12l-4.2 3.8', 'M9.2 12h9.2'],
    circles: []
  }
}

const paths = computed(() => (ICONS[props.name] || ICONS.book).paths)
const circles = computed(() => (ICONS[props.name] || ICONS.book).circles)
</script>
