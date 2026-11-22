const a = (url, label) =>
  '<a href="' +
  url +
  '" target="_blank" rel="noopener noreferrer">' +
  label +
  '</a>';
const spr = a(
  'https://docs.holykeebs.com/datasheets/SK8707-01.pdf#page=6',
  'Sprintek mechanical drawing, p. 6',
);
export const PARTS = {
  choc: {
    name: 'Kailh Choc v1 + MBK 1U',
    tag: 'Drawing + CAD',
    desc:
      '15 × 15 mm flange, 8 mm bare stem at rest and 3 mm travel. A seated 17.5 × 16.5 mm MBK cap peaks at ≈10.6 mm in the reference CAD. On the 1.6 mm carrier, allow 1.05 mm below for molded pegs and 1.4 mm for terminals. The model adds 0.4 mm for solder, uses 2.4 mm square fillet bounds, and places the LED side toward the rear before column rotation. Hot-swap sockets are not modeled. ' +
      a(
        'https://raw.githubusercontent.com/daprice/keyswitches.pretty/master/SW_PG1350.kicad_mod',
        'direct-solder hole centers',
      ) +
      ' · ' +
      a(
        'https://cdn-shop.adafruit.com/product-files/5113/CHOC+keyswitch_Kailh-CPG135001D01_C400229.pdf',
        'Kailh drawing',
      ) +
      ' · ' +
      a('https://custom.fkcaps.com/keycaps/mbk', 'FKcaps MBK') +
      ' · ' +
      a(
        'https://github.com/crides/kleeb/blob/master/models/pg1350-mbk.step',
        'assembled STEP reference',
      ) +
      '.',
  },
  ulp: {
    name: 'Kailh PG1316S + 1U cap',
    tag: 'Drawing + build',
    desc:
      'The switch body is 13.50 × 13.00 mm; its top-side solder lands extend outside it. The 0.6 mm locating pins do not emerge through a 1.6 mm PCB. The 0.6 mm space reserved below the PCB is a process allowance, not a protruding part. Catalog cap 16 × 16 mm; Mikefive measured 16.05 × 16.25 mm and a 4.2 mm seated height. Nominal travel 1.8 mm. Pitch stays 18 × 17 mm for reach comparison, not footprint compatibility. ' +
      a(
        'https://keycapsss.com/media/82/f2/46/1758970302/CPG1316S01D02-data-sheet.pdf?ts=1758970677',
        'Kailh drawing, p. 1',
      ) +
      ' · ' +
      a(
        'https://keycapsss.com/Kailh-PG1316S-Keycaps/KC10237-1U-BK',
        'catalog cap',
      ) +
      ' · ' +
      a('https://github.com/mikeholscher/zmk-config-mikefive', 'measured cap') +
      ' · ' +
      a(
        'https://kbd.news/Mikefive-a-Kailh-PG1316S-keyboard-2366.html',
        'measured stack',
      ) +
      '.',
  },
  pointer: {
    name: 'Sprintek SK8707-01-004',
    tag: 'Drawing + allowance',
    desc:
      'Sensor PCB 13.20 × 18.29 × 0.80 mm; the 2.40 mm square post protrudes 2.40 mm. Its axis is 6.60 mm from either side and 10.84 mm from the notched edge, not at the board center. The holykeebs kit includes an unsized rubber dome; the modeled Ø5 mm cap, extension and 0.6 mm rise over the keys are design allowances. ' +
      spr +
      ' · ' +
      a(
        'https://holykeebs.com/products/sk8707-01-trackpoint-sensor',
        'detached sensor, driver and dome',
      ) +
      ' · ' +
      a(
        'https://docs.holykeebs.com/guides/trackpoint-module/',
        'attachment reference',
      ) +
      '. Under-mount is a custom concept: proposed 4 mm square opening, ≤2.4 mm shaft through it, 0.5 mm front and 0.8 mm rear hardware allowances plus 0.4 mm to the cover. Bracket, interconnect and extension are unverified' +
      '.',
  },
  driver: {
    name: 'Separate Sprintek controller',
    tag: 'Drawing + allowance',
    desc:
      '23 × 14.5 mm PCB envelope interpreted from the combined views. The marked driver region reserves 3 mm of height; component heights, contacts, mounting and interconnect routing are not verified. ' +
      spr +
      '.',
  },
  controller: {
    name: 'Seeed XIAO nRF52840 Plus',
    tag: 'Spec + allowance',
    desc:
      '21 × 17.8 mm board, modeled top-mounted with a 5 mm module-height allowance. USB opening faces the rear. Extra GPIOs use underside pads, so a full cut-through would not be a valid mounting footprint. The plug and antenna keep-outs are not included. ' +
      a(
        'https://www.seeedstudio.com/Seeed-Studio-XIAO-nRF52840-Plus-p-6359.html',
        'Seeed mechanical dimensions',
      ) +
      ' · ' +
      a(
        'https://docs.zephyrproject.org/latest/boards/seeed/xiao_nrf52840_plus/doc/index.html',
        'pad map',
      ) +
      ' · ' +
      a(
        'https://eu.robotshop.com/fr/products/seeed-studio-xiao-nrf52840-plus',
        'height reference',
      ) +
      '.',
  },
  battery: {
    name: 'Protected 301230 LiPo',
    tag: 'Vendor envelope',
    desc:
      'Reference 110 mAh protected pack: 32 × 11.5 × 3.3 mm, plus 20 mm leads without a plug. The name “301230” alone is not a fit specification. Changing thickness models a hypothetical envelope; lead bend, insulation, swelling allowance and protective shell remain to be designed. ' +
      a(
        'https://42keebs.eu/shop/parts/lithium-polymer-battery/',
        '42keebs pack dimensions',
      ) +
      '.',
  },
  mouse: {
    name: 'C&K PTS810 mouse controls',
    tag: 'Drawing + allowance',
    desc:
      'Left-half controls for left click, scroll hold and right click. PTS810SJM250SMTR LFS: 4.2 × 3.2 mm housing, 2.5 mm actuator height. The 8 × 5 mm paddles are proposed; these are not standard Choc keycaps. ' +
      a(
        'https://www.digikey.com/en/products/detail/c-k/PTS810SJM250SMTR-LFS/4176610',
        'exact switch ordering code',
      ) +
      ' · ' +
      a(
        'https://www.littelfuse.com/assetdocs/littelfuse-ck-tactile-pts810-series-datasheet?assetguid=f1e4bc97-66e9-4beb-99c6-eaef0bd3bff4',
        'manufacturer drawing',
      ) +
      '.',
  },
  pcb: {
    name: 'Tapir carrier PCB',
    tag: 'Allowance',
    desc:
      'Proposed 1.6 mm PCB, 18 × 17 mm pitch; 3×6 + 3 thumb keys per side. Silkscreen and traces are illustrative. The contour is generated for this reach study; it is not a routable or verified KiCad board. ' +
      a(
        'https://github.com/EDToaster/edtoaster-zmk-keymaps/blob/main/config/corne.keymap',
        'Corne key order',
      ) +
      ' · ' +
      a('https://github.com/RasmusKoit/pipar', 'Pipar geometry reference') +
      '.',
  },
  back: {
    name: 'Protective back cover',
    tag: 'Allowance',
    desc: 'Nominal 1 mm back sheet. The original top mount reserves 2.2 mm to the carrier underside. For an under-mounted sensor the cover plane on both halves lowers if needed to leave 0.4 mm below the rear hardware allowance. A local right-hand pocket would be a different design. Mounts, fasteners and edge protection remain open.',
  },
};
