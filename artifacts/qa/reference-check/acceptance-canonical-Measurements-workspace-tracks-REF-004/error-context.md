# Instructions

- Following Playwright test failed.
- Explain why, be concise, respect Playwright best practices.
- Provide a snippet of code with the fix, if possible.

# Test info

- Name: acceptance.spec.ts >> canonical Measurements workspace tracks REF-004
- Location: e2e/acceptance.spec.ts:14:1

# Error details

```
Error: expect(page).toHaveScreenshot(expected) failed

  119276 pixels (ratio 0.08 of all image pixels) are different.

  Snapshot: garment-pattern-maker-v5-ui-reference-1536x1024.png

Call log:
  - Expect "toHaveScreenshot(garment-pattern-maker-v5-ui-reference-1536x1024.png)" with timeout 10000ms
    - verifying given screenshot expectation
  - taking page screenshot
    - disabled all CSS animations
  - waiting for fonts to load...
  - fonts loaded
  - 119276 pixels (ratio 0.08 of all image pixels) are different.
  - waiting 100ms before taking screenshot
  - taking page screenshot
    - disabled all CSS animations
  - waiting for fonts to load...
  - fonts loaded
  - captured a stable screenshot
  - 119276 pixels (ratio 0.08 of all image pixels) are different.

```

# Page snapshot

