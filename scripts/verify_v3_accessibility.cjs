// Run with the bundled Playwright runtime; no package/model installation required.
const fs = require('node:fs');
const path = require('node:path');
const assert = require('node:assert/strict');
const { chromium } = require(process.env.PLATEPLUS_PLAYWRIGHT || 'playwright');

(async () => {
  const output = path.resolve(process.env.PLATEPLUS_QA_OUTPUT || '.plateplus-demo/qa-w');
  fs.mkdirSync(output, { recursive: true });
  const browser = await chromium.launch({ headless: true, channel: process.env.PLATEPLUS_BROWSER_CHANNEL || 'msedge' });
  const results = [];
  const codes = ['LDP', 'AKLEH', 'NPE', 'GRAND_SAGA', 'SIMULATOR'];
  const names = ['LDP', 'AKLEH', 'NPE', 'Grand Saga', 'Simulator Toll Plaza'];
  const locations = codes.map((code, i) => ({ id: code, code, display_name: names[i], highway_or_route: code, status: 'operational', base_toll: 2, road_capacity: i === 4 ? 10 : 1000 }));
  for (const [width, height] of [[1280,720],[1366,768],[1920,1080],[1024,768],[390,844],[960,540]]) {
    const page = await browser.newPage({ viewport: { width, height }, reducedMotion: 'reduce' });
    const errors = [];
    page.on('pageerror', error => errors.push(error.message));
    let outcome = { status: 'accepted_for_vehicle_lookup', message: 'Synthetic Singaporean plate accepted for simulated payment.', plate_text: 'GBC6427R', plate_origin: 'singaporean', origin_reason: 'singaporean_supported_pattern', payment_status: 'successful', payment_amount: 22, payment_dynamic_toll_amount: 2, payment_foreign_vehicle_charge: 20 };
    await page.addInitScript(() => {
      sessionStorage.setItem('capstone-alpr.admin-session', JSON.stringify({access_token:'synthetic-ui-fixture',admin:{display_name:'Synthetic Demo Admin'}}));
      localStorage.setItem('plateplus.location.v1', 'all');
      // Synthetic browser video only; never request hardware or camera permission.
      Object.defineProperty(navigator.mediaDevices, 'getUserMedia', { value: async () => {
        const canvas = document.createElement('canvas'); canvas.width=320;canvas.height=180;
        const context=canvas.getContext('2d'); context.fillStyle='#162128';context.fillRect(0,0,320,180);
        context.fillStyle='#eff5f5';context.font='16px sans-serif';context.fillText('Synthetic UI camera fixture',24,90);
        return canvas.captureStream(1);
      }});
    });
    await page.route('**/api/**', async route => {
      const url = new URL(route.request().url());
      let data = [];
      if (url.pathname === '/api/locations') data = locations;
      else if (url.pathname === '/api/live/overview') {
        const telemetry = { measured_at:new Date().toISOString(), congestion_percentage:40, congestion_category:'moderate', vehicles_per_hour:400, average_speed_kmh:50, current_toll_price:3, base_toll_price:2, congestion_multiplier:1.5, camera_status:'available', system_status:'operational', active_crossings:4, road_capacity:10 };
        data = { generated_at:new Date().toISOString(), locations:locations.map(location=>({location,telemetry:{...telemetry,average_speed_kmh:location.code==='SIMULATOR'?null:50},telemetry_source:location.code==='SIMULATOR'?'webcam_alpr':'fallback'})),live:{traffic:telemetry,price:{amount:3}},metrics:{detections:0,transactions:0,successful_transactions:0,revenue:0,locations_online:5,locations_total:5,locations_reporting:5,severe_locations:0,cameras_offline:0},detections:{items:[]},transactions:{items:[]} };
      } else if (url.pathname.endsWith('/demo/feed')) data = {running:false};
      else if (url.pathname === '/api/webcam/images') data = outcome;
      else if (url.pathname === '/api/webcam/sessions') data = {session_id:'synthetic-ui-session',frame_interval_ms:100};
      else if (url.pathname.endsWith('/frames')) data = outcome;
      else if (route.request().method() === 'DELETE') { await route.fulfill({status:204}); return; }
      await route.fulfill({status:200,contentType:'application/json',body:JSON.stringify(data)});
    });
    await page.goto('http://127.0.0.1:5173/dashboard');
    await page.getByRole('heading', {name:'Network operations',exact:true}).waitFor();
    const markers = page.locator('.network-marker');
    assert.equal(await markers.count(), 5);
    const layout = await markers.evaluateAll(nodes => nodes.map(node => {
      const r=node.getBoundingClientRect(); const m=node.closest('.network-map').getBoundingClientRect();
      return {name:node.getAttribute('aria-label'),x:r.x,y:r.y,w:r.width,h:r.height,inside:r.left>=m.left&&r.right<=m.right&&r.top>=m.top&&r.bottom<=m.bottom};
    }));
    assert(layout.every(marker=>marker.inside), JSON.stringify(layout));
    assert(await page.evaluate(()=>document.documentElement.scrollWidth<=innerWidth), 'page horizontal overflow');
    const overlaps=[];
    for(let i=0;i<layout.length;i++) for(let j=i+1;j<layout.length;j++) {
      const a=layout[i],b=layout[j];
      if(a.x<b.x+b.w&&a.x+a.w>b.x&&a.y<b.y+b.h&&a.y+a.h>b.y) overlaps.push([a.name,b.name]);
    }
    assert.deepEqual(overlaps, [], 'map labels overlap');
    await page.locator('.network-map').screenshot({path:path.join(output,`map-${width}x${height}.png`)});
    // Keyboard alternative remains usable even if schematic text labels are compact.
    const selector=page.getByRole('button',{name:'Toll location',exact:true});
    await selector.focus(); await page.keyboard.press('Enter');
    await page.getByRole('listbox', {name:'Toll location',exact:true}).focus();
    await page.keyboard.press('End'); await page.keyboard.press('Enter');
    await page.getByRole('button',{name:'Open Camera',exact:true}).waitFor();
    await page.getByRole('button',{name:'Open Camera',exact:true}).click();
    const camera=page.getByRole('region',{name:'Laptop webcam ALPR'});
    await camera.waitFor();
    assert(await camera.evaluate(node=>node.getBoundingClientRect().height<=innerHeight), 'camera exceeds viewport');
    await page.getByRole('button',{name:'Start camera',exact:true}).click();
    await camera.getByText('Final simulated total',{exact:true}).waitFor();
    await camera.screenshot({path:path.join(output,`camera-${width}x${height}.png`)});
    assert(await camera.evaluate(node=>node.scrollWidth<=node.clientWidth), 'camera result horizontal overflow');
    await camera.focus(); await page.keyboard.press('End');
    const total = camera.getByText('RM22.00',{exact:true});
    // Focused overflow region supports browser-native keyboard scrolling.
    await page.waitForFunction(() => {
      const panel=document.querySelector('.camera-pip');
      return panel && panel.scrollTop + panel.clientHeight >= panel.scrollHeight - 2;
    });
    assert(await total.evaluate(node=>{const r=node.getBoundingClientRect();const c=node.closest('.camera-pip').getBoundingClientRect();return r.top>=c.top&&r.bottom<=c.bottom;}),'camera charge total is unreachable');
    await camera.screenshot({path:path.join(output,`camera-scrolled-${width}x${height}.png`)});
    await page.getByRole('button',{name:'Close camera',exact:true}).click();
    const upload=page.locator('input[type=file]');
    await upload.setInputFiles({name:'synthetic-plate.png',mimeType:'image/png',buffer:Buffer.from('iVBORw0KGgoAAAANSUhEUgAAAAEAAAABCAQAAAC1HAwCAAAAC0lEQVR42mP8/x8AAwMCAO+aNioAAAAASUVORK5CYII=','base64')});
    await page.getByRole('button',{name:'Process image',exact:true}).click();
    await page.locator('.upload-result').getByText('Final simulated total',{exact:true}).waitFor();
    assert.equal(await page.locator('.upload-result').getByText('RM22.00',{exact:true}).count(),1);
    await page.locator('.location-card').screenshot({path:path.join(output,`upload-${width}x${height}.png`)});
    outcome={status:'origin_rejected',message:'The recognized plate matches overlapping supported Malaysian and Singaporean patterns; no simulated deduction was made.',plate_text:'SLP1234A',plate_origin:'unknown'};
    await page.getByRole('button',{name:'Process image',exact:true}).click();
    await page.locator('.upload-result').getByText(outcome.message,{exact:true}).waitFor();
    const readable=await page.locator('.upload-preview span').evaluate(node=>({whiteSpace:getComputedStyle(node).whiteSpace,overflow:getComputedStyle(node).overflow,scrollWidth:node.scrollWidth,width:node.clientWidth}));
    assert.equal(readable.whiteSpace,'normal');
    assert(readable.scrollWidth<=readable.width+1);
    await page.locator('.location-card').screenshot({path:path.join(output,`rejected-${width}x${height}.png`)});
    assert.deepEqual(errors,[]);
    results.push({width,height,markers:layout.length,overlaps,readable,errors});
    await page.close();
  }
  fs.writeFileSync(path.join(output,'results.json'),JSON.stringify(results,null,2));
  console.log(JSON.stringify(results,null,2));
  await browser.close();
})().catch(error=>{console.error(error);process.exit(1);});
