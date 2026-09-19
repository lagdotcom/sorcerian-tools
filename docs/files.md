# Sorcerian Files

Sorcerian has its own filesystem and organisation scheme.

## System Disks

The v1.0 and v1.1 disks are very similar. `PRNO1` and `PRNO4` are different sizes.

- `      `: Z80 code; loader for the game
- `CH###`: character graphics; first number = race, second = gender, third = age category
- `C_###`
- `ENDTX`
- `MA###`
- `MOGI1`, `MOGI2`: planar image; text intro
- `M_###`
- `PLPTR`: character graphic patterns
- `PRNO#`: Z80 code; split into sections
  - `PRNO0`: title screen?
  - `PRNO1`: main menu
  - `PRNO2`: exploration
  - `PRNO3`: town
- `P_###`
- `SS###`
- `TAIT1`, `TAIT2`: planar image; Sorcerian logo
- `TEXT`: mono image; font

## Utility Disk

- `CH###`
- `CHCOM`
- `EE###`
- `GAME`
- `LETT1`, `LETT2`
- `MAIN#`, `MAIN#?`
- `PRNO#`
- `QUIZ#`
- `SS###`
- `ZAIKO`

## User Disk

- `SAVE#`
- `ZAIKO`
- `VOL#-#`

## Scenario Disks

- `C_##?`, `C_###P`
- `END##`
- `M_###`
- `MA###`
- `MENU`
- `MENUZZ`: MS-DOS batch file?
- `NC###`
- `ND###`
- `NP###`
- `P_###`
- `PRNO#`
- `S_###`
- `SS###`
- `TR###`: treasure data

## Odd Ones Out

- Gilgamesh has `END2`, `PIC#`, `TITL#`.
- New has `ITEM#`.
- Tsuika 2/3 disks have `COMLIB`.
- Tsuika 3 has `s#` and `SHOP01`.
- Selected disks have `CM_A#`, `FN_c#`, `MAIN#`, `SL_?#`, `SL5??`, `SR_?#`.
- Selected 1 has `TNK##`.
- Selected 3 has `ENDTX`, `FIANE`, `VOL3-?`.
- Selected 5 has `EN_A#`.