```yaml
- generic [ref=e2]:
  - banner [ref=e3]:
    - generic [ref=e7]:
      - strong [ref=e8]: Garment Pattern Maker V5
      - generic [ref=e9]: From Measurements to Production-Ready Patterns
    - generic [ref=e10]:
      - generic [ref=e11]:
        - text: "Project:"
        - combobox "Project" [ref=e12]:
          - option "Select project" [disabled]
          - option "Men's Regular Fit Shirt (Demo)" [selected]
      - button "New project" [ref=e13] [cursor=pointer]
      - generic [ref=e15]:
        - button "Help" [ref=e16] [cursor=pointer]
        - button "Settings" [ref=e20] [cursor=pointer]
        - generic [ref=e24]: U
        - button "User" [ref=e25] [cursor=pointer]
  - complementary [ref=e28]:
    - navigation [ref=e29]:
      - button "1 Measurements" [ref=e30] [cursor=pointer]:
        - generic [ref=e37]: "1"
        - text: Measurements
      - button "2 Requirements" [ref=e38] [cursor=pointer]:
        - generic [ref=e43]: "2"
        - text: Requirements
      - button "3 Generate Pattern" [ref=e44] [cursor=pointer]:
        - generic [ref=e48]: "3"
        - text: Generate Pattern
      - button "4 Pattern Studio" [ref=e49] [cursor=pointer]:
        - generic [ref=e56]: "4"
        - text: Pattern Studio
      - button "5 Grading" [ref=e57] [cursor=pointer]:
        - generic [ref=e62]: "5"
        - text: Grading
      - button "6 Marker Nesting" [ref=e63] [cursor=pointer]:
        - generic [ref=e66]: "6"
        - text: Marker Nesting
      - button "7 Export" [ref=e67] [cursor=pointer]:
        - generic [ref=e71]: "7"
        - text: Export
    - generic [ref=e72]:
      - heading "V5 Demo" [level=2] [ref=e73]
      - paragraph [ref=e74]: Men’s Regular Fit Long Sleeve Shirt
      - generic [ref=e77]: Deterministic drafting
      - generic [ref=e80]: Configurable demo rules
      - generic [ref=e83]: Source provenance
      - generic [ref=e86]: Calibration required
    - generic [ref=e89]: v5.0.0
  - generic [ref=e90]:
    - button "1 Measurements Upload or enter measurements" [ref=e91] [cursor=pointer]:
      - generic [ref=e92]: "1"
      - generic [ref=e93]:
        - strong [ref=e94]: Measurements
        - generic [ref=e95]: Upload or enter measurements
    - button "2 Requirements Check missing information" [ref=e97] [cursor=pointer]:
      - generic [ref=e98]: "2"
      - generic [ref=e99]:
        - strong [ref=e100]: Requirements
        - generic [ref=e101]: Check missing information
    - button "3 Generate Pattern Create pattern pieces" [ref=e103] [cursor=pointer]:
      - generic [ref=e104]: "3"
      - generic [ref=e105]:
        - strong [ref=e106]: Generate Pattern
        - generic [ref=e107]: Create pattern pieces
    - button "4 Review & Edit Visualize and adjust" [ref=e109] [cursor=pointer]:
      - generic [ref=e110]: "4"
      - generic [ref=e111]:
        - strong [ref=e112]: Review & Edit
        - generic [ref=e113]: Visualize and adjust
    - button "5 Export Download files" [ref=e115] [cursor=pointer]:
      - generic [ref=e116]: "5"
      - generic [ref=e117]:
        - strong [ref=e118]: Export
        - generic [ref=e119]: Download files
  - main [ref=e120]:
    - generic [ref=e121]:
      - heading "Measurements" [level=2] [ref=e122]
      - paragraph [ref=e123]: Upload your measurement file or enter values manually
      - generic [ref=e124]:
        - button "Upload XLSX" [ref=e125] [cursor=pointer]
        - button "Manual Entry" [ref=e129] [cursor=pointer]
      - generic [ref=e133]: Size
      - generic [ref=e134]:
        - combobox "Size" [ref=e135]:
          - option "S"
          - option "M"
          - option "L" [selected]
          - option "XL"
          - option "XXL"
          - option "3XL"
        - button "View all sizes" [ref=e136] [cursor=pointer]
      - generic [ref=e137]:
        - strong [ref=e138]: Unit
        - generic [ref=e139]:
          - button "cm" [ref=e140] [cursor=pointer]
          - button "inch" [ref=e141] [cursor=pointer]
      - generic [ref=e142]:
        - generic [ref=e143]:
          - generic [ref=e144]: Chest circumference
          - spinbutton "Chest circumference" [ref=e145]: "116"
          - generic [ref=e146]: cm
        - generic [ref=e147]:
          - generic [ref=e148]: Waist circumference
          - spinbutton "Waist circumference" [ref=e149]: "112"
          - generic [ref=e150]: cm
        - generic [ref=e151]:
          - generic [ref=e152]: Hip circumference
          - spinbutton "Hip circumference" [ref=e153]: "114"
          - generic [ref=e154]: cm
        - generic [ref=e155]:
          - generic [ref=e156]: Shoulder width
          - spinbutton "Shoulder width" [ref=e157]: "48.5"
          - generic [ref=e158]: cm
        - generic [ref=e159]:
          - generic [ref=e160]: Armhole straight (half)
          - spinbutton "Armhole straight (half)" [ref=e161]: "24"
          - generic [ref=e162]: cm
        - generic [ref=e163]:
          - generic [ref=e164]: Sleeve length (incl. cuff)
          - spinbutton "Sleeve length (incl. cuff)" [ref=e165]: "66"
          - generic [ref=e166]: cm
        - generic [ref=e167]:
          - generic [ref=e168]: Bicep circumference
          - spinbutton "Bicep circumference" [ref=e169]: "43"
          - generic [ref=e170]: cm
        - generic [ref=e171]:
          - generic [ref=e172]: Cuff edge to edge
          - spinbutton "Cuff edge to edge" [ref=e173]: "25.5"
          - generic [ref=e174]: cm
        - generic [ref=e175]:
          - generic [ref=e176]: Neck width
          - spinbutton "Neck width" [ref=e177]: "15.5"
          - generic [ref=e178]: cm
        - generic [ref=e179]:
          - generic [ref=e180]: Collar height
          - spinbutton "Collar height" [ref=e181]: "4.7"
          - generic [ref=e182]: cm
        - generic [ref=e183]:
          - generic [ref=e184]: Front length
          - spinbutton "Front length" [ref=e185]: "77"
          - generic [ref=e186]: cm
        - generic [ref=e187]:
          - generic [ref=e188]: Back length
          - spinbutton "Back length" [ref=e189]: "77"
          - generic [ref=e190]: cm
      - generic [ref=e191]:
        - button "Reset" [ref=e192] [cursor=pointer]
        - button "Save Measurements" [ref=e193] [cursor=pointer]
      - generic [ref=e194]: 35 source measurements · cm confirmed
    - generic [ref=e196]:
      - generic [ref=e197]:
        - generic [ref=e198]:
          - generic [ref=e199]:
            - heading "Pattern Preview" [level=2] [ref=e200]
            - paragraph [ref=e201]: 2D pattern pieces generated from your measurements
          - generic [ref=e202]:
            - button "2D Pattern" [ref=e203] [cursor=pointer]
            - button "3D Preview" [disabled] [ref=e204]
            - button "Garment View" [disabled] [ref=e205]
        - generic [ref=e206]:
          - generic [ref=e207]:
            - status "Canvas status" [ref=e208]: No piece. Zoom 100%. Pan 0, 0.
            - group "2D shirt pattern canvas" [ref=e210]:
              - generic [ref=e211]:
                - button "Select Front" [ref=e212] [cursor=pointer]:
                  - generic: Front
                  - generic: Cut 2
                - button "Select Back" [ref=e215] [cursor=pointer]:
                  - generic: Back
                  - generic: Cut 1
                - button "Select Yoke" [ref=e218] [cursor=pointer]:
                  - generic: Yoke
                  - generic: Cut 1
                - button "Select Sleeve" [ref=e221] [cursor=pointer]:
                  - generic: Sleeve
                  - generic: Cut 2
                - button "Select Collar" [ref=e224] [cursor=pointer]:
                  - generic: Collar
                  - generic: Cut 2
                - button "Select Collar Stand" [ref=e227] [cursor=pointer]:
                  - generic: Collar Stand
                  - generic: Cut 2
                - button "Select Cuff" [ref=e230] [cursor=pointer]:
                  - generic: Cuff
                  - generic: Cut 4
                - button "Select Sleeve Placket" [ref=e233] [cursor=pointer]:
                  - generic: Sleeve Placket
                  - generic: Cut 2
                - button "Select Sleeve" [ref=e236] [cursor=pointer]:
                  - generic: Sleeve
                  - generic: Cut 2
            - generic [ref=e239]: Use Tab to select a piece, Enter to inspect, arrow keys to pan, plus or minus to zoom, and F to fit.
            - group [ref=e240]:
              - generic "Accessible piece summary" [ref=e241] [cursor=pointer]
            - generic [ref=e242]:
              - button "Zoom in" [ref=e243] [cursor=pointer]
              - button "Zoom out" [ref=e247] [cursor=pointer]
              - button "100%" [ref=e251] [cursor=pointer]
              - button "Fit all" [ref=e255] [cursor=pointer]
              - generic [ref=e261]:
                - checkbox "Show Notches" [checked] [ref=e262]
                - text: Show Notches
              - generic [ref=e263]:
                - checkbox "Show Grainline" [checked] [ref=e264]
                - text: Show Grainline
              - generic [ref=e265]:
                - checkbox "Show Seam Allowance" [checked] [ref=e266]
                - text: Show Seam Allowance
          - complementary [ref=e267]:
            - generic [ref=e268]:
              - heading "Pattern Info" [level=3] [ref=e269]
              - generic [ref=e270]:
                - generic [ref=e271]:
                  - term [ref=e272]: Garment
                  - definition [ref=e273]: Men’s Shirt
                - generic [ref=e274]:
                  - term [ref=e275]: Fit
                  - definition [ref=e276]: Regular Fit
                - generic [ref=e277]:
                  - term [ref=e278]: Size
                  - definition [ref=e279]: L
                - generic [ref=e280]:
                  - term [ref=e281]: Total Pieces
                  - definition [ref=e282]: "8"
                - generic [ref=e283]:
                  - term [ref=e284]: Unit
                  - definition [ref=e285]: cm
                - generic [ref=e286]:
                  - term [ref=e287]: Seam Allowance
                  - definition [ref=e288]: 1 cm
                - generic [ref=e289]:
                  - term [ref=e290]: Notches
                  - definition [ref=e291]: Demo marks
                - generic [ref=e292]:
                  - term [ref=e293]: Grainlines
                  - definition [ref=e294]: "Yes"
            - generic [ref=e295]:
              - heading "Actions" [level=3] [ref=e296]
              - button "Regenerate Pattern" [ref=e297] [cursor=pointer]
              - button "Edit in Studio" [ref=e303] [cursor=pointer]
              - button "View 3D Preview" [disabled] [ref=e310]
      - generic [ref=e314]:
        - generic [ref=e315]:
          - heading "Measurement Summary" [level=3] [ref=e316]
          - generic [ref=e317]:
            - generic [ref=e318]:
              - term [ref=e319]: Size
              - definition [ref=e320]: L
            - generic [ref=e321]:
              - term [ref=e322]: Chest
              - definition [ref=e323]: 116.0 cm
            - generic [ref=e324]:
              - term [ref=e325]: Waist
              - definition [ref=e326]: 112.0 cm
            - generic [ref=e327]:
              - term [ref=e328]: Shoulder
              - definition [ref=e329]: 48.5 cm
            - generic [ref=e330]:
              - term [ref=e331]: Sleeve
              - definition [ref=e332]: 66.0 cm
        - generic [ref=e333]:
          - heading "Pattern Pieces (8)" [level=3] [ref=e334]
          - generic [ref=e335]:
            - button "Front (2)" [ref=e336] [cursor=pointer]
            - button "Back (1)" [ref=e340] [cursor=pointer]
            - button "Yoke (1)" [ref=e344] [cursor=pointer]
            - button "Sleeve (2)" [ref=e348] [cursor=pointer]
            - button "Collar (2)" [ref=e352] [cursor=pointer]
            - button "Collar Stand (2)" [ref=e356] [cursor=pointer]
            - button "Cuff (4)" [ref=e360] [cursor=pointer]
            - button "Sleeve Placket (2)" [ref=e364] [cursor=pointer]
        - generic [ref=e368]:
          - heading "Next Step" [level=3] [ref=e369]
          - strong [ref=e370]: Demo pattern generated
          - paragraph [ref=e371]: Review validation warnings, inspect the pieces, or export your demo.
          - button "Go to Pattern Studio" [ref=e372] [cursor=pointer]
  - button "Ask AI" [ref=e375] [cursor=pointer]
```

