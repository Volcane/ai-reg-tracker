// SPDX-License-Identifier: Elastic-2.0
// Copyright (c) 2026 Mitch Kwiatkowski
// ARIS — Automated Regulatory Intelligence System
// Licensed under the Elastic License 2.0. See LICENSE in the project root.
import { defineConfig } from 'vite'
import react from '@vitejs/plugin-react'

export default defineConfig({
  plugins: [react()],
  server: {
    proxy: {
      '/api': 'http://localhost:8000',
    },
  },
  build: {
    outDir: 'dist',
  },
})
