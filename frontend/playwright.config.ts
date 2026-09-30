import {defineConfig} from '@playwright/test';
export default defineConfig({
 testDir:'./e2e',workers:1,timeout:60000,updateSnapshots:'none',
 expect:{timeout:10000},
 snapshotPathTemplate:'../references/ui/{arg}{ext}',
 webServer:{command:'bash -lc \'export PATH="$HOME/miniconda3/bin:$PATH"; conda run --no-capture-output -n patter-codex python ../scripts/e2e_server.py\'',
   url:'http://127.0.0.1:8765/health',reuseExistingServer:false,timeout:120000},
 use:{baseURL:'http://127.0.0.1:8765',viewport:{width:1536,height:1024},headless:true,locale:'en-US',timezoneId:'UTC',colorScheme:'light',reducedMotion:'reduce',
   trace:'retain-on-failure',
   launchOptions:{executablePath:process.env.PLAYWRIGHT_CHROMIUM_EXECUTABLE}},
 reporter:'list'
});