# Test source

```ts
  1  | import AxeBuilder from '@axe-core/playwright';
  2  | import {expect,test} from '@playwright/test';
  3  | 
  4  | import {openGeneratedDemo} from './demo';
  5  | 
  6  | test('measurements workspace passes automated WCAG checks',async({page,request},info)=>{
  7  |  test.setTimeout(90000);
  8  |  await openGeneratedDemo(page,request);
  9  |  const result=await new AxeBuilder({page}).withTags(['wcag2a','wcag2aa','wcag21aa','wcag22aa']).analyze();
  10 |  await info.attach('measurements-axe.json',{body:JSON.stringify(result,null,2),contentType:'application/json'});
  11 |  expect(result.violations.map(v=>({id:v.id,nodes:v.nodes.map(n=>({target:n.target,reason:n.failureSummary}))}))).toEqual([]);
  12 | });
  13 | 
  14 | test('canonical Measurements workspace tracks REF-004',async({page,request})=>{
  15 |  test.setTimeout(90000);
  16 |  await openGeneratedDemo(page,request);
> 17 |  await expect(page).toHaveScreenshot('garment-pattern-maker-v5-ui-reference-1536x1024.png',{
     |                     ^ Error: expect(page).toHaveScreenshot(expected) failed
  18 |   animations:'disabled',caret:'hide',scale:'css',threshold:0.2,maxDiffPixels:0,
  19 |  });
  20 | });
  21 | 
```